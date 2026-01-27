/** @odoo-module **/
import { Component, onWillStart,useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";


export class FacebookComments extends Component {
    static template = "cyllo_facebook.FacebookComments";
    // Setup method to initialize the component and set up services
    setup() {
        onWillStart(this.onWillStart);
        this.actionService = useService("action");
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.comment_reply = useRef("fb_comment_reply_area");
    }
    // Fetch Facebook comments before the component is mounted
    async onWillStart() {
        var feed_id = this.props.action.context.active_id
        var self = this;
        self.fb_comments = await this.orm.call("social.media.feed", "get_facebook_comments", [feed_id], {})
    }
    // Method to get the fetched Facebook comments
    get FacebookCommentDetails() {
        return this.fb_comments
    }
    // Method to handle the 'Post' button click for posting a new comment
    async onClickPost(){
        var feed_id = this.props.action.context.active_id
        var comment_div =  document.getElementById("fb_comment_area");
        var extra_comment_div =  document.getElementById("extra_comment_div");
        await this.orm.call("social.media.feed", "post_facebook_comments", [feed_id,comment_div.value], {})
        .then(function(data) {
            comment_div.value = ''
        })
        window.location.reload();
    }
    async convertToLead(){
        var feed_id = this.props.action.context.active_id
        self=this
        var parentElementId=event.target.parentElement.id
        const matchingComment = this.fb_comments.find(comment => comment.id === parentElementId);
        await this.orm.call("social.media.feed", "create_lead", [feed_id, matchingComment], {})
        .then(function(data) {
            if (data['lead']){
                self.actionService.doAction({
                    res_model: 'crm.lead',
                    res_id: data['lead'],
                    target: "current",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                });
            }
            else{
                self.actionService.doAction({
                    res_model: 'crm.lead',
                    target: "new",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                    context: {
                        default_name: data['name'],
                        default_type: 'lead',
                        default_user_id: data['user_id'],
                        default_partner_id: data['partner_id'],
                        default_contact_name: data['contact_name'],
                        default_unique_fb_comment_number: data['unique_fb_comment_number'],
                    },
                });
            }
        })
    }
    // Method to handle the 'View Replies' button click for displaying replies
    onClickViewReplies(){
        event.target.nextElementSibling.style = 'block'
    }
    // Method to post a reply to a specific comment
    async postReply(){
        var comment_id = event.target.parentElement.id
        var feed_id = this.props.action.context.active_id
        var reply =event.target.parentElement.firstChild
        await this.orm.call("social.media.feed", "post_facebook_reply", [feed_id,comment_id,reply.value], {})
        .then(function(data) {
            reply.value=''
        })
    }
    // Method to handle the 'Reply' button click for displaying the reply input area
    onClickReply(){
        event.target.nextElementSibling.style = 'block'
    }
    // Method to handle the deletion of comments
    onClickDelete(){
        var fb_comment_id = event.target.parentElement.id
    }
}
registry.category("actions").add("fb_comments", FacebookComments);