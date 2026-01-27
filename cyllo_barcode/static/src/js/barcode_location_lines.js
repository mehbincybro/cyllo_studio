/** @odoo-module */
import { Component, useRef, useState, onPatched} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
export class CylloBarcodeLocationLines extends Component {
    setup() {
        this.root = useRef('root-LocationLines')
        this.sound = useService("barcodeSound");
        this.state = useState({
            transfer: this.props.transfer,
            move_lines: this.props.transfer.move_line_ids,
            destination: this.props.destination,
            open_modal: this.props.open_modal
        })
        this.notification = useService("notification")
        this.actionService = useService("action")
        this.orm = useService("orm")
        onPatched(() => {
            var value = (this.state.transfer.open_modal == 'open') ? true : false
            this._onClickOpenModal(value)
        })
    }
    /**
     * Function for opening modal based on the scanned products tracking
     */
    _onClickOpenModal(value) {
        if (value) {
            this.root.el.querySelector('#MoveLinesModal').style.display = 'block'
        } else {
            this.root.el.querySelector('#MoveLinesModal').style.display = 'none'
            this.actionService.doAction('soft_reload')
        }
    }
    UpdateQuantity(value) {
        this.state.transfer.quantity = value
        this.orm.write('stock.move', [this.state.transfer.id], {
            'done_quantity': Number(value),
            'with_barcode': true
        })
    }
    /**
     * Function to assign serial numbers.
     */
    async OnAssign(serial, count) {
        try {
            await this.orm.call("stock.move", "generate_serial_numbers", [this.props.transfer.id, {
                'sn': serial,
                'count': this.state.transfer.quantity
            }]);
            this.state.move_lines = await this.orm.searchRead('stock.move.line', [
                ['move_id', '=', this.props.transfer.id]
            ], []);
            this.actionService.doAction('soft_reload')
        } catch (error) {
            //             Handle errors if any
            alert("Error:", error);
        }
    }
    /**
     * Function to assign lot numbers.
     */
    async OnAssignLots(value) {
        if (!value) {
            this.sound.Alert.play()
            this.notification.add('Please add Lot Number', {
                type: "danger",
                sticky: false,
            })
        } else {
            var qty_done = this.root.el.querySelector('.input_for_quantity').value;
            var stock_move_line = await this.orm.searchRead('stock.move.line', [
                ['move_id', '=', this.props.transfer.id],
                ['lot_name', '=', false]
            ]);
            if (stock_move_line.length > 0) {
                var lots = await this.orm.write('stock.move.line', [stock_move_line[0].id], {
                    'lot_name': value
                })
                this.state.move_lines = await this.orm.searchRead('stock.move.line', [
                    ['move_id', '=', this.props.transfer.id]
                ], []);
            }
            this.notification.add('Lot Number', {
                type: "success",
                sticky: false,
            })
            this.actionService.doAction('soft_reload')
        }
    }
    /**
     * Function for invisible the modal
     */
    _onClickDiscardChanges() {
        this.root.el.querySelector('#LocationLinesModal').style.display = 'none'
        this.root.el.querySelector('.input_for_quantity').value = this.state.transfer.quantity
        this.is_float = false;
    }
    /**
     * Function trigger 'barcode-cancel-stock-quantity' bus for removing data from the Barcode product view c
     */
    _onclickCancel() {
        this.env.bus.trigger('barcode-cancel-stock-move', {
            id: this.state.transfer.id
        });
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
     * Function for apply button in the modal for changing the quantity of the record
     */
    _onClickApplyChanges(value) {
        this.state.transfer.quantity = value
        this.orm.write('stock.move', [this.state.transfer.id], {
            'done_quantity': Number(value),
            'with_barcode': true
        })
        this.root.el.querySelector('#LocationLinesModal').style.display = 'none'
        this.is_float = false;

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
     * While double clicking the card removing applying the custom style and passing id using bus
     */
    onDblClick() {
        if (this.props.type === 'location') {
            this.state.transfer.value = !this.state.transfer.value
            if (this.state.transfer.value) {
                this.root.el.classList.add("barcode-card-active");
            } else {
                this.root.el.classList.remove("barcode-card-active");
            }
            this.env.bus.trigger('barcode-applying-multi-stock-quantity', {
                id: this.state.transfer.id,
                value: this.state.transfer.value
            })
        }
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
    /**
     * Function for applying the decimal value in the quantity
     */
    _onClickDialDecimal() {
        if (this.root.el.querySelector('.input_for_quantity').value.indexOf('.') === -1) {
            this.is_float = true;
        }
    }
    /**
     * Function for increment or decrement the quantity of the record by 1
     */
    _onClickExternalOperation(operation) {
        if (operation == 'minus') {
            this.state.transfer.quantity--
        } else {
            this.state.transfer.quantity++
        }
        this.orm.write('stock.move', [this.state.transfer.id], {
            'done_quantity': this.state.transfer.quantity,
            'with_barcode': true
        })
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
}
CylloBarcodeLocationLines.template = "cyllo_barcode.BarcodeLocationLines";