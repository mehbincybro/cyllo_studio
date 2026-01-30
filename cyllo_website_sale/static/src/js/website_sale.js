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

    async _onClickAdd(ev) {
        // We must do this before any 'await' to prevent Odoo from submitting the form.
        ev.preventDefault();
        ev.stopImmediatePropagation();

        const _super = this._super.bind(this);
        const self = this;
        const $form = $(ev.currentTarget).closest('form');
        const productId = parseInt($form.find('input[name="product_id"]').val());

        try {
            // Fetch cart and product info
            const cartData = await this.rpc('/shop/cart/get_info_json', {
                product_id: productId
            });

            const hasSubscriptionInCart = cartData.has_subscription;
            const hasNormalInCart = cartData.has_normal;
            const isSubscription = cartData.is_subscription;

            // Logic check for conflicts
            const conflict = (isSubscription && hasNormalInCart) || (!isSubscription && hasSubscriptionInCart);
            console.log(conflict)
            if (conflict) {
                // Show the Dialog
                this.call("dialog", "add", ConfirmationDialog, {
                    title: _t("Cart Conflict"),
                    body:_t("Subscription and non-subscription products cannot be purchased together. Do you want to clear your cart and add this item instead?"),
                    confirmLabel: _t("Clear Cart & Add"),
                    cancelLabel: _t("Cancel"),
                    confirm: async () => {
                        // Use your custom clear cart route
                        await this.rpc("/shop/cart/clear", {});
                        // Call the original Odoo add-to-cart logic
                        return _super(ev);
                    },
                    cancel: () => {
                        // Do nothing: close dialog
                    },
                });
                return Promise.resolve(); // Stop further execution
            }
        } catch (error) {
            console.error("Cart compatibility check failed", error);
        }

        //  If no conflict, manually run the super logic
        return _super(ev);
    },

});

