/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { jsonrpc } from "@web/core/network/rpc_service";
import { RecentTab } from '@cyllo_twilio_voice_call/js/recent_tab'
import { ContactTab } from '@cyllo_twilio_voice_call/js/contact_tab'
var device;

export class DialPad extends Component {
    static template = "dial_pad";
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.keys = useRef("keys");
        this.clear = useRef("clear");
        this.outgoing = useRef("keypad")
        this.notification = useService("notification");
        this.sid = null; // Initialize callSid as null
        this.number = null;
        this.PhoneNumber = null,
            this.callAction = null,
            this.timer = null,
        this.orm = useService("orm");
        onMounted(() => this.fetch_data());
        this.state = useState({
            value: false,
            selectedPartner: null,
            duration: 0,
            wasRejected: false,
            recent: false,
            contacts: false,
            isPartner: false,
            isRejected:false,
            cancel:false
        })
        this.isTimerPaused = false;
    }
    /* The function 'fetch_data' for initializing the device,
       and creating the access token for making and receiving the calls
     */
    fetch_data() {
        var self = this;
        var def1 = jsonrpc('/access/token', {}).then(function(data) {
            device = new Twilio.Device(data, {
                // Set Opus as our preferred codec. Opus generally performs better, requiring less bandwidth and
                // providing better audio quality in restrained network conditions. Opus will be default in 2.0.
                codecPreferences: ["opus", "pcmu"],
                // Use fake DTMF tones client-side. Real tones are still sent to the other end of the call,
                // but the client-side DTMF tones are fake. This prevents the local mic capturing the DTMF tone
                // a second time and sending the tone twice. This will be default in 2.0.
                fakeLocalDTMF: true,
                // Use `enableRingingState` to enable the device to emit the `ringing`
                // state. The TwiML backend also needs to have the attribute
                // `answerOnBridge` also set to true in the `Dial` verb. This option
                // changes the behavior of the SDK to consider a call `ringing` starting
                // from the connection to the TwiML backend to when the recipient of
                // the `Dial` verb answers.
                enableRingingState: true,
            });
            self.device = device;
            /*
               Device must be registered in order to receive incoming calls
            */
            device.register();
        });
        return $.when(def1);
    }
    /*
       This functions are used to get the time counter or the duration of the calls,
       when accepting the call even if it is outgoing or incoming.
     */
    _runTimer() {
        if (!this.isTimerPaused) {
            this.timer = setTimeout(() => {
                this.state.duration += 1;
                this._runTimer();
            }, 1000);
        }
    }

    resetTimer() {
        clearTimeout(this.timer);
        this.isTimerPaused = true;
        this.state.duration = 0;
    }

    get timeFormatted() {
        const minutes = Math.floor(this.state.duration / 60);
        const seconds = this.state.duration % 60;
        return `${minutes}:${seconds < 10 ? "0" : ""}${seconds}`;
    }

    /*
       The function is used to clear the numbers in the screen
    */
    _onClickScreen(event) {
        const clickedButton = event.target;
        if (clickedButton.classList.contains('cy-dialing-nmbr')) {
            const buttonText = clickedButton.textContent;
            this.keys.el.value += buttonText;
        }
    }

    /* To Clear the numbers */
    _OnClear() {
        this.keys.el.value = this.keys.el.value.slice(0, -1);
    }

    /*
        To create the display notification
    */
    displayNotification(text) {
        this.notification.add(text, {
            type: "warning"
        });
    }
    /*
        The function is used to check the number is valid or note
    */
    _isValidPhoneNumber(number) {
        // Regex for numbers with a country code
        const phoneRegex = /^\+\d{1,3}\d{4,}$/;
        return phoneRegex.test(number);
    }

    /*
        For making outgoing calls
    */
    async _onClickCall() {
        var self = this;
        const callButton = this.outgoing.el.querySelector('.cy-call-btn');
        const callClear = this.outgoing.el.querySelector('.cy-dial_clearbtn');
        this.PhoneNumber = this.keys.el.value
        const PartnerId = await this.orm.searchRead("res.partner", [
            ["phone", "=", this.PhoneNumber]
        ], ['image_1920', 'name']);
        if (PartnerId && PartnerId.length > 0) {
            this.state.selectedPartner = PartnerId
            this.state.isPartner = true
            this.state.selectedPartner.image_1920 = PartnerId[0].image_1920;
            this.state.selectedPartner.partner_name = PartnerId[0].name;
        }
        if (PartnerId && PartnerId.length > 0) {
            var id = PartnerId[0].id
        } else {
            var id = null
        }
        if (this.PhoneNumber) {
            if (!this._isValidPhoneNumber(this.PhoneNumber)) {
                this.displayNotification(_t("Please enter the correct phone number with the country code"))
            } else {
                var params = {
                    To: this.PhoneNumber,
                };
                event.stopPropagation();
                if (self.device) {
                    try {
                        const call = await device.connect({
                            params
                        });
                        this.callAction = call
                        this.state.value = true;
                        this.state.cancel = true
                        callButton.style.display = 'none';
                        callClear.style.display = 'none';
                        call.on('ringing', (event) => {
                            const callSid = call.parameters.CallSid;
                            this.sid = callSid
                        });
                        /*
                            Wait for the call to have CallSid
                         */
                        call.on('accept', (event) => {
                            const callSid = call.parameters.CallSid;
                            this.sid = callSid; // Store the CallSid for later use
                            this.isTimerPaused = false;
                            this._runTimer();
                            if (id) {
                                this.orm.call('out.going.call.list', 'action_call', [, this.PhoneNumber, callSid, id]);
                            } else {
                                this.orm.call('out.going.call.list', 'action_making_call', [, this.PhoneNumber, callSid]);

                            }
                        });
                        call.on('cancel', async (event) => {
                            this.state.value = false;
                            this.state.cancel = false;
                            callButton.style.display = 'block';
                            callClear.style.display = 'block';
                            const callSid = call.parameters.CallSid;
                            await this.orm.call('out.going.call.list', 'action_cancel', [, this.PhoneNumber, callSid]);
                            this.action.doAction('soft_reload')
                            this.resetTimer();
                        });

                     call.on('disconnect',async (event) => {
                            this.state.value = false;
                            this.state.cancel = false;
                            callButton.style.display = 'block';
                            callClear.style.display = 'block';
                            this.resetTimer();
                            const callSid = call.parameters.CallSid;
                            // Check if it's not a rejection, then perform action_cancel
                            if(!this.state.wasRejected) {
                            if(!this.state.isRejected){
                                try {
                                   await this.orm.call('out.going.call.list', 'action_cancel', [, this.number, callSid]);
                                     this.action.doAction('soft_reload');
                                } catch (error) {
                                    console.error("Failed to perform action_cancel:", error);
                                }
                              }
                            }
                        });

                        call.on('reject', async (event) => {
                            this.state.value = false;
                            this.state.cancel = false;
                            const callSid = call.parameters.CallSid;
                            await this.orm.call('out.going.call.list', 'action_cancel', [, this.PhoneNumber, callSid]);
                            this.action.doAction('soft_reload')
                            this.resetTimer();
                            callButton.style.display = 'block';
                            callClear.style.display = 'block';
                        });
                    } catch (error) {
                        // Handle any errors if the promise is rejected
                        console.error("Call rejected:", error);
                        callButton.style.display = 'block';
                        callClear.style.display = 'block';
                    }
                }
            }
        } else {
            this.displayNotification(_t("Please enter a phone number to call"))
        }
    }
    /*
        For rejecting or disconnecting the active call
    */
  async _onClickCancel() {
        var self = this;
        this.state.value = false;
        this.state.cancel = false;
        this.state.isRejected = true;
        var PhoneNumber = this.PhoneNumber
        if (!this.sid) {
            this.displayNotification(_t("There is no active call for rejecting."))
        }
        if (self.device) {
            self.device.disconnectAll();
            this.state.wasRejected = true
            if (this.state.wasRejected) {
                await this.orm.call('out.going.call.list', 'action_cancel', [, PhoneNumber, this.sid]);
                this.action.doAction('soft_reload')
            }
        }
        this.resetTimer();
    }

    /*
       To minimize and maximise the templates
    */
    _onClickMinimise() {
        var outgoingDiv = this.outgoing.el.querySelector('.outgoing');
        var closeBtn = this.outgoing.el.querySelector('.close-btn');
        var outgoingKeypad = this.outgoing.el;
        var minimiseIcon = this.outgoing.el.querySelector('.minimise');
        var icon = this.outgoing.el.querySelector('.mini');
        if (outgoingDiv.style.display === 'none') {
            outgoingDiv.style.display = 'block';
            closeBtn.style.display = 'flex';
            outgoingKeypad.style.minWidth = '347px';
            outgoingKeypad.style.borderRadius = '0px';
            outgoingKeypad.style.removeProperty('height');
            outgoingKeypad.style.backgroundColor = 'white';
            if (!minimiseIcon) {
                icon.classList.remove('ri-phone-fill');
                icon.classList.add('ri-subtract-fill');
                icon.style.fontSize = ''
                icon.style.marginRight = ''
                icon.style.marginBottom = ''
                icon.style.color = 'black';
                icon.classList.add('minimise');
            }
        } else {
            outgoingDiv.style.display = 'none';
            closeBtn.style.display = 'none';
            outgoingKeypad.style.minWidth = '66px';
            outgoingKeypad.style.height = '68px';
            outgoingKeypad.style.borderRadius = '50%';
            outgoingKeypad.style.backgroundColor = '';
            if (minimiseIcon) {
                minimiseIcon.classList.add('ri-phone-fill');
                minimiseIcon.classList.remove('ri-subtract-fill');
                minimiseIcon.classList.remove('minimise');
                outgoingKeypad.style.backgroundColor = '#9EA700';
                minimiseIcon.style.color = 'white';
                minimiseIcon.style.fontSize = '30px'
            }
        }
    }
    /*
      By clicking on it we can move to the recent tab
    */
    _onClickRecent() {
        this.state.recent = true
        this.state.value = true
    }
    /*
      By clicking on it we can move to the contact tab
    */
    _onClickContact() {
        this.state.contacts = true
        this.state.value = true
    }
}

DialPad.components = {
    RecentTab,
    ContactTab
}
