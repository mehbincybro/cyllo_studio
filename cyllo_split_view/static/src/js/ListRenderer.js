/** @odoo-module **/
import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";
import { useBus, useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

patch(ListRenderer.prototype, {
    setup(){
    super.setup();
        this.orm = useService('orm');
        this.spil = useState({
            split_view_enable: false
        })
        useBus(this.env.bus, "split_view_record_clicked", this.enableSplitView);
        useBus(this.env.bus, "split_view_close_clicked", this.disableSplitView);
    },
    async enableSplitView(){
        var modelName =  new URLSearchParams(window.location.href.split('#')[1]).get('model');
        this.is_split_view = await this.orm.call("ir.model", "search_read", [], {
            fields: ["id", "list_split_view"],
            domain: [["model", "=", modelName]],
        });
        this.spil.split_view_enable = this.is_split_view[0].list_split_view
    },
    disableSplitView(){
        this.spil.split_view_enable = false
    }
})
