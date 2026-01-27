/** @odoo-module **/
import { AccountMoveListController } from "@account/components/bills_upload/bills_upload";
import { AccountMoveUploadKanbanController } from '@account/components/bills_upload/bills_upload';
import { CogMenuList } from "@cyllo_base/js/cog_menu_form";
import { View } from "@web/views/view";

AccountMoveListController.components={
   ...AccountMoveListController.components, CogMenuList, View
}

AccountMoveUploadKanbanController.components={
   ...AccountMoveUploadKanbanController.components, CogMenuList
}