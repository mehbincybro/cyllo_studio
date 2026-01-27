/* @odoo-module */
import {patch} from "@web/core/utils/patch";
import {SocialMediaFeed} from "@cyllo_social_media_marketing/js/feed_dashboard";
import {useRef} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


patch(SocialMediaFeed.prototype, {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
        this.modalContainerYt = useRef('social_comment_modal_youtube');
        this.newMessage = useRef('new_message_yt');
        this.state.fields.push('youtube_number', 'views_count')
        this.state.comments = []
    },
    async OpenCommentYoutube(feed) {
        this.state.comments=[]
        this.state.type='youtube'
        this.feed = feed
        this.state.comments = await this.orm.call(
            "social.media.feed", "get_youtube_comments", ["", feed.id], {})
        this.modalContainerYt.el.style.display = "block";
    },
    async convertToLeadYt() {
    var feed_id = this.props.action.context.active_id
    self = this
    var parentElementId = event.target.parentElement.id
    const matchingComment = this.state.comments.find(comment => comment.id === parentElementId);
    await this.orm.call(
            "social.media.feed", "create_lead_youtube", [feed_id, matchingComment], {})
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
                        default_unique_yt_comment_number: data['unique_yt_comment_number'],
                    },
                }, );
            }
        })
},
    onClickViewReplies(ev) {
        if (ev.target.nextElementSibling.classList.contains("d-none")){
                    ev.target.nextElementSibling.classList.remove("d-none")
        }
        else{
            ev.target.nextElementSibling.classList.add("d-none")
        }
    },
    CloseCommentYoutube() {
        this.modalContainerYt.el.style.display = "none";
    },
    async PostCommentYoutube() {
        var self = this
        if (this.newMessage.el.value) {
            await this.orm.call(
                "social.media.feed", "post_youtube_comments", ["", self.feed.id, self.newMessage.el.value], {}
            ).then(function (data) {
                self.newMessage.el.value = ''
            })
            window.location.reload();
        }
    },
    ReplyCommentYoutube(comment) {
        if (event.target.nextElementSibling.classList.contains("d-none")) {
            event.target.nextElementSibling.classList.remove("d-none")
        } else {
            event.target.nextElementSibling.classList.add("d-none")
        }
        this.nextElementSibling = event.target.nextElementSibling
    },
    async ReplyToCommentYoutube(comment, feed) {
        var self = this
        var comment_reply_div = document.getElementById('yt_' + comment.id);
        await this.orm.call(
            "social.media.feed", "post_youtube_reply",
            ["", feed.id, comment.id, comment_reply_div.value], {}
        ).then(function (data) {
            self.nextElementSibling.classList.add("d-none")
            comment_reply_div.value = ''
        })
    },
    async ComputeDataYt(feed) {
        var YtDetails = document.getElementById(("Details_" + feed.id));
        if (YtDetails.classList.contains("d-none")) {
            self = this
            await this.orm.call(
                "social.media.feed", "action_compute_likes_count", [feed.id], {}).then(function (data) {
                if (data.comments_count) {
                    self.state.Feeds.filter(r => r.id === feed.id)[0].comments_count = data.comments_count
                }
                if (data.likes_count) {
                    self.state.Feeds.filter(r => r.id === feed.id)[0].likes_count = data.likes_count
                }
                if (data.views_count) {
                    self.state.Feeds.filter(r => r.id === feed.id)[0].views_count = data.views_count
                }
                self.detailsRefresh(self)
                YtDetails.classList.remove("d-none")
            })
        } else {
            YtDetails.classList.add("d-none")
        }
    },

});
