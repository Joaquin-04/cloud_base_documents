/** @odoo-module **/

import { DocumentsInspector } from "@documents/views/inspector/documents_inspector";
import { download } from "@web/core/network/download";
import { patch } from "@web/core/utils/patch";
import { serializeDate } from "@web/core/l10n/dates";
import { useService } from "@web/core/utils/hooks";
const { DateTime } = luxon;


patch(DocumentsInspector.prototype, {
    /*
    * Re-write to import required services
    */
    setup() {
        this.uiService = useService("ui");
        super.setup(...arguments);
    },
    /*
    * Re-write not to consider synced PDFs as pdfs to be cut
    */
    isPdfOnly() {
        return this.props.documents.every(
            (record) => record.isPdf() || (
                record.data.cloud_key && (record.data.mimetype === "application/pdf" || record.data.mimetype === "application/pdf;base64")
            )
        );
    },
    /*
    * Fully re-write to allow donwloading URL links as zip
    */
    async onDownload() {
    	this.uiService.block();
        const documents = this.props.documents.filter((rec) => rec.data.type !== "empty");
        if (!documents.length) {
            return;
        }
        const linkDocuments = documents.filter((el) => el.data.type === "url" && !el.data.cloud_key);
        const noLinkDocuments = documents.filter((el) => el.data.type !== "url" || el.data.cloud_key);
        if (documents.length === 1 && linkDocuments.length) {
            let url = linkDocuments[0].data.url;
            url = /^(https?|ftp):\/\//.test(url) ? url : "http://" + url;
            window.open(url, "_blank");
        } else if (noLinkDocuments.length) {
            await this.download(noLinkDocuments);
        };
        this.uiService.unblock();
    },
    /*
    * Fully re-write to make async (and block UI in meanwhile)
    */
    async download(records) {
        if (records.length === 1) {
            await download({
                data: {},
                url: `/documents/content/${records[0].resId}`,
            });
        } else {
            await download({
                data: {
                    file_ids: records.map((rec) => rec.resId),
                    zip_name: `documents-${serializeDate(DateTime.now())}.zip`,
                },
                url: "/document/zip",
            });
        }
    },
    /*
    * The method to open the cloud URL if any
    */
    async onOpenCloudLink(ev, recordId) {
        ev.stopPropagation();
        ev.preventDefault();
        const cloudURL = await this.orm.call(
            "documents.document", "action_retrieve_url", [[recordId]],
        );
        const cloudLink = document.createElement("a");
        cloudLink.setAttribute("href", cloudURL);
        cloudLink.setAttribute("target", "_blank");
        cloudLink.click();
    },
});
