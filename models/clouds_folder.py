# -*- coding: utf-8 -*-

import json

from odoo import api, fields, models


class clouds_folder(models.Model):
    """
    Overwrite to introduce one2one related to documents folder
    """
    _inherit = "clouds.folder"

    documents_folder_id = fields.Many2one("documents.folder", string="Linked workspace", index=True)

    @api.model_create_multi
    def create(self, vals_list):
        """
        Re-write to automatically create documents folders if parent has a related document folder
        We may safely assign the same rule as parent folder, since if a document folder is synced by the rule,
        all its children would be also synced as children

        Extra info:
         * prepare_queue_context in ctx - means that we are here from folders preparation queue (both standard &
           enterprise, which does not assume creating new workspace folders. It works with existing document folders,
           while document rules even do not assume default folders
          IMPORTANT: context is different from running queue context which might generate new folders (it is
          "sync_queue_context" defined during clients initiated)
        """
        folders = super(clouds_folder, self).create(vals_list)
        if self._context.get("prepare_queue_context"):
            return folders
        folders_updated = folders.sudo()
        for folder in folders_updated:
            if folder.parent_id and folder.parent_id.rule_id and folder.parent_id.rule_id.rule_type == "document" \
                    and not folder.documents_folder_id:
                parent_workspace_id = folder.parent_id.documents_folder_id
                documents_folder_id = self.env["documents.folder"].sudo().create({
                    "company_id": parent_workspace_id.company_id.id,
                    "parent_folder_id": parent_workspace_id.id,
                    "name": folder.name,
                    "group_ids": [(6, 0, parent_workspace_id.group_ids.ids)],
                    "read_group_ids": [(6, 0, parent_workspace_id.read_group_ids.ids)],
                    "user_specific": parent_workspace_id.user_specific,
                })
                folder.write({
                    "documents_folder_id": documents_folder_id.id,
                    "rule_id": folder.parent_id.rule_id.id,
                    "res_model": "documents.folder",
                    "res_id": documents_folder_id.id,
                })
        return folders

    @api.model
    def _reconcile_folder_enterprise(self, vals, reconcilled_ids=[]):
        """
        The method to create or update folder based on rules

        Args:
         * vals - dict of folder values
           ** documents_folder_id should be present as key (int)
         * reconcilled_ids - list of ints - of folders which we have managed before

        Methods:
         * _check_needed_update

        Returns:
         * tuple:
          ** clouds.folder object
          ** folder_write - bool - whether any change to a folder was done (so, need to update attachments)
        """
        folder_write = False
        folder_id = self.search(
            [
                ("documents_folder_id", "=", vals.get("documents_folder_id")),
                "|", ("active", "=", True), ("active", "=", False),
            ], limit=1,
        )
        if folder_id:
            if folder_id.id not in reconcilled_ids:
                new_vals = folder_id._check_needed_update(vals)
                if new_vals:
                    folder_write = True
                    new_vals.update({"source_name": vals.get("name")})
                    folder_id.write(new_vals)
        else:
            folder_write = True
            vals.update({"source_name": vals.get("name")})
            folder_id = self.create(vals)
        return folder_id, folder_write
