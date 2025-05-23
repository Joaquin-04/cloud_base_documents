/** @odoo-module **/

import { DocumentsActivityController } from "@documents/views/activity/documents_activity_controller";
import { patch } from "@web/core/utils/patch";
import { useCloudBaseDocumentView } from "@cloud_base_documents/views/cloud_base_hooks"


patch(DocumentsKanbanController.prototype, {
    /*
    * Re-write to re-define onClickShareDomain
    */
    setup() {
        super.setup(...arguments);
        const properties = useCloudBaseDocumentView(this.documentsViewHelpers());
        Object.assign(this, properties);
    },
});
