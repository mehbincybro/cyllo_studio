/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.TourInquiryForm = publicWidget.Widget.extend({
    selector: '.js_tour_inquiry_form',
    events: {
        'submit': '_onFormSubmit',
        'change #package_id': '_onPackageChange',
    },

    start: function () {
        this._super.apply(this, arguments);
        this._updateCustomizationGroups();
    },

    _onPackageChange: function () {
        this._updateCustomizationGroups();
    },

    _onFormSubmit: function (ev) {
        const packageId = this.$('#package_id').val();
        if (!packageId) {
            ev.preventDefault();
            alert('Please select a tour package');
            return false;
        }
        
        const email = this.$('#customer_email').val();
        if (email && !this._validateEmail(email)) {
            ev.preventDefault();
            alert('Please enter a valid email address');
            return false;
        }
        
        return true;
    },

    _updateCustomizationGroups: function () {
        const packageId = this.$('#package_id').val();
        this.$('.js_package_customization_group').each((index, group) => {
            const isActive = String(group.dataset.packageId) === String(packageId);
            group.style.display = isActive ? 'block' : 'none';
            const inputs = group.querySelectorAll('.js_customization_option');
            inputs.forEach((input) => {
                input.disabled = !isActive;
                input.required = isActive && input.dataset.required === '1';
            });
            if (isActive) {
                const requiredNames = new Set();
                inputs.forEach((input) => {
                    if (input.dataset.required === '1') {
                        requiredNames.add(input.name);
                    }
                });
                requiredNames.forEach((name) => {
                    const groupInputs = group.querySelectorAll(`input[name="${name}"]`);
                    if (!Array.from(groupInputs).some((input) => input.checked) && groupInputs.length) {
                        groupInputs[0].checked = true;
                    }
                });
            }
        });
    },

    _validateEmail: function (email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    },
});

export default publicWidget.registry.TourInquiryForm;

