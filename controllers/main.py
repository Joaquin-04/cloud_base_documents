# -*- coding: utf-8 -*-

from odoo import http
from odoo.addons.documents.controllers.documents import ShareRoute
from odoo.http import request


class ShareRouteClass(ShareRoute):
    """
    Re-write to make possible donwload of cloud files instead of opening an url
    """
    def _get_file_response(self, res_id, share_id=None, share_token=None, field="raw", as_attachment=None):
        """
        Re-write to allow downlodaing synced attachments
        """
        record = request.env["documents.document"].browse(int(res_id))
        if record.cloud_key:
            filename = (record.name if not record.file_extension or record.name.endswith(f'.{record.file_extension}')
                else f'{record.name}.{record.file_extension}')
            return request.env["ir.binary"]._get_stream_from(
                record, field, filename=filename
            ).get_response(as_attachment)
        else:
            return super(ShareRouteClass, self)._get_file_response(
                res_id, share_id, share_token, field, as_attachment
            )

    @classmethod
    def _get_downloadable_documents(cls, documents):
        """
        Re-write to add synced attachments (not only binary) to zip archives
        """
        return documents.filtered(lambda d: d.type == "binary" or d.cloud_key)

    @http.route(["/document/share/<int:share_id>/<token>"], type="http", auth="public")
    def share_portal(self, share_id=None, token=None):
        """
        Fully re-write to:
        1. to make cloud synced downloadable
        2. to allow 'all downloadable' when at least one binary of archive
        3. To make negative size if synced
        """
        try:
            share = http.request.env["documents.share"].sudo().browse(share_id)
            available_documents = share._get_documents_and_check_access(token, operation="read")
            if available_documents is False:
                if share._check_token(token):
                    options = {
                        "expiration_date": share.date_deadline,
                        "author": share.create_uid.name,
                    }
                    return request.render("documents.not_available", options)
                else:
                    return request.not_found()

            shareable_documents = available_documents.filtered(lambda r: r.type != "url" or r.cloud_key) # 1
            options = {
                "name": share.name,
                "base_url": share.get_base_url(),
                "token": str(token),
                "upload": share.action == "downloadupload",
                "share_id": str(share.id),
                "author": share.create_uid.name,
                "date_deadline": share.date_deadline,
                "document_ids": shareable_documents,
            }
            if len(shareable_documents) == 1 and shareable_documents.type == "empty":
                return request.render("documents.document_request_page", options)
            elif share.type == "domain":
                all_btn = [document.type == "binary" or document.cloud_key for document in shareable_documents] \
                    and True or False
                options.update(all_button=all_btn, request_upload=share.action == "downloadupload")
                return request.render("documents.share_workspace_page", options)
            if shareable_documents.filtered(lambda r: r.cloud_key):
                total_size = -1 #3
            else:
                total_size = sum(document.file_size for document in shareable_documents)
            options.update(file_size=total_size, is_files_shared=True)
            return request.render("documents.share_files_page", options)
        except Exception:
            logger.exception("Failed to generate the multi file share portal")
        return request.not_found()
