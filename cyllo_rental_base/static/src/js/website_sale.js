/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { websiteSaleCart } from '@website_sale/js/website_sale';
import { jsonrpc } from "@web/core/network/rpc_service";

/**
 * Override websiteSaleCart to edit addresses from rental page.
 */
publicWidget.registry.websiteSaleCart.include({
    events: Object.assign({}, publicWidget.registry.websiteSaleCart.prototype.events, {
        'click .js_change_rental_shipping': '_onClickChangeRentalShipping',
        'click .js_edit_rental_address': '_onClickEditRentalAddress',
    }),
    /**
     * Handle changing shipping address from rental address page.
     */
    _onClickChangeRentalShipping: function(ev) {
        var $old = $('.all_shipping').find('.card.border.border-primary');
        $old.find('.btn-ship').toggle();
        $old.addClass('js_change_rental_shipping');
        $old.removeClass('border border-primary');
        var $new = $(ev.currentTarget).parent('div.one_kanban').find('.card');
        $new.find('.btn-ship').toggle();
        $new.removeClass('js_change_rental_shipping');
        $new.addClass('border border-primary');
        var $form = $(ev.currentTarget).parent('div.one_kanban').find('form.d-none');
        $.post($form.attr('action'), $form.serialize() + '&xhr=1');
    },
    /**
     * Handle editing address from rental address page.
     */
    _onClickEditRentalAddress: function(ev) {
        ev.preventDefault();
        $(ev.currentTarget).closest('div.one_kanban').find('form.d-none').attr('action', '/rental/address').submit();
    },
});
/**
 * Widget for handling rental orders in the shopping cart.
 */
publicWidget.registry.RentalOrderCart = publicWidget.Widget.extend({
    selector: '#rental_cart',
    events: {
        'click .js_rental_add_cart_json': '_onClickCartQtyUpdate'
    },
    /**
     * Handle updating quantity in the rental cart.
     */
    _onClickCartQtyUpdate(ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var $input = $link.closest('.input-group').find("input");
        var min = parseFloat($input.data("min") || 0);
        var max = parseFloat($input.data("max") || Infinity);
        var previousQty = parseFloat($input.val() || 0, 10);
        var quantity = ($link.has(".fa-minus").length ? -1 : 1) + previousQty;
        var newQty = quantity > min ? (quantity < max ? quantity : max) : min;
        if (newQty !== previousQty) {
            $input.val(newQty).trigger('change');
            this._updateRentalCart(ev)
        }
        return false;
    },
    /**
     * Update rental cart asynchronously.
     */
    async _updateRentalCart(ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var $line_id = $link.closest('.o_cart_product').find('#line_id')
        var $product_id = $link.closest('.o_cart_product').find('#product_id')
        var $input = $link.closest('.input-group').find("input");
        var $order_id = $link.closest('.js_rental_cart_lines').find("#order_id");
        var $line_sub_total = $link.closest('.o_cart_product').find(".line_sub_total");
        await jsonrpc('/update/rental/cart', {
            'product_id': parseInt($product_id.val()),
            'line_id': parseInt($line_id.val()),
            'quantity': parseInt($input.val()),
            'order_id': parseInt($order_id.val()),
        }).then(function(result) {
            if (result['reload']) {
                window.location.reload()
            } else {
                result['line_id'] = $line_id.val()
            }
            updateRentalCartNavBar(result);
        })
    },
});
export default publicWidget.registry.RentalOrderCart;
/**
 * Function to update the rental cart navbar.
 * @param {Object} data - Data for updating the navbar.
 */
function updateRentalCartNavBar(data) {
    sessionStorage.setItem('rental_cart_quantity', data.total_quantity);
    $(".my_rental_cart_quantity")
        .parents('li.o_wsale_my_cart').removeClass('d-none').end()
        .toggleClass('d-none', data.total_quantity === 0)
        .addClass('o_mycart_zoom_animation').delay(300)
        .queue(function() {
            $(this)
                .toggleClass('fa fa-warning', !data.line_sub_total)
                .attr('title', data.warning)
                .text(data.rental_cart_quantity || '')
                .removeClass('o_mycart_zoom_animation')
                .dequeue();
        });
    $('#' + data.line_id).replaceWith(data['re_render'])
    $('.o_rental_total_card').replaceWith(data['rental_total_template'])
}
export default {
    updateRentalCartNavBar: updateRentalCartNavBar,
};