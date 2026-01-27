/* @odoo-module */
import { patch } from "@web/core/utils/patch";
import { SocialMediaFeed } from "@cyllo_social_media_marketing/js/feed_dashboard";
import { onWillStart, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


patch(SocialMediaFeed.prototype, {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
        this.modalContainerYt = useRef('social_comment_modal_youtube');
        this.newMessage = useRef('new_message_yt');
        this.state.fields.push('youtube_number', 'views_count');
        this.state.comments = [];
        this.state.YtFeeds = [];
        this.state.channels = [];
        this.state.selectedChannelId = [];

        onWillStart(async () => {
            const channels = await this.orm.call("youtube.channel", "get_connected_channels", []);
            this.state.channels = channels;
            this.state.selectedChannelId = null; // nothing selected yet
            this.state.YtFeeds = [];

            if (!this.state.fields.includes('fb_media_number')) {
                await this.loadYoutubePosts();
                this.state.currentAccount = 'Youtube';
            }
        });
    },
    async onChannelChange(ev) {
        const channelId = parseInt(ev.target.value);
        this.state.selectedChannelId = channelId;
        await this.orm.call("youtube.channel", "set_default_account_from_channel", [channelId]);
        this.state.YtFeeds = [];
        await this.loadYoutubePosts(null, channelId);
    },

    async showYtFeed() {
        if (this.state.currentAccount !== 'Youtube') {
            this.state.currentAccount = 'Youtube';
            // If no channel selected yet, pick the first one (default)
            if (!this.state.selectedChannelId && this.state.channels.length > 0) {
                this.state.selectedChannelId = this.state.channels[0].id; // or last connected channel
            }
            if (this.state.selectedChannelId) {
                await this.loadYoutubePosts(null, this.state.selectedChannelId);
            }
        }
    },

    async loadYoutubePosts(pageToken = null, channelId = null) {
        this.state.loading = true;

        const response = await this.orm.call(
            "social.media.feed",
            "get_youtube_feed_data",
            [channelId, pageToken]  // pass selected channel ID
        );
        const posts = (response?.data || []).map(video => {
            const published_at = new Date(video.publishedAt);
            const options = {
                year: "numeric",
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit"
            };
            return {
                id: video.id,
                post_id: video.id,
                description: video.description || "",
                author_name: video.channelTitle || "",
                author_link_url: `https://youtube.com/watch?v=${video.id}`,
                posted_date: published_at.toLocaleDateString(undefined, options),
                posted_image_url: video.thumbnails?.medium?.url || "",
                profile_image_url: video.channelThumb || "",
                likes_count: video.statistics?.likeCount || 0,
                dislikes_count: video.statistics?.dislikeCount || 0,
                comments_count: video.statistics?.commentCount || 0,
                views_count: video.statistics?.viewCount || 0,
            };
        });
        this.state.YtFeeds = posts;
        this.state.nextPage = response?.nextPageToken || null;
        this.state.loading = false;
        this.detailsRefresh(this);
    },

    async loadYoutubeMore() {
        if (this.state.nextPage) {
            await this.loadYoutubePosts(this.state.nextPage);
        }
    },

   async OpenCommentYoutube(feed) {
        this.state.activeFeed = feed;
        this.state.comments = [];
        this.state.nextPageToken = null;

        const res = await this.orm.call(
            "social.media.feed",
            "get_youtube_comments",
            [feed.id, null, this.state.selectedChannelId]
        );

        this.state.comments = res.comments;
        this.state.nextPageToken = res.nextPageToken;
        this.modalContainerYt.el.style.display = "flex";
   },


   async LoadMoreComments() {
        if (!this.state.nextPageToken) return;
        const res = await this.orm.call(
            "social.media.feed",
            "get_youtube_comments",
            [this.state.activeFeed.id, this.state.nextPageToken, this.state.selectedChannelId]
        );

        this.state.comments.push(...res.comments);
        this.state.nextPageToken = res.nextPageToken;
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
        const replies =
            ev.currentTarget.closest(".cy-social_marketComment-box").querySelector(".view_replies");
        if (replies.classList.contains("d-none")){
            replies.classList.remove("d-none");
        }
        else{
            replies.classList.add("d-none");
        }
    },

    CloseCommentYoutube() {
        this.modalContainerYt.el.style.display = "none";
    },
    async PostCommentYoutube(ev, feed) {
        if (!feed) {
            alert("No feed selected!");
            return;
        }
        const input = this.newMessage.el.value;
        if (input) {
            await this.orm.call(
                "social.media.feed",
                "post_youtube_comments",
                [feed.id, input,this.state.selectedChannelId],
                {}
            );
            this.newMessage.el.value = "";
            await this.OpenCommentYoutube(feed);
        }
    },

    ReplyCommentYoutube(event) {
        const replyDiv =
            event.currentTarget.closest(".cy-social_marketComment-box").querySelector(".reply_div");
        if (replyDiv.classList.contains("d-none")){
            replyDiv.classList.remove("d-none");
        } else {
            replyDiv.classList.add("d-none");
        }
        this.nextElementSibling = replyDiv;
    },
    async ReplyToCommentYoutube(comment, feed) {
        if (!comment || !feed) return;  // safety check
        const input = document.getElementById('yt_' + comment.id);
        if (!input || !input?.value?.trim()) return;

        try {
            await this.orm.call(
                "social.media.feed",
                "post_youtube_reply",
                [feed.id, comment.id, input.value, this.state.selectedChannelId],
                {}
            );
            input.value = '';
            await this.loadYoutubePosts();
            await this.OpenCommentYoutube(feed);
        } catch (err) {
            console.error("Failed to post reply:", err);
        }
    },
    async ComputeDataYt(feed) {
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
                self.OpenCommentYoutube(feed)
            })
    },

});
