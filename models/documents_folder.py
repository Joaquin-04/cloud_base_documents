# -*- coding: utf-8 -*-

import json

from odoo import _, api, fields, models

OBJECTS_TO_PROCESS = 1000  # based on performance tests on default psql conf


class documents_folder(models.Model):
    """
    Overwrite to add sync options
    """
    _inherit = "documents.folder"

    key = fields.Char(string="ID in client")

    @api.depends("parent_folder_id.parent_level")
    def _compute_parent_level(self):
        """
        Compute method for parent level
        The idea is to sort folders by hierarchy involvement, to firstly serve the ones closer to the top
        This method is recursive storable
        """
        for folder in self:
            folder.parent_level = folder.parent_folder_id and folder.parent_folder_id.parent_level + 1 or 0

    parent_level = fields.Integer(
        string="Parent Level",
        compute=_compute_parent_level,
        compute_sudo=True,
        store=True,
        recursive=True,
    )

    def _prepare_doc_folders_recursively(self, cron_timeout, rule_id, parent_id=False, reconcilled_ids=[],
        done_sync_models_ids=[]):
        """
        The method to prepare folder for this sync model and its records
        Trigger itself to launch the same for child sync models

        Args:
         * cron_timeout - datetime after which cron should be stopped
         * rule_id - int- sync.model id
         * parent_id - int - id of clouds.folder object
         * reconcilled_ids - list of ids - created clouds.folder (used both as argument and in return)
         * done_sync_models_ids - list if ids - sync rules which have been already processed

        Methods:
         * _reconcile_folder_enterprise of clouds.folder
         * _prepare_doc_folders_recursively (recursion)

        Returns:
         * tuple
          ** list of ints - reconcilled ids of cloud.folders
          ** bool - whether the method is fully done

        Extra info:
         * We write both res_model/res_id & documents_folder_id, since the former is used for UI & user rights,
           the latter - to simplify preparing queue algos
        """
        Config = self.env["ir.config_parameter"].sudo()
        all_folders = self
        while all_folders:
            # split records in batches to be able to exit if timeouted and commit changes frequently
            bath_folders = all_folders[:OBJECTS_TO_PROCESS]
            for doc_folder in bath_folders:
                doc_folder_id_int = doc_folder.id
                folder_id, folder_write = self.env["clouds.folder"]._reconcile_folder_enterprise({
                    "name": doc_folder.name,
                    "rule_id": rule_id,
                    "parent_id": parent_id,
                    "documents_folder_id": doc_folder_id_int,
                    "active": True,
                    "res_model": "documents.folder",
                    "res_id": doc_folder_id_int,
                }, reconcilled_ids)
                folder_id_int = folder_id.id
                if folder_id_int not in reconcilled_ids:
                    reconcilled_ids.append(folder_id_int)
                if folder_write:
                    attachments_to_update = self.env["ir.attachment"].search([
                        ("folder_id", "=", doc_folder_id_int), ("clouds_folder_id", "!=", folder_id_int),
                    ])
                    if attachments_to_update:
                        attachments_to_update.with_context(no_folder_update=True).write({
                            "clouds_folder_id": folder_id.id
                        })
                # go by child workspaces before going to the next found: child is more important than the next found
                for subfolder in doc_folder.children_folder_ids:
                    reconcilled_ids, fully_done = subfolder._prepare_doc_folders_recursively(
                        cron_timeout, rule_id, folder_id.id, reconcilled_ids, done_sync_models_ids,
                    )
                    if not fully_done:
                        return reconcilled_ids, False
            # If not enough time left > make emergent exit
            if fields.Datetime.now() >= cron_timeout:
                folder_savepoint_vals = json.dumps({
                    "synced_models_list": done_sync_models_ids,
                    "reconcilled_ids": reconcilled_ids,
                })
                Config.set_param("cloud_base_doc_folders_savepoint", folder_savepoint_vals)
                self.env["sync.model"]._cloud_commit()
                return reconcilled_ids, False
            self.env["sync.model"]._cloud_commit()
            all_folders -= bath_folders
        return reconcilled_ids, True
