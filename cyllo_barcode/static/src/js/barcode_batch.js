/** @odoo-module */
import { registry } from "@web/core/registry";
import { BarcodeDialog } from "./barcode_dialog";
import { Component,useState, onWillStart, useRef } from "@odoo/owl";
import { useBus,useService } from "@web/core/utils/hooks";
import { jsonrpc } from "@web/core/network/rpc_service";
const actionRegistry = registry.category("actions");

export class CylloBarcodeBatch extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            batches: []
        })
        this.actionService = useService("action")
        this.getBatchTransfers()
    }
    /**
     * Function for opening the transfer view
     */
    _onClickOpenTransfer(id, name) {
        localStorage.setItem('cyllo-barcode-batch-transfer', id)
        this.actionService.doAction({
            type: "ir.actions.client",
            name: name,
            tag: "cyllo_batch_lines_client_action",
            target: "current"
        })
    }
    /**
     * Function for opening the wizard
     */
    OpenBatchTransfer(ev, id, name) {
        ev.stopPropagation()
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: 'stock.picking.batch',
            res_id: id,
            target: "current",
            views: [
                [false, "form"]
            ],
        })
    }
    /**
     * Function for getting all records of batch transfer
     */
    async getBatchTransfers() {
        this.state.batches = await this.orm.searchRead(
            "stock.picking.batch", [
                ["state", "=", 'in_progress']
            ], ["name", "id", "picking_type_id", "scheduled_date"]
        )
    }
}

CylloBarcodeBatch.template = "cyllo_barcode.BarcodeBatchTransfer";
actionRegistry.add('cyllo_batch_client_action', CylloBarcodeBatch);

export class CylloBarcodeMoveLines extends Component {
    setup() {
        this.actionService = useService("action")
        this.state = useState({
            line: this.props.line
        })
        this.orm = useService("orm")
        this.root = useRef("MoveLine-root")
    }
    /**
     * Function for invisible the modal
     */
    _onClickDiscardChanges() {
        this.root.el.querySelector('#BatchLineModal').style.display = 'none'
        this.root.el.querySelector('.input_for_quantity').value = this.state.line.quantity_product_uom
        this.is_float = false;
    }
    /**
     * Function for adding number to value of the input box
     */
    _onclickNumber(number) {
        if (!this.is_float) {
            this.root.el.querySelector('.input_for_quantity').value = this.root.el.querySelector('.input_for_quantity').value + number
        } else {
            this.root.el.querySelector('.input_for_quantity').value = Number(this.root.el.querySelector('.input_for_quantity').value) + "." + Number(number)
            this.is_float = false;
        }
    }
    /**
     * Function for increment or decrement the quantity of the record by 1
     */
    _onClickDialOperation(operation) {
        if (operation == 'add') {
            this.root.el.querySelector('.input_for_quantity').value = Number(this.root.el.querySelector('.input_for_quantity').value) + 1
        } else {
            this.root.el.querySelector('.input_for_quantity').value = Number(this.root.el.querySelector('.input_for_quantity').value) - 1
        }
        this.is_float = false;
    }
    /**
     * Function for applying the decimal value in the quantity
     */
    _onClickDialDecimal() {
        if (this.root.el.querySelector('.input_for_quantity').value.indexOf('.') === -1) {
            this.is_float = true;
        }
    }
    /**
     * Function for opening the wizard
     */
    _onClickOpenWizard(model, id) {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: 'Product',
            target: 'current',
            res_model: model,
            res_id: Number(id),
            views: [
                [false, 'form']
            ],
        })
    }
    /**
     * Function for apply button in the modal for changing the quantity of the record
     */
    async _onClickApplyChanges(value) {
        const lot_name = this.state.line.tracking != 'none' ? this.root.el.querySelector('.input_for_batch_serial_number').value : ''
        this.state.line.quantity_product_uom = value
        this.orm.write('stock.move.line', [this.state.line.id], {
            'quantity': Number(value),
            'lot_name': lot_name
        })
        this.root.el.querySelector('#BatchLineModal').style.display = 'none'
        this.is_float = false;
        await this.actionService.doAction('soft_reload');
    }
    /**
     * Function for removing the last value from input value
     */
    _onClickDialRemove() {
        var value = this.root.el.querySelector('.input_for_quantity').value
        if (value) {
            if (value.charAt(value.length - 2) == '.') {
                this.root.el.querySelector('.input_for_quantity').value = value.slice(0, -2);
            } else {
                this.root.el.querySelector('.input_for_quantity').value = value.slice(0, -1);
            }
        }
        this.is_float = false;
    }
}

