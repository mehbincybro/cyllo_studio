/** @odoo-module **/
import { registry } from "@web/core/registry";
import { BarcodeDialog } from "./barcode_dialog";
import { Component,useState, useRef } from "@odoo/owl";
import { useService, useBus } from "@web/core/utils/hooks";
import { CylloBarcodeLocationLines } from "./barcode_location_lines"
import { jsonrpc } from "@web/core/network/rpc_service";

const actionRegistry = registry.category("actions");
export class CylloBarcodeLocation extends Component {
    setup() {
        const barcode = useService("barcode");
        this.id = localStorage.getItem("cyllo-barcode-inventory")
        this.type = localStorage.getItem("cyllo-barcode-inventory-type")
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.sound = useService("barcodeSound");
        this.actionService = useService("action")
        this.notification = useService("notification")
        this.state = useState({
            transfer: [],
            data: [],
            selected_move: [],
            lot_move: []
        })
        this.getData()
        useBus(barcode.bus, "barcode_scanned", (ev) => this.BarcodeReader(ev.detail.barcode))
        useBus(this.env.bus, 'barcode-cancel-stock-move', (ev) => this._onClickCancelSelected(ev.detail.id));
        useBus(this.env.bus, 'barcode-applying-multi-stock-quantity', (ev) => this.MultiApplyQuantity(ev.detail));
        this.root = useRef('BarcodeLocationRoot')

    }
    /**
     * Function for return the corresponding picking
     */
    _onClickReturn() {
        if (this.state.data.state == 'done') {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: 'stock.return.picking',
                name: 'Reverse Transfer',
                views: [
                    [false, "form"]
                ],
                target: "new",
                context: {
                    active_id: Number(this.id),
                    active_model: 'stock.picking'
                },
            })
        } else {
            this.notification.add('Please validate the order first.', {
                type: "danger",
                sticky: true,
            })
        }
    }

    /**
     * Function change the data from the list that are confirmed
     */
    MultiApplyQuantity(data) {
        if (data.value) {
            this.state.selected_move.push(data.id)
        } else {
            this.state.selected_move = this.state.selected_move.filter(item => item !== data.id)
        }
    }
    /**
     * Function for cancelling the selected records in the view
     */
    _onClickCancelSelected(id) {
        this.orm.unlink("stock.move", [Number(id)])
        this.state.transfer = this.state.transfer.filter(item => ![id].includes(item.id))
    }
    /**
     * Function for displaying the data in the inventory transfers
     */
    async getData() {
        var response = await this.orm.searchRead(
            "stock.picking",
            [["id", "=", this.id]],
            ["id", "name", "location_id", "location_dest_id", "state"]
        )
        this.state.data = {
            'name': response[0].name,
            'state': response[0].state,
            'location': response[0].location_id[0],
            'location_name': response[0].location_id[1],
            'destination': response[0].location_dest_id[1],
            'destination_id': response[0].location_dest_id[0]
        }
        this.state.transfer = await jsonrpc('/barcode-location/get-product-data', {
            'pick_id': this.id
        })
    }
    /**
     * Function for returns to the previous menu
     */
    OpenMainScreen() {
        this.actionService.doAction({
            type: "ir.actions.client",
            tag: this.props.action.context.menu ? this.props.action.context.menu : "cyllo_barcode_tags",
            name: this.props.action.context.menu ? 'Operation' : 'Barcode',
            target: "inline",
        })
    }
    /**
     * Function for open web cam and scan the barcode
     */
    _onClickScanProduct() {
        this.dialog.add(BarcodeDialog, {
            title: 'Barcode Scanner',
            ReadBarcode: (result) => {
                this.BarcodeReader(result)
            }
        })
    }
    /**
     * Function for the action confirm in stock.picking
     */
    async _onClickApplyPicking() {
        var self = this
        var response = await jsonrpc('/barcode-location/product-barcode-confirm', {
            'pick_id': self.id
        })
        if (response != true) {
            self.actionService.doAction(response)
        } else {
            this.actionService.doAction('soft_reload')
        }
    }
    /**
     * Function for checking the product is with lot or serial.
     */
    async BarcodeReader(barcode) {
        barcode = String(barcode)
        if (this.state.lot_move.length > 0) {
            var product = await this.orm.searchRead("product.product", [
                ["barcode", "=", barcode]
            ]);
            if (product.length > 0) {
                var move = this.state.transfer.find(move => move['id'] === this.state.lot_move[0])
                move.open_modal = 'close'
                this.ReadBarcode(barcode)
            } else {
                var move = this.state.transfer.find(move => move['id'] === this.state.lot_move[0])
                var move_line = await this.orm.searchRead("stock.move.line", [
                        ["move_id", "=", this.state.lot_move[0]],
                    ], [])
                if (move.operation_type === 'incoming') {
                    var move_line_no_lot = await this.orm.searchRead("stock.move.line", [
                        ["move_id", "=", this.state.lot_move[0]],["lot_name", "=", false]
                    ], [])
                    var same_line = move_line.find(line => line.lot_name === barcode);
                    if (same_line) {
                        if(same_line.lot_serial_name){
                            this.sound.Alert.play()
                            this.notification.add(
                                'The Lot/Serial number ('+ barcode +') is already scanned'
                            )
                        }else{
                            await this.orm.write("stock.move.line", [same_line.id], {
                                lot_serial_name: barcode,
                            });
                            this.sound.Success.play()
                            var _move_line = move.move_line_ids.find(move_id => move_id['id'] === same_line.id)
                            move.line_quantity += same_line.quantity
                            _move_line.lot_serial_name = barcode
                            var move_line_no_lot_name = await this.orm.searchRead("stock.move.line", [
                                ["move_id", "=", this.state.lot_move[0]],["lot_serial_name", "=", false]
                            ], [])
                            if(move_line_no_lot_name.length == 0){
                                move.open_modal = 'close'
                                this.state.lot_move = []
                            }
                        }
                    }else if(move_line_no_lot.length > 0){
                        await this.orm.write("stock.move.line", [move_line_no_lot[0].id], {
                            lot_name: barcode,
                            lot_serial_name: barcode
                        });
                        this.sound.Success.play()
                        var _move_line = move.move_line_ids.find(move_id => move_id['id'] === move_line_no_lot[0].id)
                        move.line_quantity += _move_line.quantity
                        _move_line.lot_serial_name = barcode

                    }else{
                         this.notification.add('Please scan valid Lot/Serial number or Another product', {
                            type: "warning",
                            sticky: false,
                        })
                        this.sound.Danger.play()
                    }
                } else if (['internal', 'outgoing'].includes(move.operation_type)) {
                    var same_line = move_line.find(line => line.lot_id[1] === barcode);
                    var move_line_no_lot = await this.orm.searchRead("stock.move.line", [
                        ["move_id", "=", this.state.lot_move[0]],["lot_id", "=", false]
                    ], [])
                    if(same_line){
                        if(same_line.lot_serial_name){
                            this.sound.Alert.play()
                            this.notification.add(
                                'The Lot/Serial number ('+ barcode +') is already scanned'
                            )
                        }else{
                            await this.orm.write("stock.move.line", [same_line.id], {
                                lot_serial_name: barcode,
                            });
                            this.sound.Success.play()
                            var _move_line = move.move_line_ids.find(move_id => move_id['id'] === same_line.id)
                            move.line_quant_int += same_line.quantity
                            _move_line.lot_serial_name = barcode
                            var move_line_no_lot_name = await this.orm.searchRead("stock.move.line", [
                                ["move_id", "=", this.state.lot_move[0]],["lot_serial_name", "=", false]
                            ], [])
                            if(move_line_no_lot_name.length == 0){
                                move.open_modal = 'close'
                                this.state.lot_move = []
                            }
                        }
                    }else if(move_line_no_lot.length > 0){
                        var stock_lot = await this.orm.searchRead("stock.lot", [
                            ["product_id", "=", move.product],
                            ["name", "=", barcode]
                        ]);
                        if (stock_lot.length == 0) {
                            this.notification.add('Please scan the valid Lot / Serial Number.', {
                                type: "warning",
                                sticky: false,
                            })
                        } else {
                            var stock_quant = await this.orm.searchRead("stock.quant", [
                                ["product_id", "=", move.product],
                                ["lot_id", "=", stock_lot[0].id],
                                ['location_id.usage', '=', 'internal']
                            ]);
                            var exist_lot = stock_quant.find(quant => quant.location_id[0] === this.state.data.location)
                            if (exist_lot) {
                                var move_line = await this.orm.searchRead("stock.move.line", [
                                    ["move_id", "=", this.state.lot_move[0]],
                                    ["lot_id", "=", false]
                                ], [])
                                await this.orm.write("stock.move.line", [move_line[0].id], {
                                    lot_id: exist_lot.lot_id[0],
                                    lot_serial_name: barcode,
                                });
                                var _move_line = move.move_line_ids.find(move_id => move_id['id'] === move_line[0].id)
                                move.line_quant_int += _move_line.quantity
                                _move_line.lot_serial_name = barcode
                                _move_line.lot_id = [exist_lot.lot_id[0], barcode]
                            } else {
                                this.sound.Alert.play()
                                this.notification.add(
                                    'Serial number (' + barcode + ') is not located in' + this.state.data.location_name + ', but it is located in location(s):' + stock_quant.map(quant => quant.location_id[1]).join(", ")
                                )
                            }
                        }
                    }else {
                        this.notification.add('Please scan valid Lot/Serial number or Another product', {
                            type: "warning",
                            sticky: false,
                        })
                        this.sound.Danger.play()
                    }
                }
            }
        } else {
            this.ReadBarcode(barcode)
        }
    }
    /**
     * Function works when the barcode catches the barcode code and passing the code to python
     */
    async ReadBarcode(barcode) {
        var self = this
        if (['action_slip', 'action_picking', 'action_components'].includes(barcode)) {
            jsonrpc('/inventory_commands', {
                'code': barcode,
                'id': this.id
            }).then(function(result) {
                if (result != true) {
                    self.actionService.doAction(result)
                }
            })
        } else if (barcode === 'action_main_menu') {
            this.actionService.doAction('cyllo_barcode.cyllo_barcode_action')
        } else if (barcode === 'action_return') {
            self._onClickReturn()
        } else if (this.state.data.state != 'done') {
            if (barcode === 'action_cancel') {
                this.sound.Alert.play()
                this.orm.call("stock.picking", "action_cancel", [Number(this.id)]);
                this.notification.add('The operation has been canceled.', {
                    type: "warning",
                    sticky: false,
                })
            } else if (barcode === 'action_validate') {
                self._onClickApplyPicking()
            } else {
                var data = await jsonrpc('/barcode-location/product-barcode', {
                    'code': barcode,
                    'location_id': this.state.data.location,
                    'destination': this.state.data.destination_id,
                    'pick_id': this.id
                })
                if (data.type === 'location') {
                    this.orm.write('stock.picking', [Number(this.id)], {
                        'location_dest_id': data.id
                    })
                    this.notification.add('The destination location is updated as ' + data.name, {
                        type: "success",
                        sticky: false,
                    })
                } else if (data.type === 'exist_product_lot') {
                    var move = this.state.transfer.find(move => move['id'] === data.id)
                    move.open_modal = 'open'
                    this.state.lot_move = []
                    this.state.lot_move.push(data.id)
                    this.sound.Success.play()
                    this.notification.add('Please scan a the Lot number or scan another product', {
                        type: "warning",
                        sticky: false,
                    })
                } else if (data.type === 'exist_product_serial') {
                    this.sound.Success.play()
                    this.notification.add('Please scan a the serial number or scan another product', {
                        type: "warning",
                        sticky: false,
                    })
                    this.state.transfer.find(move => move['id'] === data.id).open_modal = 'open'
                    this.state.lot_move = []
                    this.state.lot_move.push(data.id)
                } else if (data.type === 'product') {
                    this.state.transfer.push(data)
                } else if (data.type === 'no_package') {
                    this.sound.Alert.play()
                    this.notification.add('Please scan the valid package', {
                        type: "warning",
                        sticky: false,
                    })
                } else if (data.type === 'exist_product') {
                    var move = this.state.transfer.find(move => move['id'] === data.id)
                    move.quantity = data.quantity
                    move.move_line_ids = data.move_lines
                } else if (data.type == 'not_storable') {
                    this.sound.Alert.play()
                    this.notification.add('The product ' + data.name + ' is not a storable product please scan a storable product', {
                        type: "warning",
                        sticky: false,
                    })
                } else {
                    this.sound.Alert.play()
                    this.notification.add('Product or Location is not found, try again', {
                        type: "warning",
                        sticky: false,
                    })
                }
            }
        } else {
            this.sound.Danger.play()
            this.notification.add('This picking is already done please create another one', {
                type: "danger",
                sticky: false,
            })
        }

    }
}

CylloBarcodeLocation.template = "cyllo_barcode.BarcodeLocation";
CylloBarcodeLocation.components = {
    CylloBarcodeLocationLines
}
actionRegistry.add('cyllo_location_client_action', CylloBarcodeLocation);