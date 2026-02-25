/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";
import { serializeDateTime, deserializeDateTime } from "@web/core/l10n/dates";
import { useEmojiPicker } from "@web/core/emoji_picker/emoji_picker";

const actionRegistry = registry.category("actions");

export class SocialMediaFeed extends Component {
    async setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.containerRef = useRef("container");
        this.state = useState({
            Feeds: false,
            fields: ['id', 'description', 'author_name', 'author_link', 'posted_date', 'author_link_url', 'posted_image', 'profile_image_url', 'posted_image_url', 'profile_image', 'likes_count', 'comments_count', 'post_id', 'linkedin_account_id', 'linkedin_org_id'],
            demo: false,
            posts: [],
            nextPage: null,
            loading: false,
            currentAccount: null,
            LinkedinFeeds: [],
            currentComments: [],
            commentingFeed: null,
            liCommentText: "",
            liReplyTexts: {},
            // Nested Comments State
            replies: {}, // { commentId: [replyObjects] }
            showReplies: {}, // { commentId: boolean }
            repliesLoading: {}, // { commentId: boolean }
            // LinkedIn Organization Selector
            linkedinOrgs: [],       // list of {id, name, org_urn, logo_url}
            selectedOrgId: null,    // null = All orgs
            // LinkedIn Pagination
            liOffset: 0,
            liHasMore: true,
            liBatchSize: 15,
            AllLinkedinFeedsForTotals: [], // Stores matching feeds for totals calculation
            LiPostCount: 0,
        });

        this.emojiPicker = useEmojiPicker(useRef("liEmojiButton"), {
            onSelect: this.onEmojiSelect.bind(this),
        });

        onWillStart(async () => {
            this.state.Feeds = await this.orm.searchRead('social.media.feed', [], this.state.fields)
            this.state.YoutubeFeeds = this.state.Feeds.filter(r => r.youtube_number !== false)
            this.state.LinkedinFeeds = this.state.Feeds.filter(r => r.linkedin_account_id !== false)
            this.detailsRefresh(this)

            await this._loadLinkedInOrgs();
            await this.fetchLinkedInFeeds(true);
        });
        onMounted(() => {
            if (this.containerRef.el) {
                this.containerRef.el.addEventListener("scroll", this.onScroll.bind(this));
            }
            document.querySelectorAll("textarea").forEach((textarea) => {
                textarea.addEventListener("input", () => {
                    textarea.style.height = "auto";
                    textarea.style.height = textarea.scrollHeight + "px";
                });
            });
        });

