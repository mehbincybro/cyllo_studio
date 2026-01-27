/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useRef } from "@odoo/owl";
import { SocialMediaFeed } from "@cyllo_social_media_marketing/js/feed_dashboard";

patch(SocialMediaFeed.prototype,{
    setup(){
        super.setup(...arguments);
        this.actionService = useService("action");
        this.state.fields.push('ig_media_number');
        this.newMessageInsta = useRef('new_message_ig');
        this.state.comments = [];
        this.state.instaFeeds = [];
        this.modalContainerInsta = useRef('social_comment_modal_insta');

        onWillStart(async () => {
            if (!this.state.fields.includes('fb_media_number')) {
                await this.loadInstaPosts();
                this.state.currentAccount = 'Instagram';
            }
        });
    },

    async showInstaFeed(){
        if (this.state.currentAccount !== 'Instagram') {
            this.state.currentAccount = 'Instagram';
            if (this.state.instaFeeds.length === 0) {
                await this.loadInstaPosts();
            }
        }
    },

    async loadInstaPosts(url = null) {
        this.state.loadingInsta = true;
        const response = await this.orm.call(
            'social.media.feed','get_insta_feed_data',
            [],
            { loadMore: url }
        );
        const posts = response?.data?.map(post => {
            const created_time = new Date(post.timestamp);
            const options = {
                year: "numeric",
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit"
            };
            return {
                id: post.id,
                post_id: post.id,
                description: post.caption || "",
                author_name: post.username || "",
                author_link_url: post.permalink,
                posted_date: created_time.toLocaleDateString(undefined, options),
                posted_image_url: (post.media_type === "IMAGE" || post.media_type === "CAROUSEL_ALBUM")
                    ? post.media_url
                    : post.thumbnail_url || "",
                profile_image_url: post.profile_picture_url || "",
                likes_count: post.like_count || 0,
                comments_count: post.comments_count || 0,
            };
        });

        if (!posts) return;

        this.state.instaFeeds.push(...posts);
        this.state.nextInstaPage = response?.paging?.next || null;
        this.state.loadingInsta = false;
        this.detailsRefresh(this)
    },

    async loadMoreInsta() {
        if (this.state.nextInstaPage) {
            await this.loadInstaPosts(this.state.nextInstaPage);
        }
    },

    async openCommentInsta(feed){
        this.state.comments = [];
        this.state.type = 'instagram';
        this.feed = feed;
        const res = await this.orm.call(
            "social.media.feed", "get_instagram_comments",
            [],
            { feed: feed.id }
        );
        this.state.comments = res.data || [];
        this.state.nextInstaCommentsPage = res.paging?.next || null;
        this.modalContainerInsta.el.style.display = "flex";
    },

    closeCommentInsta(){
        this.modalContainerInsta.el.style.display = "none";
    },

    onClickViewReplies(ev) {
        const replies =
            ev.currentTarget.closest(".cy-social_marketComment-box").querySelector(".view_replies");
        if (replies.classList.contains("d-none")){
            replies.classList.remove("d-none");
        }
        else{
            replies.classList.add("d-none");
        }
    },

    async loadMoreInstaComments(feed) {
        if (!this.state.nextInstaCommentsPage || this.state.loadingInstaComments) return;

        this.state.loadingInstaComments = true;
        const res = await this.orm.call(
            "social.media.feed", "get_instagram_comments",
            [],
            {
                feed: feed.id,
                nextUrl: this.state.nextInstaCommentsPage,
            }
        );
        this.state.comments.push(...res?.data);
        this.state.nextInstaCommentsPage = res.paging?.next || null;
        this.state.loadingInstaComments = false;
    },

    async loadMoreInstaReplies(comment){
        if (this.state.loadingInstaComments) return;

        this.state.loadingInstaComments = true;
        const url = comment.replies?.paging?.next
        const { origin, pathname, search } = new URL(url);
        const baseWithVersion = `${origin}${pathname.split("/").slice(0, 2).join("/")}`;
        const accessToken = new URLSearchParams(search).get("access_token");
        const replyResponse = await (await fetch(url)).json();

        if (replyResponse.data && replyResponse.data.length) {
            const enrichedReplies = await Promise.all(
                replyResponse.data.map(async (reply) => {
                    const userRes = await fetch(
                        `${baseWithVersion}/${reply.id}?fields=id,username,text,timestamp&access_token=${accessToken}`
                    );

                    const userData = await userRes.json();
                    return {...reply, ...userData}
                })
            );
            comment.reply.push(...enrichedReplies);
        }
        comment.replies.paging.next = replyResponse.paging?.next || null;
        this.state.loadingInstaComments = false;
    },

    async convertToLead(title) {
        const feed_id = this.props.action.context.active_id;
        const self = this;
        const parentElementId = event.target.parentElement.id;
        const matchingComment = this.state.comments.find(comment => comment.id === parentElementId);
        await this.orm.call(
                "social.media.feed", "create_lead_ig", [feed_id, matchingComment, title], {}
        ).then((data) => {
            if (data['lead']) {
                self.actionService.doAction({
                    res_model: 'crm.lead',
                    res_id: data['lead'],
                    target: "current",
                    type: "ir.actions.act_window",
                    views: [
                        [false, "form"]
                    ],
                });
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
                });
            }
        });
    },

    async postCommentInsta(){
        if (this.state.loadingInsta === true) return;

        this.state.loadingInsta = true;
        const self = this;
        if(this.newMessageInsta.el.value) {
            await this.orm.call(
                "social.media.feed", "post_instagram_comments", [], {
                    feed: self.feed.id,
                    comment: self.newMessageInsta.el.value,
                }
           ).then(async (data) => {
                self.state.comments.unshift({
                    id: data.id,
                    username: data.username || "You",
                    text: data.text,
                    like_count: 0,
                    replies: [],
                    partner_id: 0,
                });
                self.newMessageInsta.el.value = '';
                self.state.loadingInsta = false;
           })
        }
    },

    replyCommentInsta(event){
        const replyDiv =
            event.currentTarget.closest(".cy-social_marketComment-box").querySelector(".reply_div");
        if (replyDiv.classList.contains("d-none")){
            replyDiv.classList.remove("d-none");
        } else {
            replyDiv.classList.add("d-none");
        }
        this.nextElementSibling = replyDiv;
    },

    async replyToCommentInsta(comment,feed){
        if (this.state.loadingInsta === true) return;

        this.state.loadingInsta = true;
        const self = this;
        const comment_reply_div =  document.getElementById(("comment_"+comment.id));
         await this.orm.call("social.media.feed", "post_instagram_reply", [], {
             feed: feed.id,
             comment: comment.id,
             reply: comment_reply_div.value,
         }).then(async (data) => {
             comment.reply = comment.reply || [];
             comment.reply.unshift(data);
             self.nextElementSibling.classList.add("d-none");
             comment_reply_div.value = '';
             self.state.loadingInsta = false;
           })
    },

});
