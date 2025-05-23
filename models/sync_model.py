# -*- coding: utf-8 -*-

import json

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class sync_model(models.Model):
    """
    Overriding to introduce documents-related rules
    """
    _inherit = "sync.model"

    rule_type = fields.Selection(
        selection_add=[("document", "Workspace-Related Rule")],
        ondelete={"document": "cascade"},
    )
    doc_domain = fields.Text(string="Workspace filters", default="[]")

    @api.model
    def _prepare_document_folders(self, cron_timeout):
        """
        --- RELATES ONLY TO THE RULES OF TYPE "DOCUMENT" ---
        The method to parse document-related rules to trigger folders update:
         * recursive folder creation for workspace under the rule (recursively)
         * deactivating obsolete folders related to the rules

        --- CRITICAL---
        While parsing the rules we rely upon sequence of the rules. If a folder is found by the first rule,
         it would be excluded from the others. In that sense, ordering by parent_level and passing reconcilled_ids
         is critical.
        Moreover, it defines the key difference from "_prepare_folders" where we can multi create folders, since
         do not need to CHECK EACH CHILDREN BEFORE MOVING TO THE NEXT POINT.
        Simultaneously, it is assumed that there would be no dozens of thousands of workspaces, so such not
         optimal perfomance is not crucial

        Args:
         * cron_timeout - datetime after which cron should be stopped

        Methods:
         * _reconcile_folder
         * _prepare_doc_folders_recursively of documents.folder

        Returns:
         * bool - if the method was fully done, False otherwise
        """
        self.env["clouds.client"]._cloud_log(
            True, "Workspace folders updating was started. Locked till: {}".format(cron_timeout)
        )
        cloud_folder_object = self.env["clouds.folder"]
        document_folder_object = self.env["documents.folder"]
        to_sync_models = self.search([("rule_type", "=", "document")])

        Config = self.env["ir.config_parameter"].sudo()
        # if there was a savepoint, get done rules and folders
        folders_savepoint = json.loads(Config.get_param("cloud_base_doc_folders_savepoint", "{}"))
        done_sync_models_ids = []
        reconcilled_ids = []
        if folders_savepoint != "{}":
            done_sync_models_ids = folders_savepoint.get("synced_models_list", [])
            reconcilled_ids = folders_savepoint.get("reconcilled_ids", [])
        # iterarate over all worskpace-related rules
        for rule in to_sync_models:
            if rule.id in done_sync_models_ids:
                # processed by previous not finished cron job > might safely switch to a new rule
                continue
            # manage this sync.model folder
            root_folder_id, create_vals, folder_write = cloud_folder_object._reconcile_folder({
                "name": rule.name,
                "rule_id": rule.id,
                "parent_id": False,
                "active": True,
                "res_model": "documents.folder",
            })
            if root_folder_id:
                root_folder_id_int = root_folder_id.id
            else:
                root_folder_id_int = self.env["clouds.folder"].create(create_vals).id
            if root_folder_id_int not in reconcilled_ids:
                reconcilled_ids.append(root_folder_id_int)
            # find worskpace based on the rule settings, and launch folders' preparation for those
            found_folders = document_folder_object.search(safe_eval(rule.doc_domain), order="parent_level, sequence")
            reconcilled_ids, fully_done = found_folders._prepare_doc_folders_recursively(
                cron_timeout, rule.id, root_folder_id_int, reconcilled_ids, done_sync_models_ids,
            )
            if not fully_done:
                log_message = "Workspace folders' updating was stopped because of the timeout. Continue afterward"
                self.env["clouds.client"]._cloud_log(True, log_message, "WARNING")
                return False
            done_sync_models_ids.append(rule.id)
        else:
            # if all rules are processed > deactivate folders which do not suit any of the rules
            # IMPORTANT: workspace-related folders are created only here; so we may safely rely upon reconcilled items
            obsolete_folder_ids = self.env["clouds.folder"].search([
                ("id", "not in", reconcilled_ids), ("rule_id", "!=", False), ("rule_id.rule_type", "=", "document")
            ])
            obsolete_folder_ids.write({"active": False})
            Config.set_param("cloud_base_doc_folders_savepoint", "{}")
            self.env["clouds.client"]._cloud_log(True, "Workspace folders updating was successfully finished")
            self._cloud_commit()
            return True
