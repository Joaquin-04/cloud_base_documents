# -*- coding: utf-8 -*-

from odoo import api, fields, models


class documents_document(models.Model):
    """
    Overwritting to make sync of Odoo document folders and their attachments
    """
    _inherit = "documents.document"

    @api.depends("attachment_type", "url")
    def _compute_type(self):
        """
        Re-write to make possible url base on attachment url
        """
        for record in self:
            record.type = "empty"
            if record.attachment_id:
                record.type = record.attachment_id.type in ["binary", "url"] and record.attachment_id.type or "binary"
            elif record.url:
                record.type = "url"

    @api.depends("checksum", "cloud_key")
    def _compute_thumbnail(self):
        """
        Re-write to avoid upload file consistent error
        """
        for record in self:
            if record.cloud_key:
                record.thumbnail = False
            else:
                super(documents_document, record)._compute_thumbnail()

    @api.depends("thumbnail", "cloud_key")
    def _compute_thumbnail_status(self):
        """
        Re-write to male all pdfs as not have thumbnails
        """
        synced_documents = self.filtered(lambda doc: doc.cloud_key)
        for sync in synced_documents:
            sync.thumbnail_status = False
        super(documents_document, self-synced_documents)._compute_thumbnail_status()

    type = fields.Selection(compute=_compute_type)
    cloud_key = fields.Char(related="attachment_id.cloud_key", compute_sudo=True, related_sudo=True)
    clouds_folder_id = fields.Many2one(related="attachment_id.clouds_folder_id", compute_sudo=True, related_sudo=True)
    thumbnail = fields.Binary(compute=_compute_thumbnail)
    thumbnail_status = fields.Selection(compute=_compute_thumbnail_status)

    @api.model_create_multi
    def create(self, vals_list):
        """
        Re-write to connect to a proper clouds.folder if exists
        """
        document_ids = super(documents_document, self).create(vals_list)
        document_ids._update_attachments_folder()
        return document_ids

    def write(self, vals):
        """
        Re-write to connect to a proper clouds.folder if exists
        """
        res = super(documents_document, self).write(vals)
        self._update_attachments_folder(vals)
        return res

    def action_donwload_cloud_file(self):
        """
        The method to retrieve content from clouds

        Methods:
         * action_donwload_cloud_file of ir.attachment
        """
        return self.attachment_id.action_donwload_cloud_file()

    def action_retrieve_url(self):
        """
        The method to retrieve a topical URL

        Methods:
         * action_retrieve_url_window of ir.attachment

        Returns:
         * char

        Extra info:
         * Expected singleton
        """
        return self.attachment_id.url and self.attachment_id.action_retrieve_url() or self.url

    def action_retrieve_url_window(self):
        """
        The method to return the window action for the url opening

        Methods:
         * action_retrieve_url

        Returns:
         * dict

        Extra info:
         * Expected singleton
        """
        return {
            "name": "{}".format(self.name),
            "type": "ir.actions.act_url",
            "url": self.action_retrieve_url(),
        }

    def _update_attachments_folder(self, vals=None):
        """
        The method to update clouds folder of attachment
        """
        if vals is None or (vals and vals.get("folder_id")):
            for document in self.sudo():
                if document.folder_id:
                    cloud_folder = self.sudo().env["clouds.folder"].search(
                        [("documents_folder_id", "=", document.folder_id.id)], limit=1,
                    )
                    if cloud_folder:
                        attachment = document.attachment_id
                        if attachment.clouds_folder_id != cloud_folder:
                            attachment.sudo().write({"clouds_folder_id": cloud_folder.id})
