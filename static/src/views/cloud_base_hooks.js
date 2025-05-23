/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { useService } from "@web/core/utils/hooks";
import { useEnv, useRef } from "@odoo/owl";
import { x2ManyCommands } from "@web/core/orm_service";


export function useCloudBaseDocumentView(helpers) {
	/*
	* This is a copy of the documents hooks, since monkeypatching is not possible for stand-alone functions
	* The only goal (mentioned as intervention) is to allow sharing synced items
	*/
    const root = useRef("root");
    const orm = useService("orm");
    const notification = useService("notification");
    const dialogService = useService("dialog");
    const env = useEnv();

	return {
        onClickShareDomain: async () => {
            const selection = env.model.root.selection;
            const folderId = env.searchModel.getSelectedFolderId();
            if (
                selection.length &&
                selection.every((rec) => ["empty", "url"].includes(rec._values.type) && !rec.data.cloud_key) /*intervention*/
            ) {
                notification.add(_t("The links and requested documents are not shareable."), {
                    type: "danger",
                });
                return;
            }
            // All workspace
            let folderIds;
            if (!folderId) {
                folderIds = selection
                    .filter((rec) => ! ( ["empty", "url"].includes(rec._values.type) && !rec.data.cloud_key )) /*intervention*/
                    .map((rec) => rec.data.folder_id[0]);
                // Check if documents are from different workspace
                if (folderIds.length > 1 && folderIds.some((val) => val !== folderIds[0])) {
                    notification.add(_t("Can't share documents of different workspaces."), {
                        type: "danger",
                    });
                    return;
                }
            }
            const defaultVals = {
                domain: env.searchModel.domain,
                folder_id: folderId || folderIds[0],
                tag_ids: [x2ManyCommands.set(env.searchModel.getSelectedTagIds())],
                type: selection.length ? "ids" : "domain",
                document_ids: selection.length
                    ? [
                          x2ManyCommands.set(
                              selection
                                  .filter((rec) => rec._values.type !== "empty")
                                  .map((rec) => rec.resId)
                          ),
                      ]
                    : false,
            };
            const vals = helpers?.sharePopupAction
                ? await helpers.sharePopupAction(defaultVals)
                : defaultVals;
            const act = await orm.call("documents.share", "open_share_popup", [vals]);
            const shareResId = act.res_id;
            let saved = false;
            dialogService.add(
                FormViewDialog,
                {
                    resModel: "documents.share",
                    resId: shareResId,
                    onRecordSaved: async (record) => {
                        saved = true;
                        // Copy the share link to the clipboard
                        navigator.clipboard.writeText(record.data.full_url);
                        // Show a notification to the user about the copy to clipboard
                        notification.add(_t("The share url has been copied to your clipboard."), {
                            type: "success",
                        });
                    },
                },
                {
                    onClose: async () => {
                        if (!saved) {
                            await orm.unlink("documents.share", [shareResId]);
                        }
                    },
                }
            );
        },
    }
};
