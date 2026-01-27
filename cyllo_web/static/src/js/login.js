/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.LoginBehavior = publicWidget.Widget.extend({
    selector: '.cy-instance-login',
    events: {
        'click #continue_button': '_onContinueButtonClick',
    },

    start: function () {
        this._super.apply(this, arguments);
        const self = this;
        document.getElementById("login").addEventListener("keydown", function(event) {
            if (event.key === "Enter") {
                event.preventDefault();
                self._onContinueButtonClick(event);
            }
        });
    },

    _onContinueButtonClick: function (ev) {
        ev.preventDefault();

        const $continueButton = this.$('#continue_button');
        const $emailInput = this.$('#login');
        const $passwordGroup = this.$('#password_group');
        const $loginButton = this.$('#login_button');
        const $errorDisplay = this.$('.email-error');

        $errorDisplay.text('').removeClass('cy-input-error').hide();
        $emailInput.css('border-color', '');

        const email = $emailInput.val();

        if (!email) {
            $errorDisplay.text('Email is required').addClass('cy-input-error').show();
            $emailInput.css('border-color', 'red');
            return;
        }

        jsonrpc('/check/mail', { email: email })
            .then((data) => {
                if (data.status === 'error') {
                    $errorDisplay.text(data.message).addClass('cy-input-error').show();
                    $emailInput.css('border-color', 'red');

                    $passwordGroup.hide();
                    $loginButton.hide();
                } else if (data.status === 'success') {
                    $errorDisplay.text('').removeClass('cy-input-error').hide();
                    $emailInput.css('border-color', '');
                    $passwordGroup.addClass('fade-in');
                    $loginButton.show();
                    $continueButton.hide();
                        $loginButton.show();
                        this.$('#password').focus();
                }
            })
            .catch((error) => {
                console.error("ERROR:", error);
                $errorDisplay.text('An unexpected error occurred. Please try again.')
                    .addClass('cy-input-error').show();
                $emailInput.css('border-color', 'red');
            });

    }

})

publicWidget.registry.Signup = publicWidget.Widget.extend({

    selector: '.cy-instance-signup',
    events: {
        'click #signup_button': '_onButtonClick',
    },

    _onButtonClick: function (ev) {
        ev.preventDefault();

        const password = this.$('#password').val();
        const $confirmPasswordInput = this.$('#confirm_password');
        const confirm_password = $confirmPasswordInput.val();
        const $errorDisplay = this.$('.cy-password-error');

        $errorDisplay.text('').removeClass('cy-input-error').hide();
        $confirmPasswordInput.css('border-color', '');

        if (password !== confirm_password) {
            $errorDisplay.text('Passwords do not match')
                .addClass('cy-input-error')
                .show();
            $confirmPasswordInput.css('border-color', 'red');
            return;
        }

        this.$('form[role="form"]').submit();
    }

});