        onWillUnmount(() => {
            if (this.containerRef.el) {
                this.containerRef.el.removeEventListener("scroll", this.onScroll.bind(this));
            }
        });
    }

    async showLinkedinFeed() {
        this.state.currentAccount = 'LinkedIn';
        await this.fetchLinkedInFeeds(true);
    }

    async _loadLinkedInOrgs() {
        try {
            const orgs = await this.orm.searchRead(
                'linkedin.organization',
                [['state', '=', 'active'], ['type', '=', 'organization']],
                ['id', 'name', 'org_urn', 'logo_url', 'account_id']
            );
            this.state.linkedinOrgs = orgs;
            if (!this.state.selectedOrgId && orgs.length > 0) {
                this.state.selectedOrgId = orgs[0].id;
            }
        } catch (e) {
            console.error('Failed to load LinkedIn orgs', e);
        }
    }

    async selectLinkedInOrg(orgId) {
        this.state.selectedOrgId = orgId;
        this.state.LinkedinFeeds = [];
        this.state.liOffset = 0;
        this.state.liHasMore = true;
        await this.fetchLinkedInFeeds(false);
    }

    onLinkedInOrgChange(ev) {
        const value = ev.target.value;
        const orgId = value === "all" ? null : parseInt(value);
        this.selectLinkedInOrg(orgId);
    }

    async loadMoreLinkedInFeeds() {
        if (!this.state.liHasMore || this.state.loading) return;
        this.state.liOffset += this.state.liBatchSize;
        await this.fetchLinkedInFeeds(true, true);
    }

    async onScroll() {
        if (this.state.loading || !this.state.liHasMore || this.state.currentAccount !== 'LinkedIn') {
            return;
        }
        const { scrollTop, scrollHeight, clientHeight } = this.containerRef.el;
        if (scrollTop + clientHeight >= scrollHeight - 50) {
            await this.loadMoreLinkedInFeeds();
        }
    }

    async fetchLinkedInFeeds(sync = false, loadMore = false) {
        if (this.state.loading) return;
        this.state.loading = true;
        try {
            if (sync) {
                const accounts = await this.orm.searchRead('linkedin.account', [['state', '=', 'connected']], ['id']);
                let combinedHasMore = false;
                for (const account of accounts) {
                    const result = await this.orm.call('linkedin.account', 'action_fetch_linkedin_feeds', [[account.id]], {
                        start: this.state.liOffset,
                        count: this.state.liBatchSize
                    });
                    if (result && result.has_more) {
                        combinedHasMore = true;
                    }
                }
                this.state.liHasMore = combinedHasMore;
                await this._loadLinkedInOrgs();
            }

            const domain = [['linkedin_account_id', '!=', false]];
            if (this.state.selectedOrgId) {
                domain.push(['linkedin_org_id', '=', this.state.selectedOrgId]);
            }

            this.state.LinkedinFeeds = await this.orm.searchRead(
                'social.media.feed',
                domain,
                this.state.fields,
                {
                    order: 'posted_date DESC',
                    limit: this.state.liOffset + this.state.liBatchSize
                }
            );

            this.state.AllLinkedinFeedsForTotals = await this.orm.searchRead(
                'social.media.feed',
                domain,
                ['likes_count', 'comments_count']
            );

            this.state.Feeds = await this.orm.searchRead('social.media.feed', [], this.state.fields);

            this.detailsRefresh(this);
        } catch (e) {
            console.error("Failed to fetch LinkedIn feeds", e);
        } finally {
            this.state.loading = false;
        }
    }

    async OpenLinkedInComments(feed) {
        this.state.showCommentsModal = true;
        this.state.commentsLoading = true;
        this.state.currentComments = [];

        if (feed === 'demo') {
            this.state.commentingFeed = { author_name: 'LinkedIn Demo Page' };
            // Synchronous update for demo to ensure it shows immediately after modal opens
            this.state.currentComments = [
                { id: 'd1', author_name: 'Alex Rivera', text: 'This is a game changer! 🚀', created_at: new Date().getTime() - 1000000, comments_count: 2 },
                { id: 'd2', author_name: 'Sarah Chen', text: 'Excellent insights on the market trends.', created_at: new Date().getTime() - 5000000, comments_count: 0 },
                { id: 'd3', author_name: 'Marcus Thorne', text: 'Would love to hear more about the technical details.', created_at: new Date().getTime() - 10000000, comments_count: 5 }
            ];
            // Simulate replies for demo
            this.state.replies['d1'] = [
                { id: 'd1_r1', author_name: 'Cyllo Team', text: 'Glad you think so, Alex!', created_at: new Date().getTime() - 500000 },
                { id: 'd1_r2', author_name: 'Alex Rivera', text: 'Can\'t wait to try it.', created_at: new Date().getTime() - 200000 }
            ];
            this.state.commentsLoading = false;
            return;
        }

        this.state.commentingFeed = feed;
        try {
            const comments = await this.orm.call('social.media.feed', 'action_social_media_comments', [[feed.id]]);
            this.state.currentComments = comments || [];
        } catch (e) {
            console.error("Failed to fetch LinkedIn comments", e);
            this.state.currentComments = [];
        } finally {
            this.state.commentsLoading = false;
        }
    }

    CloseCommentsModal() {
        this.state.showCommentsModal = false;
        this.state.currentComments = [];
        this.state.commentingFeed = null;
        this.state.liCommentText = "";
        this.state.liReplyTexts = {};
        this.state.replies = {};
        this.state.showReplies = {};
    }

    onLiCommentInput(ev) {
        this.state.liCommentText = ev.target.value;
    }

    onLiReplyInput(ev, commentId) {
        this.state.liReplyTexts[commentId] = ev.target.value;
    }

    async onClickPostLinkedIn() {
        if (this.state.commentsLoading) return;
        const textarea = document.getElementById("li_comment_area");
        if (!textarea) return;
        const message = textarea.value.trim();
        if (!message) return;

        this.state.commentsLoading = true;
        try {
            const feed = this.state.commentingFeed;
            if (feed && feed.id) {
                // Fetch the post URN and account ID from the feed record
                const feed_data = await this.orm.read('social.media.feed', [feed.id], ['linkedin_post_urn', 'linkedin_account_id']);
                const post_urn = feed_data[0].linkedin_post_urn;
                const account_id = feed_data[0].linkedin_account_id[0];

                const result = await this.orm.call('linkedin.account', 'action_post_linkedin_comment', [account_id, post_urn, message]);
                if (result && !result.error) {
                    textarea.value = '';
                    this.state.liCommentText = "";
                    // Trigger auto-resize reset
                    textarea.style.height = "auto";
                    // Refresh comments
                    await this.OpenLinkedInComments(feed);
                }
            }
        } catch (e) {
            console.error("Failed to post LinkedIn comment", e);
        } finally {
            this.state.commentsLoading = false;
        }
    }

    onClickReplyLinkedIn(commentId) {
        // Toggle visibility of the reply input for a specific comment
        const replyDiv = document.getElementById(`reply_div_${commentId}`);
        if (replyDiv) {
            replyDiv.classList.toggle("d-none");
        }
    }

    async postLinkedInReply(comment) {
        if (this.state.commentsLoading) return;
        const input = document.getElementById(`reply_input_${comment.id}`);
        if (!input) return;
        const message = input.value.trim();
        if (!message) return;

        this.state.commentsLoading = true;
        try {
            const feed = this.state.commentingFeed;
            const feed_data = await this.orm.read('social.media.feed', [feed.id], ['linkedin_account_id']);
            const account_id = feed_data[0].linkedin_account_id[0];

            const result = await this.orm.call('linkedin.account', 'action_post_linkedin_reply', [account_id, comment.id, message]);
            if (result && !result.error) {
                input.value = '';
                if (this.state.liReplyTexts[comment.id]) {
                    delete this.state.liReplyTexts[comment.id];
                }

                // If replies were not shown, show them now to see the new reply
                if (!this.state.showReplies[comment.id]) {
                    this.state.showReplies[comment.id] = true;
                }

                await this.fetchNestedComments(comment.id);
            }
        } catch (e) {
            console.error("Failed to post LinkedIn reply", e);
        } finally {
            this.state.commentsLoading = false;
        }
    }

    // ========== Nested Comments Methods ==========
    async fetchNestedComments(commentId) {
        if (this.state.repliesLoading[commentId]) return;
        this.state.repliesLoading[commentId] = true;
        try {
            // Use the current feed record to call the method
            const feed = this.state.commentingFeed;
            if (feed && feed.id) {
                const replies = await this.orm.call('social.media.feed', 'action_fetch_nested_comments', [[feed.id], commentId]);
                this.state.replies[commentId] = replies || [];
            } else if (feed === 'demo') {
                if (!this.state.replies[commentId]) this.state.replies[commentId] = [];
            }
        } catch (e) {
            console.error("Failed to fetch nested comments", e);
            this.state.replies[commentId] = [];
        } finally {
            this.state.repliesLoading[commentId] = false;
        }
    }

    async toggleReplies(commentId) {
        if (this.state.showReplies[commentId]) {
            this.state.showReplies[commentId] = false;
        } else {
            this.state.showReplies[commentId] = true;
            if (!this.state.replies[commentId]) {
                await this.fetchNestedComments(commentId);
            }
        }
    }

    detailsRefresh(self) {
        self.state.FbTotalComments = 0;
        self.state.IgTotalComments = 0;
        self.state.FbTotalLikes = 0;
        self.state.IgTotalLikes = 0;
        self.state.YtTotalComments = 0;
        self.state.YtTotalLikes = 0;
        self.state.LiTotalComments = 0;
        self.state.LiTotalLikes = 0;

        // Sum totals for non-LinkedIn platforms from the global list
        self.state.Feeds.forEach(post => {
            if (post.fb_media_number) {
                self.state.FbTotalComments += post.comments_count;
                self.state.FbTotalLikes += post.likes_count;
            }
            if (post.ig_media_number) {
                self.state.IgTotalComments += post.comments_count;
                self.state.IgTotalLikes += post.likes_count;
            }
            if (post.youtube_number) {
                self.state.YtTotalComments += post.comments_count;
                self.state.YtTotalLikes += post.likes_count;
            }
        });

        if (self.state.AllLinkedinFeedsForTotals) {
            let totalLikes = 0;
            let totalComments = 0;
            self.state.AllLinkedinFeedsForTotals.forEach(post => {
                totalLikes += (post.likes_count || 0);
                totalComments += (post.comments_count || 0);
            });
            self.state.LiTotalLikes = totalLikes;
            self.state.LiTotalComments = totalComments;
            self.state.LiPostCount = self.state.AllLinkedinFeedsForTotals.length;
        }
    }

    CreatePost() {
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                target: "new",
                name: this.title,
                res_model: "social.media.post",
                views: [[false, "form"]],
            },
        );

    }
    DisplayDemo() {
        if (this.state.demo) {
            this.state.demo = false
        }
        else {
            this.state.demo = true
        }
    }

    async detailsRefreshAll() {
        await this.orm.call("social.media.feed", "action_compute_likes_count_all", [""], {})
        window.location.reload();
    }
    DirectPartner(res_id) {
        this.actionService.doAction({
            res_model: 'res.partner',
            res_id: res_id,
            target: "current",
            type: "ir.actions.act_window",
            views: [
                [false, "form"]
            ],
        });
    }
    ComputeDemoData(feed) {
        var YtDetails = document.getElementById(("Details_" + feed));
        if (YtDetails.classList.contains("d-none")) {
            YtDetails.classList.remove("d-none")
        } else {
            YtDetails.classList.add("d-none")
        }
    }

    formatDate(dateStr) {
        if (!dateStr) return '';
        try {
            const date = deserializeDateTime(dateStr);
            return date.toFormat("dd MMM yyyy, HH:mm");
        } catch (e) {
            return dateStr;
        }
    }

    // ========== Emoji Picker Methods ==========
    onEmojiSelect(codepoints) {
        const target = this.lastEmojiTarget;
        if (!target || !target.el) return;

        const originalContent = target.el.value;
        const start = target.el.selectionStart;
        const end = target.el.selectionEnd;
        const left = originalContent.slice(0, start);
        const right = originalContent.slice(end, originalContent.length);

        target.el.value = left + codepoints + right;

        target.el.dispatchEvent(new InputEvent("input", { bubbles: true }));

        // Update state manually as well
        if (target.type === 'comment') {
            this.state.liCommentText = target.el.value;
        } else if (target.type === 'reply') {
            this.state.liReplyTexts[target.id] = target.el.value;
        }

        target.el.focus();
        const newCursorPos = start + codepoints.length;
        target.el.setSelectionRange(newCursorPos, newCursorPos);
    }

    addReplyEmojiPicker(ev, commentId) {
        const buttonRef = { el: ev.currentTarget };
        const inputEl = document.getElementById(`reply_input_${commentId}`);

        this.lastEmojiTarget = {
            el: inputEl,
            type: 'reply',
            id: commentId
        };

        this.emojiPicker.add(buttonRef, (codepoints) => this.onEmojiSelect(codepoints), { show: true });
    }

    onCommentEmojiClick() {
        this.lastEmojiTarget = {
            el: document.getElementById('li_comment_area'),
            type: 'comment'
        };
    }

    async loadMoreFeeds() {
        await this.fetchLinkedInFeeds(false); // Load next batch without resetting
    }
}

SocialMediaFeed.template = "cyllo_social_media_marketing.SocialMediaFeed";
actionRegistry.add("social_media_feed_dashboard_tag", SocialMediaFeed);