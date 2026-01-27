/* @odoo-module */
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { SocialMediaFeed } from "@cyllo_social_media_marketing/js/feed_dashboard";
import { onWillStart, useState , useRef } from "@odoo/owl";

patch(SocialMediaFeed.prototype,{
    setup(){
        super.setup(...arguments);
        this.actionService = useService("action");
        this.modalContainer = useRef('social_comment_modal_fb');
        this.newMessageFb = useRef('new_message_fb');
        this.state.fields.push('fb_media_number');
        this.state.FbFeeds = []
        this.state.comments = []

        onWillStart(async () => {
            if (this.state.fields.includes('fb_media_number')) {
                await this.loadFbPosts()
                this.state.currentAccount = 'Facebook';
            }
        });
    },

    async showFbFeed(){
        if (this.state.currentAccount !== 'Facebook') {
            this.state.currentAccount = 'Facebook';
            if (this.state.FbFeeds.length === 0) {
                await this.loadFbPosts();
            }
        }
    },

    async loadFbPosts(url = null) {
        if (this.state.loadingFb === true) {
            return;
        }
        this.state.loadingFb = true;

        const response = await this.orm.call('social.media.feed', 'get_feed_data', [], {loadMore: url})

        const posts = response?.data?.map(post => {
            const created_time = new Date(post.created_time.replace("+0000", "Z"));
            const options = {
                year: "numeric",
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit"
            };
            return {
                id: post.id,  // same as post_id
                post_id: post.id,
                description: post.message || "",
                author_name: post.from?.name || "",
                author_link_url: `https://www.facebook.com/${post.id.split("_")[0]}/posts/${post.id.split("_")[1]}`,
                posted_date: created_time.toLocaleDateString(undefined, options),
                posted_image_url: post.attachments?.data?.[0]?.media?.image?.src || "",
                profile_image_url: `https://graph.facebook.com/${post.from?.id}/picture?type=large`,
                likes_count: post.likes?.summary?.total_count || 0,
                comments_count: (() => {
                    let count = post.comments?.summary?.total_count || 0;
                    if (post.comments?.data) {
                        post.comments.data.forEach(c => {
                            count += c.comments?.summary?.total_count || 0;
                        });
                    }
                    return count;
                })(),
            };
        });

        if (!posts) {
            return;
        }

        await this.orm.call("social.media.feed", "action_compute_fb_likes_count", [], {})
        this.state.FbFeeds.push(...posts);
        this.state.nextFbPage = response.paging?.next || null;
        this.state.loadingFb = false;
        this.detailsRefresh(this)
    },

    async loadMore() {
        if (this.state.nextFbPage) {
            await this.loadFbPosts(this.state.nextFbPage);
        }
    },

    async OpenCommentFb(feed){
        this.state.comments=[]
        this.state.type='facebook'
        this.feed=feed
        const res = await this.orm.call("social.media.feed", "get_facebook_comments", [], { feed: feed.id })
        this.state.comments = res.data || []
        this.state.nextFbCommentsPage = res.paging?.next || null
        this.modalContainer.el.style.display = "flex";
    },

    CloseCommentFb(){
        this.modalContainer.el.style.display = "none";
    },

    async loadMoreFbComments(feed) {
        if (!this.state.nextFbCommentsPage || this.state.loadingFbComments) return;

        this.state.loadingFbComments = true;
        const res = await this.orm.call("social.media.feed", "get_facebook_comments", [], {
            feed: feed.id,
            nextUrl: this.state.nextFbCommentsPage
        })
        this.state.comments.push(...res.data)   // append new comments
        this.state.nextFbCommentsPage = res.paging?.next || null
        this.state.loadingFbComments = false;
    },

    async loadMoreFbReplies(comment){
        if (this.state.loadingFbComments) return;
        this.state.loadingFbComments = true;
        const res = await fetch(comment.replies_paging?.next)
        const replies = await res.json()

        if (replies.data && replies.data.length) {
            comment.replies.push(...replies.data);
        }
        comment.replies_paging.next = replies.paging?.next || null;
        this.state.loadingFbComments = false;
    },

    async convertToLeadFb(title) {
        var feed_id = this.props.action.context.active_id
        self = this
        var parentElementId = event.target.parentElement.id
        const matchingComment = this.state.comments.find(comment => comment.id === parentElementId);
        await this.orm.call(
            "social.media.feed", "create_lead", [feed_id, matchingComment, title], {})
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
                            default_unique_fb_comment_number: data['unique_fb_comment_number'],
                        },
                    }, );
                }
            })
    },

    async PostCommentFb(){
        if (this.state.loadingFb === true) {
            return;
        }
        this.state.loadingFb = true;
        var self = this
        if(this.newMessageFb.el.value){
            await this.orm.call(
                "social.media.feed", "post_facebook_comments", [], {
                    feed: self.feed.id,
                    comment: self.newMessageFb.el.value
                }
            ).then(async (data) => {
                this.state.comments.unshift({
                    id: data.id,
                    username: data.from.name || "You",
                    userid: data.from.id || "0",
                    text: data.message,
                    like_count: 0,
                    replies: [],
                    partner_id: 0,
                });
                self.newMessageFb.el.value = ''
                self.state.loadingFb = false
            })
        }
    },
    ReplyCommentFb(event){
        const replyDiv = event.currentTarget.closest(".cy-social_marketComment-box").querySelector(".reply_div");
        if (replyDiv.classList.contains("d-none")){
            replyDiv.classList.remove("d-none")
        }
        else{
            replyDiv.classList.add("d-none")
        }
        this.nextElementSibling = replyDiv
    },
    async ReplyToCommentFb(comment,feed){
        if (this.state.loadingFb === true) {
            return;
        }
        this.state.loadingFb = true;
        var self=this
        var comment_reply_div =  document.getElementById("reply_"+comment.id);
        await this.orm.call("social.media.feed", "post_facebook_reply", [], {
            feed: feed.id,
            comment: comment.id,
            reply: comment_reply_div.value,
        })
        .then(async function(data) {
            comment.replies = comment.replies || [];
            comment.replies.unshift(data);
            self.nextElementSibling.classList.add("d-none")
            comment_reply_div.value = ''
            self.state.loadingFb = false;
        })
    },
    async ComputeDataFb(feed){
            this.state.currentFeed=feed
            self = this
            await this.orm.call("social.media.feed", "action_compute_fb_likes_count", [], {feed: feed.id})
            .then(function(data) {
                self.detailsRefresh(self)
                self.OpenCommentFb(feed)
            })
    },
    onClickViewRepliesFb(ev) {
        const replies = ev.currentTarget.closest(".cy-social_marketComment-box").querySelector(".view_replies");
        if (replies.classList.contains("d-none")){
            replies.classList.remove("d-none")
        }
        else{
            replies.classList.add("d-none")
        }
    },
});