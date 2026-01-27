/** @odoo-module */
// Import necessary modules and components
import { registry } from "@web/core/registry";
import { BarcodeDialog } from "./barcode_dialog";
import { Component, useState, useRef } from "@odoo/owl";
import { useService, useBus } from "@web/core/utils/hooks";
import { CylloBarcodeAdjustmentLines } from "./barcode_adjustment_lines"
import { jsonrpc } from "@web/core/network/rpc_service";

const actionRegistry = registry.category("actions");
export class CylloBarcodeAdjustment extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action")
        this.dialog = useService("dialog");
        this.notification = useService("notification")
        const barcode = useService("barcode");
        this.sound = useService("barcodeSound");
        this.location = false
        this.state = useState({
            adjust_stock: [],
            selected_stock: []
        })
        useBus(barcode.bus, "barcode_scanned", (ev) => this.ReadBarcode(ev.detail.barcode))
        useBus(this.env.bus, 'barcode-cancel-stock-quantity', (ev) => this._onClickCancelSelected(ev.detail));
        useBus(this.env.bus, 'barcode-applying-multi-stock-quantity', (ev) => this.MultiApplyQuantity(ev.detail));
        this.root = useRef('BarcodeAdjustmentRoot')
        this.getAdjustmentData()
    }
    /**
     * Function for cancelling the selected records in the view
     */
    _onClickCancelSelected(ids) {
        var self = this
        jsonrpc('/barcode-adjustment/cancel_stock_quant', {
            'quant_ids': ids
        }).then(() => {
            if (self.state.selected_stock == ids) {
                self.state.selected_stock = []
            }
            self.state.adjust_stock = self.state.adjust_stock.filter(item => !ids.includes(item.id))
        })
    }
    /**
     * Function for applying the selected records in the view
     */
    _onClickApplySelected() {
        var self = this
        if(this.state.selected_stock.length){
            jsonrpc('/barcode-adjustment/apply_multiple_inventory', {
                'quant_ids': self.state.selected_stock
            }).then((response) => {
                self.actionService.doAction('soft_reload')
                if (response) {
                    self.actionService.doAction(response)
                    self.state.adjust_stock = self.state.adjust_stock.filter(item => !self.state.selected_stock.includes(item.id))
                    self.state.selected_stock = []
                } else {
                    self.state.adjust_stock = self.state.adjust_stock.filter(item => !self.state.selected_stock.includes(item.id))
                    self.state.selected_stock = []
                }
            })
        } else {
            self.sound.Danger.play()
            self.notification.add('Please select minimum one product ', {
                type: "warning",
                sticky: false,
            })
        }
    }
    /**
     * Function change the data from the list that are confirmed
     */
    MultiApplyQuantity(data) {
        if (data.value) {
            this.state.selected_stock.push(data.id)
        } else {
            this.state.selected_stock = this.state.selected_stock.filter(item => item !== data.id)
        }
    }
    /**
     * Function for open web cam and scan the barcode
     */
    _onClickScanProduct() {
       this.dialog.add(BarcodeDialog, {
            title: 'Barcode Scanner',
            ReadBarcode: (result) => {
                this.ReadBarcode(result)
            }
        })
    }
    /**
     * Function works when the barcode catches the barcode code and passing the code to python
     */
    ReadBarcode(barcode) {
        barcode = String(barcode)
        var self = this
        if (barcode === 'action_main_menu') {
            this.actionService.doAction({
                type: "ir.actions.client",
                name: 'Barcode',
                tag: "cyllo_barcode_tags",
                target: "inline",
            })
        } else if (barcode === 'action_validate') {
            this._onClickApplySelected()
        } else {
            jsonrpc('/barcode-adjustment/product-barcode', {
                'code': barcode,
                'location': this.location
            }).then(function(response) {

                if (response.type == 'location') {
                    self.root.el.querySelector('.adjustment_location_header').innerHTML = 'Scan product from the location ' + response.name + ' <i class="fa fa-barcode"/>'
                    self.location = response.id
                } else if (response.type == 'not_storable') {
                    self.sound.Alert.play()
                    self.notification.add('The product ' + response.name + ' is not a storable product please scan a storable product', {
                        type: "warning",
                        sticky: false,
                    })
                } else if (response.type == 'product') {
                    self.state.adjust_stock.push(response)
                } else if (response.type == 'exist_product') {
                    self.state.adjust_stock.find(task => task['id'] === response.id).inv_quantity += 1
                } else {
                    self.sound.Alert.play()
                    self.notification.add('Product or Location is not found, try again', {
                        type: "warning",
                        sticky: false,
                    })
                }
            })
        }
    }
    /**
     * Function for displaying the data in the inventory adjustment view
     */
    async getAdjustmentData() {
        this.state.adjust_stock = await jsonrpc('/barcode-adjustment/get_adjustment_stock_data', {})
    }
}

CylloBarcodeAdjustment.template = "cyllo_barcode.BarcodeAdjustment";
CylloBarcodeAdjustment.components = {
    CylloBarcodeAdjustmentLines
}
actionRegistry.add('cyllo_adjustment_client_action', CylloBarcodeAdjustment);