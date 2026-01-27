/** @odoo-module */
// Import necessary modules and components
import { registry } from "@web/core/registry";
import { Component, useState, useRef} from "@odoo/owl";
import { useService, useBus} from "@web/core/utils/hooks";
import { BarcodeDialog } from "./barcode_dialog";
import { jsonrpc } from "@web/core/network/rpc_service";
const actionRegistry = registry.category("actions");
export class CylloBarcode extends Component {
    setup() {
        const barcode = useService("barcode");
        this.root = useRef('BarcodeRoot')
        this.actionService = useService("action")
        this.companyService = useService("company");
        this.sound = useService("barcodeSound");
        this.notification = useService("notification")
        this.dialog = useService("dialog");
        this.orm = useService("orm")
        this.state = useState({
            types: []
        })
        useBus(barcode.bus, "barcode_scanned", (ev) => this.ReadBarcode(ev.detail.barcode))
        this.getOperationTypes()
    }
    /**
     * Function for all operations types in the corresponding company
     */
    async getOperationTypes() {
        const StockOperation = await this.orm.searchRead(
            "stock.picking.type", [
                ["company_id", "=", this.companyService.currentCompany.id],
                ["code", "!=", "mrp_operation"]
            ], ["name"]
        );
        for (let i = 0; i < StockOperation.length; i++) {
            var PickingDraft = await this.orm.searchCount(
                "stock.picking", [
                    ["picking_type_id", "=", StockOperation[i].id],
                    ["state", "=", 'draft']
                ])
            var PickingReady = await this.orm.searchCount(
                "stock.picking", [
                    ["picking_type_id", "=", StockOperation[i].id],
                    ["state", "=", 'assigned']
                ])
            var PickingDone = await this.orm.searchCount(
                "stock.picking", [
                    ["picking_type_id", "=", StockOperation[i].id],
                    ["state", "=", 'done']
                ])
            this.state.types.push({
                'id': StockOperation[i].id,
                'name': StockOperation[i].name,
                PickingDraft,
                PickingReady,
                PickingDone
            })
        }
    }
    /**
     * Function works when the barcode catches the barcode code and passing the code to python
     */
    async ReadBarcode(barcode) {
        barcode = String(barcode)
        this.currentCompany = this.companyService.currentCompany;
        const StockPicking = await this.orm.searchRead(
            "stock.picking", [
                ["name", "=", barcode]
            ], ["name", "id", ]
        )
        const PickingBatch = await this.orm.searchRead(
            "stock.picking.batch", [
                ["name", "=", barcode]
            ], ["name", "id", ]
        )
        if (PickingBatch.length > 0) {
            var id = PickingBatch[0].id
            var name = PickingBatch[0].name
            localStorage.setItem('cyllo-barcode-batch-transfer', id)
            this.actionService.doAction({
                type: "ir.actions.client",
                name: name,
                tag: "cyllo_batch_lines_client_action",
                target: "current"
            })
        } else if (StockPicking.length > 0) {
            var id = StockPicking[0].id
            var name = StockPicking[0].name
            localStorage.setItem('cyllo-barcode-inventory', id)
            localStorage.setItem('cyllo-barcode-inventory-type', 'stock-picking')
            this.actionService.doAction({
                type: "ir.actions.client",
                name: name,
                tag: "cyllo_location_client_action",
                target: "current",
            })
        } else if (barcode === 'action_scrap') {
            this.actionService.doAction({
                name: 'Scrap',
                type: 'ir.actions.act_window',
                res_model: 'stock.scrap',
                views: [
                    [false, 'form']
                ],
                view_mode: 'form',
                target: 'self',
            })
        } else {
            var data = await jsonrpc('/barcode/main-barcode', {
                'code': barcode,
                'company_id': this.companyService.currentCompany.id,
            })
            if (data.type === 'product') {
                this.actionService.doAction({
                    type: 'ir.actions.act_window',
                    res_model: 'stock.quant',
                    domain: [
                        ["product_id", "=", data.id]
                    ],
                    view_mode: 'tree',
                    name: data.name,
                    views: [
                        [false, 'tree']
                    ],
                    target: 'current'
                })
            } else if (data.type === 'operation_type') {
                localStorage.setItem('cyllo-barcode-inventory', data.stock_transfer_id)
                localStorage.setItem('cyllo-barcode-inventory-type', data.type)
                this.actionService.doAction({
                    type: "ir.actions.client",
                    name: data.stock_transfer_name,
                    tag: "cyllo_location_client_action",
                    target: "current"
                })
            } else if (data.type === 'location') {
                localStorage.setItem('cyllo-barcode-inventory', data.stock_transfer_id)
                localStorage.setItem('cyllo-barcode-inventory-type', data.type)
                this.actionService.doAction({
                    type: "ir.actions.client",
                    name: data.stock_transfer_name,
                    tag: "cyllo_location_client_action",
                    target: "current"
                })
            } else {
                this.sound.Alert.play()
                this.notification.add('Please scan the product or location or document', {
                    type: "warning",
                    sticky: false,
                })
            }
        }
    }
    /**
     * Function for opening the view for the corresponding operation types
     */
    _onClickOperation(operation_id, name) {
        localStorage.setItem('cyllo-barcode-operation-type', operation_id)
        localStorage.setItem('cyllo-barcode-operation-name', name)
        this.actionService.doAction({
            type: "ir.actions.client",
            name: "Operation",
            tag: "cyllo_stock_picking_client_action",
            target: "current"
        })
    }
    /**
     * Function for opening batch view
     */
    _onClickOpenBatch() {
        this.actionService.doAction({
            type: "ir.actions.client",
            name: 'Batch Transfer',
            tag: "cyllo_batch_client_action",
            target: "current",
        })
    }
    /**
     * Function for opening product quantity view
     */
    _onClickOpenInventoryAdjustment() {
        this.actionService.doAction({
            type: "ir.actions.client",
            name: 'Inventory Adjustment',
            tag: "cyllo_adjustment_client_action",
            target: "current",
        })
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
}
CylloBarcode.template = "cyllo_barcode.Barcode";
actionRegistry.add('cyllo_barcode_tags', CylloBarcode);