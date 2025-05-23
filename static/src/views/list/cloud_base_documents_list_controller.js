/** @odoo-module **/

import { DocumentsListController } from "@documents/views/list/documents_list_controller";
import { patch } from "@web/core/utils/patch";
import { useCloudBaseDocumentView } from "@cloud_base_documents/views/cloud_base_hooks"


patch(DocumentsListController.prototype, {
    /*
    * Re-write to re-define onClickShareDomain
    */
    setup() {
        super.setup(...arguments);
        const properties = useCloudBaseDocumentView(this.documentsViewHelpers());
        Object.assign(this, properties);
    },
});