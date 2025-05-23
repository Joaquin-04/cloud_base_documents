# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ir_attachment(models.Model):
    """
    Overwritting to make sync of Odoo document folders and their attachments
    """
    _inherit = "ir.attachment"

    @api.depends("document_ids", "document_ids.folder_id")
    def _compute_folder_id(self):
        """
        Compute method for folder_id
        """
        for attachment in self:
            folder_id = False
            handler = False
            if attachment.document_ids:
                folder_id = attachment.document_ids[0].folder_id
                if hasattr(attachment.document_ids, "handler"):
                    handler = attachment.document_ids[0].handler
            attachment.folder_id = folder_id
            attachment.handler = handler

    def _inverse_url(self):
        """
        Inverse method for URL
        To update document.document url if changed

        Extra info:
         * We apply document URL change if attachment is synced (cloud_key) or when its URL becomes empty (to cover
           the case when attachment is reversively synced)
        """
        if self._context.get("sync_queue_context"):
            for attachment in self:
                document = self.document_ids and self.document_ids[0] or False
                if document:
                    document.url = attachment.url

    folder_id = fields.Many2one(
        "documents.folder",
        compute=_compute_folder_id,
        compute_sudo=True,
        store=True,
        string="Documents Folder",
    )
    # the special field which might be introduced to add the special type, e.g. Odoo spreadsheet
    handler = fields.Char(compute=_compute_folder_id, compute_sudo=True, store=True)
    document_ids = fields.One2many("documents.document", "attachment_id", string="Related documents")
    url = fields.Char(inverse=_inverse_url)

    @api.model_create_multi
    def create(self, vals_list):
        """
        Re-write to force linked workspace change if folder is changed

        Methods:
         * _update_documents_workspaces
        """
        attachment_ids = super(ir_attachment, self).create(vals_list)
        attachment_ids._update_documents_workspaces()
        return attachment_ids

    def write(self, vals):
        """
        Re-write to force linked workspace change if folder is changed

        Methods:
         * _update_documents_workspaces
        """
        res = super(ir_attachment, self).write(vals)
        self._update_documents_workspaces(vals)
        return res

    def _update_documents_workspaces(self, vals=None):
        """
        The method to change document workspace when their attachment cloud folder is changed

        Extra info:
         * If we are from preparing queue, document.document should not be created, since attachments cannot be created
        """
        if self._context.get("prepare_queue_context"):
            return False

        if vals is None or (vals and vals.get("clouds_folder_id")):
            self = self.with_context(no_document=True).sudo()
            self.invalidate_model(["clouds_folder_id", "document_ids", "url"])
            for attachment in self:
                folder_id = attachment.clouds_folder_id
                if (vals is None and folder_id) or (vals and vals.get("clouds_folder_id")):
                    new_worskpace_id = folder_id and folder_id.documents_folder_id
                    document_ids = attachment.document_ids
                    if not new_worskpace_id:
                        # if not workspace > delete documents, keep attachments
                        if document_ids:
                            # since ondelete=cascade, we should firslty unlink attachments from documents
                            document_ids.write({"attachment_id": False})
                            document_ids.unlink()
                    elif not document_ids:
                        # if workspace, but no documents > create documents to the workspaces
                        self.env["documents.document"].sudo().create({
                            "attachment_id": attachment.id,
                            "folder_id": new_worskpace_id.id,
                            "url": attachment.url,
                        })
                    else:
                        # if new workspace differs from old one > move document
                        for doc in document_ids:
                            if doc.folder_id != new_worskpace_id:
                                doc.write({"folder_id": new_worskpace_id.id})

