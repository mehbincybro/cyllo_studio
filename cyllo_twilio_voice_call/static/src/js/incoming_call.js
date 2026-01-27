/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef } from "@odoo/owl";
import { jsonrpc } from "@web/core/network/rpc_service";

var device;

export class FetchIncomingCall extends Component {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.incoming = useRef("incoming");
        this.action = useService("action");
        this.state = useState({
            showIncomingCall: false,
            duration: 0,
            selectedPartner: null,
            isPartner: false
        })
        this.fetch_data();
    }

    /*
    Timer functions
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
    Fetching data for receiving incoming calls
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
            self.addDeviceListeners(device);
            /*
               The device must be registered to receive incoming calls
            */
            device.register();
        });
        return $.when(def1);
    }

    /*
    This function is used to identify whether it is incoming calls,
     if it incoming we can respond to the call by using this.
     */
    async addDeviceListeners(device) {
        if (device) {
            device.on('registered', (call) => {});
            device.on("incoming", async (call) => {
                const PartnerId = await this.orm.searchRead("res.partner", [
                    ["phone", "=", call.parameters.From]
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
                this.state.showIncomingCall = true;
                this.props.parent_this.toggle_keypad()
                this.handleIncomingCall(call);
                this.state.incomingCallNumber = call.parameters.From
                const CallSid = call.parameters.CallSid
                const From = call.parameters.From
                if (id) {
                  await this.orm.call('incoming.call.list', 'action_incoming_from_partner', [, From, CallSid, id]);
                  this.action.doAction('soft_reload')
                } else {
                   await this.orm.call('incoming.call.list', 'action_incoming_call', [, From, CallSid]);
                   this.action.doAction('soft_reload')
                }

            });
        }
    }
    /*
    This function is used to handle the incoming call
    */
   async handleIncomingCall(call) {
        this.state.showIncomingCall = true;
        this.state.incomingCall = call
        const CallSid = call.parameters.CallSid
        const From = call.parameters.From
        /*
            If the  Call cancelled by the caller before answering the call
        */
        call.on('cancel', async (event) => {
            this.state.showIncomingCall = false;
            await this.orm.call('incoming.call.list', 'action_hanging_call', [, From, CallSid]);
                  this.action.doAction('soft_reload')
                  this.resetTimer();
        });
        /*
            If the Call disconnected by the caller or receiver after answering the call
        */
        call.on('disconnect', async (event) => {
            this.state.showIncomingCall = false;
             await this.orm.call('incoming.call.list', 'action_hanging_call', [, From, CallSid]);
                  this.action.doAction('soft_reload')
            this.resetTimer();
        });
        /*
            If the Call rejected by the receiver after or before answering the call answering the call
        */
        call.on('reject', async (event) => {
            this.state.showIncomingCall = false;
            await this.orm.call('incoming.call.list', 'action_hanging_call', [, From, CallSid]);
                  this.action.doAction('soft_reload')
            this.resetTimer();
        });
    }
    /*
      Function for accepting the call in a button click
    */
    _onClickAccept() {
        if (this.state.incomingCall) {
            this.state.incomingCall.accept();
            this.isTimerPaused = false;
            this._runTimer();
            const acceptButton = this.incoming.el.querySelector('.ongoing-call');
            acceptButton.style.display = 'none';
        }
    }
    /*
       Function for rejecting the call in a button click
    */
   async _onClickReject() {
        if (this.state.incomingCall) {
            const CallSid = this.state.incomingCall.parameters.CallSid
            const From = this.state.incomingCall.parameters.From
            this.state.incomingCall.reject();
            this.state.incomingCall.disconnect();
            await this.orm.call('incoming.call.list', 'action_hanging_call', [, From, CallSid]);
            this.action.doAction('soft_reload')
            this.state.showIncomingCall = false;
            this.resetTimer();
        }
    }
    /*
    To hide and show the templates
    */
    _onClickMinimise() {
        const incomingDiv = this.incoming.el.querySelector('.show-incoming');
        var incomingKeypad = this.incoming.el;
        var minimiseIcon = this.incoming.el.querySelector('.minimise');
        var icon = this.incoming.el.querySelector('.mini');

        if (incomingDiv.style.display === 'none') {
            incomingDiv.style.display = 'block';
            incomingKeypad.style.width = '347px';
            incomingKeypad.style.borderRadius = '';
            incomingKeypad.style.removeProperty('height');
            incomingKeypad.style.backgroundColor = 'white';
            if (!minimiseIcon) {
                icon.classList.add('ri-subtract-fill');
                icon.style.fontSize = ''
                icon.style.marginRight = ''
                icon.classList.remove('ri-phone-fill');
                icon.classList.add('minimise');
                icon.style.color = 'black';

            }
        } else {
            incomingDiv.style.display = 'none';
            incomingKeypad.style.width = '70px';
            incomingKeypad.style.height = '70px';
            incomingKeypad.style.minWidth = '66px';
            incomingKeypad.style.borderRadius = '50%';
            incomingKeypad.style.backgroundColor = '';
            if (minimiseIcon) {
                minimiseIcon.classList.add('ri-phone-fill');
                minimiseIcon.classList.remove('ri-subtract-fill');
                minimiseIcon.classList.remove('minimise');
                incomingKeypad.style.backgroundColor = '#9EA700';
                minimiseIcon.style.color = 'white';
                minimiseIcon.style.fontSize = '35px'
                minimiseIcon.style.marginLeft = '1px'
            }
        }
    }
}

FetchIncomingCall.template = "incoming_call";