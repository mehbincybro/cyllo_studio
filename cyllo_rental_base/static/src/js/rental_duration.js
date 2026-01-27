/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import Dialog from "@web/legacy/js/core/dialog";
import { jsonrpc } from "@web/core/network/rpc_service";
import { session } from "@web/session";
import { useService } from "@web/core/utils/hooks";
let currency_symbol;
// Define a new widget named 'RentalOrder' that extends the 'publicWidget.Widget' class
publicWidget.registry.RentalOrder = publicWidget.Widget.extend({
    selector: '.rental_dates',
    events: {
        'change #return_date': '_rental_duration',
        'change #quantity': '_order_total',
    },
    setup() {
        this.orm = useService('orm');
        this.rpc = useService("rpc");
    },
    start: function() {
        /**
         * Initialize the widget.
         */
        // Setting default time and dates
        this.$("#product_id").val(this.$('#p_id').html());
        this.$("#product_name").val(this.$('#p_name').html());
        this.$("#quantity").val(1);
    },
    /**
     * Calculate rental duration and pricing based on selected dates.
     */
    _rental_duration: async function() {
        var startDate = Date.parse(this.$("#pickup_date").val());
        var endDate = Date.parse(this.$("#return_date").val());
        var p_id = this.$('#p_id').html();
        let dates = {
            'start_date': startDate,
            'end_date': endDate
        };
        try {
            let data = await jsonrpc('/rental_charge', {
                'p_id': p_id,
                data: 'data',
                dates: dates
            });
            if (this.$("#pickup_date").val() > this.$("#return_date").val()) {
                Dialog.alert(this, "End date should be greater than Start date");
                this.$("#return_date").val('');
            }
            if (data['duration']){
                currency_symbol = data['currency_symbol'];
                let sub_total = data['sub_total'];
                this.$('#duration').val(data['duration']);
                this.$("#total").val(currency_symbol + ' ' + sub_total);
                this.$("#amount").val(sub_total);
                this.$('#price_total').val(currency_symbol + '' + sub_total);
                this._order_total()
            }else{
                Dialog.alert(this, "Choose a minimum of 1 hour for rent");
                this.$("#return_date").val('');
            }
        } catch (error) {
            console.error("Error fetching rental data:", error);
        }
    },
    /**
     * Calculate the total amount.
     */
    _order_total: async function() {
        const quantity = parseFloat(this.$("#quantity").val());
        const match = this.$("#total").val().match(/(\D+)(\d+)/)
        const product = await jsonrpc('/rental/product',{
            'product_id':this.$('#p_id')[0].innerHTML
        });
        if (product[0].qty_available < quantity) {
            this.$("#quantity").val(product[0].qty_available);
            Dialog.alert(this, "Only " + product[0].qty_available + " is available");
        }
        const total_amount = match ? parseInt(match[2]) : 0;
        this.$('#price_total').val(currency_symbol + '' + total_amount * (product[0].qty_available < quantity ? product[0].qty_available : quantity));
    },
});
export default publicWidget.registry.RentalOrder;