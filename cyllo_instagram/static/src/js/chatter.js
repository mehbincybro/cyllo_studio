/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Composer } from "@mail/core/common/composer";
import { Typing } from "@mail/discuss/typing/common/typing";
import { useService } from "@web/core/utils/hooks";

patch(Composer, {
    components: { ...Composer.components, Typing },
});

patch(Composer.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state.insta_sent=false
        this.state.model=this.thread.model
        this.state.res_id=this.thread.id
    },
    onChangeInstaCheckbox(){
        if(this.state.insta_sent){
        this.state.insta_sent=false
        }
        else{
        this.state.insta_sent=true
        }
    },
    async sendMessage() {
        const self = this;
        await super.sendMessage();
            if(self.state.insta_sent){
            await this.orm.call(
            "res.partner", "action_message_partner_insta",
            [self.state.res_id,this.value], {}
            )}
    },
});
