/** @odoo-module **/

import {WebsiteSale} from "@website_sale/js/website_sale";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

WebsiteSale.include({
    selector: '.oe_website_sale',
    events: Object.assign({}, WebsiteSale.prototype.events, {
        'change .js_subscription_plan_select': '_onChangeSubscriptionPlan',
    }),

    /**
     * Handles the change event for the subscription plan selector.
     * * Updates the displayed product price on the page based on the
     * selected plan's data attributes and stores the selected plan ID.
     */

    _onChangeSubscriptionPlan: function (ev) {
        const $select = $(ev.currentTarget);
        const $selectedOption = $select.find('option:selected');

        // Get price and unit from the data attributes
        const price = $selectedOption.data('price');

        // Locate the price display elements on the Odoo product page
        const $priceElement = $('.oe_price .oe_currency_value');

        if (price !== undefined) {

            $priceElement.text(parseFloat(price).toFixed(2));
        }
        this.planId = $selectedOption.val();
    },

    /**
     * @override
     * This is the method that actually builds the JSON-RPC request.
     * We inject the plan ID here so it reaches the Python kwargs.
     */

    _getOptionalCombinationInfoParam: function (product) {
        // Call the original method using Odoo's legacy _super
        var res = this._super.apply(this, arguments) || {};

        // Append your plan_id
        if (this.planId) {
            res['plan_id'] = this.planId;
        }

        return res;
    },
    /**
     * Ensures data is also sent when clicking 'Add to Cart'
     */
    _updateRootProduct: function ($form, productId) {
        this._super(...arguments);
        const $planSelect = $form.find('.js_subscription_plan_select');
        if ($planSelect.length) {
            this.rootProduct.time_based_price_id = parseInt($planSelect.val());
            this.rootProduct.end_date = $form.find('input[name="end_date"]').val();
        }
    },
 /**
 * @override
 * Intercept the add to cart click
 */
async _onClickAdd(ev) {
    const $form = this.$el.find('form[action^="/shop/cart/update"]');
    const isSubscription = $form.find('.js_subscription_plan_select').length > 0;

    // Fetch current cart info from the server
    const cartData = await this.rpc('/shop/cart/get_info_json');

    const hasSubscriptionInCart = cartData.has_subscription;
    const hasNormalInCart = cartData.has_normal;

    // Check for incompatible products
    if ((isSubscription && hasNormalInCart) || (!isSubscription && hasSubscriptionInCart)) {
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Your cart contains incompatible items. Subscription and non-subscription products cannot be purchased together. Do you want to clear your cart and add this item instead?"),
            confirmLabel: _t("Clear Cart & Add"),
            cancelLabel: _t("Cancel"),
            confirm: async () => {
                await this.rpc("/shop/cart/clear");
                await super._onClickAdd(ev); // Proceed with adding the product
            },
            cancel: () => {
                // Do nothing, just close the modal
            },
        });
        return; // Stop normal execution
    }

    // No conflicts, proceed normally
    return super._onClickAdd(ev);
}

});