CylloBarcodeMoveLines.template = "cyllo_barcode.CylloBarcodeMoveLines";

export class CylloBarcodeBatchLines extends Component {
    setup() {
        this.user = useService('user');
        this.id = Number(localStorage.getItem("cyllo-barcode-batch-transfer"))
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.root = useRef("BarcodeTransferLine-Root");
        this.notification = useService("notification")
        this.sound = useService("barcodeSound");
        this.state = useState({
            data: [],
            move_line: [],
        })
        const barcode = useService("barcode");
        this.actionService = useService("action")
        this.locations = false
        this.getData()
        useBus(barcode.bus, "barcode_scanned", (ev) => this.ReadBarcode(ev.detail.barcode));
        onWillStart(async () => {
            var data = await jsonrpc('/barcode-batch/location-package', {})
            this.group_stock_tracking_lot = data.package
            this.group_stock_multi_locations = data.location
        })
    }
    /**
     * Function works when the barcode catches the barcode code and passing the code to python
     */
    async ReadBarcode(barcode) {
        barcode = String(barcode)
        var self = this
        if (barcode === 'print_batch') {
            jsonrpc('/inventory_commands', {
                'code': barcode,
                'id': this.id
            }).then(function(result) {
                if (result != true) {
                    self.actionService.doAction(result)
                }
            })
        } else if (barcode === 'action_validate') {
            this._onClickActionValidate()
        } else if (barcode === 'action_main_menu') {
            this.actionService.doAction({
                type: "ir.actions.client",
                name: 'Barcode',
                tag: "cyllo_barcode_tags",
                target: "inline",
            })
        } else {
            var data = await jsonrpc('/barcode/batch-barcode', {
                'code': barcode,
                'id': this.id,
                'picking_type': this.state.data.picking_type,
                'locations': this.locations,
            })
            if (data.type == 'location') {
                this.locations = data
            } else if (data.type == 'new_lines') {
                this.state.move_line = await this.orm.searchRead(
                    "stock.move.line",
                    [
                        ["batch_id", "=", this.id]
                    ],
                    ["id", "product_id", "quantity_product_uom", "location_id", "location_dest_id", "picking_id", "quantity_product_uom", "tracking"]
                )
            } else if (data.type == 'no_location') {
                this.sound.Danger.play()
                this.notification.add('Please scan the location first', {
                    type: "warning",
                    sticky: false,
                })
            } else {
                this.sound.Danger.play()
                this.notification.add('The product or location is not found for the scanned barcode', {
                    type: "warning",
                    sticky: false,
                })
            }
        }
    }
    /**
     * Function works return to the previous menu
     */
    _onClickExit() {
        this.actionService.doAction({
            type: "ir.actions.client",
            name: 'Batch Transfer',
            tag: "cyllo_batch_client_action",
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
    /**
     * Function for validate function in batch transfer
     */
    _onClickActionValidate() {
        var self = this;
        jsonrpc('/barcode-batch/action_validate', {
            'id': this.id
        }).then(function(response) {
            if (typeof response === 'object') {
                self.actionService.doAction(response)
            } else {
               self.actionService.doAction('soft_reload')
            }
        })
    }

    /**
     * Function for put in pack function in batch transfer
     */
    _onClickActionPackage() {
        jsonrpc('/barcode-batch/action_put_in_pack', {
            'id': this.id
        })
        this.actionService.doAction({
            type: "ir.actions.client",
            name: name,
            tag: "cyllo_batch_lines_client_action",
            target: "current"
        })
    }
    /**
     * Function for displaying the data in the batch transfer view
     */
    async getData() {
        var response = await this.orm.searchRead(
            "stock.picking.batch",
            [["id", "=", this.id]],
            ["name", "picking_type_id", "state"]
        )
        var operation_type = await this.orm.searchRead(
            "stock.picking.type",
            [
                ["id", "=", response[0].picking_type_id[0]]
            ], ["name", "code"]
        )
        this.state.data = {
            'name': response[0].name,
            'picking_id': response[0].picking_type_id[0],
            'picking_type': operation_type[0].code,
            'state': response[0].state
        }
        this.state.move_line = await this.orm.searchRead(
            "stock.move.line",
            [
                ["batch_id", "=", this.id]
            ],
            ["id", "product_id", "quantity_product_uom", "location_id", "location_dest_id", "picking_id", "quantity_product_uom", "tracking"]
        )
    }
}

CylloBarcodeBatchLines.template = "cyllo_barcode.BarcodeBatchTransferLines";
CylloBarcodeBatchLines.components = {
    CylloBarcodeMoveLines
}
actionRegistry.add('cyllo_batch_lines_client_action', CylloBarcodeBatchLines);