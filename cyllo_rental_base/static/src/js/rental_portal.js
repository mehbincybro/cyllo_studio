/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import Dialog from "@web/legacy/js/core/dialog";
import { jsonrpc } from "@web/core/network/rpc_service";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
publicWidget.registry.RentalOrderPortal = publicWidget.Widget.extend({
    selector: '.o_portal_rental_order_sidebar',
    start: function() {
        this.return_line_ids = []
        this.orm = this.bindService("orm");
    },
    events: {
        'click .button_return': 'rental_return',
        'click #confirm_return_rental':'_onClickConfirmRental',
        'change #picking_selection' : '_onChangePicking',
        'change .o_rental_input_quantity': '_onChangeQuantity'
    },

    async _onChangePicking(ev){
        if(ev.target.value){
            var response = await jsonrpc('/create/stock-return-orders',{
                'pick_id':ev.target.value,
            })
            this.el.querySelector('#confirm_return_rental').value = response.pick_id
            this.modalTableBody.empty()
            for (const line of response.lines) {
                const row = `<tr>
                <td>${line.name}</td>
                <td><input  id="${line.id}" value="${line.quantity}" class="form-control o_rental_input_quantity"/></td>
                </tr>`;
                this.modalTableBody.append(row);
            }
        }
    },
    _onClickConfirmRental(ev){
        jsonrpc('/confirm/stock-return-orders',{
            'pick_id':ev.target.value
        }).then(()=>{
            window.location.reload()
        })
    },
    async _onChangeQuantity(ev){
        var response = await jsonrpc('/update/stock-return-orders',{
            'pick_id':ev.target.id, 'quantity': ev.target.value
        })
    },
    async rental_return() {
        this.modalTableBody = this.$('#modalTableBody');
        this.$('#RentalReturnModal').modal('show');
    }
})
export default publicWidget.registry.RentalOrderPortal;
