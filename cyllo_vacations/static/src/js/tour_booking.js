/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.TourBookingForm = publicWidget.Widget.extend({
    selector: '.js_tour_booking_form',
    events: {
        'change .js_num_passengers': '_onPassengerChange',
        'input .js_num_passengers': '_onPassengerChange',
        'change .js_customization_option': '_onCustomizationChange',
    },

    start: function () {
        this._super.apply(this, arguments);
        // Get package data from form attributes for client-side calculation
        this.packageId = this.$el.data('package-id');
        this.priceType = this.$el.data('price-type');
        this.adultPrice = parseFloat(this.$el.data('adult-price')) || 0;
        this.childPrice = parseFloat(this.$el.data('child-price')) || 0;
        this.infantPrice = parseFloat(this.$el.data('infant-price')) || 0;
        this.currency = this.$el.data('currency') || '';
        // Update price immediately
        this._updatePrice();
    },

    _onPassengerChange: function () {
        this._updatePrice();
    },

    _onCustomizationChange: function () {
        this._updatePrice();
    },

    _getPassengerCounts: function () {
        return {
            adults: parseInt(this.$('#num_adults').val()) || 1,
            children: parseInt(this.$('#num_children').val()) || 0,
            infants: parseInt(this.$('#num_infants').val()) || 0,
        };
    },

    _formatPrice: function (price) {
        return this.currency + ' ' + price.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    },

    _calculateClientSidePrice: function () {
        const counts = this._getPassengerCounts();
        let total = 0;
        
        if (this.priceType === 'per_person') {
            total += counts.adults * this.adultPrice;
            total += counts.children * this.childPrice;
            total += counts.infants * this.infantPrice;
        } else {
            total = this.adultPrice; // For per_package, use the base price
        }

        this.$('.js_customization_option:checked').each((index, input) => {
            const priceExtra = parseFloat(input.dataset.priceExtra) || 0;
            const priceApplication = input.dataset.priceApplication || 'per_booking';
            let quantity = 1;
            if (priceApplication === 'per_person') {
                quantity = counts.adults + counts.children + counts.infants;
            } else if (priceApplication === 'per_adult') {
                quantity = counts.adults;
            } else if (priceApplication === 'per_child') {
                quantity = counts.children;
            } else if (priceApplication === 'per_infant') {
                quantity = counts.infants;
            }
            total += priceExtra * quantity;
        });

        return total;
    },

    _getSelectedOptionLineIds: function () {
        const selectedOptionLineIds = [];
        this.$('.js_customization_option:checked').each((index, input) => {
            selectedOptionLineIds.push(parseInt(input.value));
        });
        return selectedOptionLineIds.filter(Boolean);
    },

    async _updatePrice() {
        const counts = this._getPassengerCounts();
        
        // Show client-side calculated price immediately for responsiveness
        const clientSideTotal = this._calculateClientSidePrice();
        this.$('.js_total_price').text(this._formatPrice(clientSideTotal));

        // Also fetch from server to ensure accuracy
        try {
            const result = await jsonrpc('/tour/calculate-price', {
                package_id: this.packageId,
                num_adults: counts.adults,
                num_children: counts.children,
                num_infants: counts.infants,
                option_line_ids: this._getSelectedOptionLineIds(),
            });
            
            if (result.success) {
                this.$('.js_total_price').text(result.formatted_total);
                this.$('.js_total_price').data('currency-symbol', result.currency);
            } else if (result.error) {
                console.error('Price calculation error:', result.error);
            }
        } catch (error) {
            console.error('RPC error:', error);
            // Keep client-side calculated price as fallback
        }
    },
});

export default publicWidget.registry.TourBookingForm;

