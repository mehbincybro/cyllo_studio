/** @odoo-module **/
import { Component, onWillStart, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class InstagramComment extends Component {
    static template = "cyllo_instagram.InstagramComment";
    // Setup method to initialize the component and set up services
    setup() {
        onWillStart(this.onWillStart);
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.comment_reply = useRef("ig_comment_reply_area");
    }
    // Fetch Instagram comments before the component is mounted
    async onWillStart() {
        const feed_id = this.props.action.context.active_id;
        const self = this;
        self.insta_comment = await this.orm.call(
            "social.media.feed", "get_instagram_comments", ["", feed_id], {})
    }
    // Method to get the fetched Instagram comments
    get InstagramCommentDetails() {
        return this.insta_comment
    }
    // Method to handle the 'Post' button click for posting a new comment
    async onClickPost() {
        const feed_id = this.props.action.context.active_id;
        const comment_div = document.getElementById("ig_comment_area");
        await this.orm.call(
            "social.media.feed", "post_instagram_comments", ["", feed_id, comment_div.value], {}
        ).then(function(data) {
            comment_div.value = ''
        })
        window.location.reload();
    }
    async convertToLead() {
        var feed_id = this.props.action.context.active_id
        self = this
        var parentElementId = event.target.parentElement.id
        const matchingComment = this.insta_comment.find(comment => comment.id === parentElementId);
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
    }
    // Method to handle the 'View Replies' button click for displaying replies
    onClickViewReplies(ev) {
        var style = ev.target.nextElementSibling.style
        if (style.display == 'none') {
            ev.target.nextElementSibling.style = 'block'
        } else {
            ev.target.nextElementSibling.style = 'none'
        }
    }
    // Method to post a reply to a specific comment
    async postReply() {
        const comment_id = event.target.parentElement.id;
        const feed_id = this.props.action.context.active_id;
        const comment_reply_div = event.target.parentElement.firstChild;
        await this.orm.call(
            "social.media.feed", "post_instagram_reply",
            ["", feed_id, comment_id, comment_reply_div.value], {}
        ).then(function(_) {
            comment_reply_div.value = ''
        })
    }
    // Method to handle the 'Reply' button click for displaying the reply input area
    onClickReply() {
        event.target.nextElementSibling.style = 'block'
    }
    // Method to handle the deletion of comments
}
registry.category("actions").add("insta_comments", InstagramComment);
