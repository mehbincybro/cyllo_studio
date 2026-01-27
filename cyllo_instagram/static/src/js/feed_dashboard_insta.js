/* @odoo-module */
import { patch } from "@web/core/utils/patch";
import { SocialMediaFeed } from "@cyllo_social_media_marketing/js/feed_dashboard";
import { useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


patch(SocialMediaFeed.prototype,{
    setup(){
            super.setup(...arguments);
            this.actionService = useService("action");
            this.state.fields.push('ig_media_number')
            this.newMessageInsta = useRef('new_message_ig');
            this.state.comments=[]
            this.modalContainerInsta = useRef('social_comment_modal_insta');
        },
        async OpenCommentInsta(feed){
        this.state.comments=[]
        this.state.type='instagram'
        this.feed=feed
        this.state.comments = await this.orm.call(
           "social.media.feed", "get_instagram_comments", ["",feed.id], {})
        this.modalContainerInsta.el.style.display = "block";
        },
        onClickViewReplies(ev) {
        if (ev.target.nextElementSibling.classList.contains("d-none")){
                    ev.target.nextElementSibling.classList.remove("d-none")
        }
        else{
            ev.target.nextElementSibling.classList.add("d-none")
        }
    },
        CloseCommentInsta(){
            this.modalContainerInsta.el.style.display = "none";
        },
        async convertToLead() {
        var feed_id = this.props.action.context.active_id
        self = this
        var parentElementId = event.target.parentElement.id
        const matchingComment = this.state.comments.find(comment => comment.id === parentElementId);
        await this.orm.call(
                "social.media.feed", "create_lead_ig", [feed_id, matchingComment], {})
            .then(function(data) {
                if (data['lead']) {
                    self.actionService.doAction({
                        res_model: 'crm.lead',
                        res_id: data['lead'],
                        target: "current",
                        type: "ir.actions.act_window",
                        views: [
                            [false, "form"]
                        ],
                    }, );
                } else {
                    self.actionService.doAction({
                        res_model: 'crm.lead',
                        target: "new",
                        type: "ir.actions.act_window",
                        views: [
                            [false, "form"]
                        ],
                        context: {
                            default_name: data['name'],
                            default_type: 'lead',
                            default_user_id: data['user_id'],
                            default_partner_id: data['partner_id'],
                            default_contact_name: data['contact_name'],
                            default_unique_ig_comment_number: data['unique_ig_comment_number'],
                        },
                    }, );
                }
            })
    },
        async PostCommentInsta(){
        var self = this
        if(this.newMessageInsta.el.value){
          await this.orm.call(
           "social.media.feed", "post_instagram_comments", ["",self.feed.id,self.newMessageInsta.el.value], {}
           ).then(function(data) {
             self.newMessageInsta.el.value = ''
           })
            window.location.reload();
        }
        },
        ReplyCommentInsta(comment){
        if (event.target.nextElementSibling.classList.contains("d-none")){
                    event.target.nextElementSibling.classList.remove("d-none")
        }
        else{
            event.target.nextElementSibling.classList.add("d-none")
        }
        this.nextElementSibling = event.target.nextElementSibling
        },
        async ReplyToCommentInsta(comment,feed){
        var self=this
        var comment_reply_div =  document.getElementById(("comment_"+comment.id));
         await this.orm.call(
           "social.media.feed", "post_instagram_reply",
            ["",feed.id,comment.id,comment_reply_div.value], {}
           ).then(function(data) {
             self.nextElementSibling.classList.add("d-none")
             comment_reply_div.value = ''
             self.CloseCommentInsta()
           })
        },
        async ComputeDataInsta(feed){
                self=this
                await this.orm.call(
                "social.media.feed", "action_compute_likes_count", [feed.id], {}).then(function(data) {
                self.state.Feeds.filter(r => r.id === feed.id)[0].comments_count=data.comments_count
                self.state.Feeds.filter(r => r.id === feed.id)[0].likes_count=data.likes_count
                self.detailsRefresh(self)
                self.OpenCommentInsta(feed)
          })
          }

});
