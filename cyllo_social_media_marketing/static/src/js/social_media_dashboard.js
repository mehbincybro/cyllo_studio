/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";
import { serializeDateTime, deserializeDateTime } from "@web/core/l10n/dates";

const actionRegistry = registry.category("actions");

export class SocialMediaDashboard extends Component {
    async setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            accounts: false,
            posts: false,
            activePosts: false,
            linkedinUsername: '',
            linkedinAccountName: '',
            linkedinAccessToken: '',
            isLinkedinInstalled: false
        });
        onWillStart(async () => {
            var self = this;
            this.state.isLinkedinInstalled = await this.orm.call("social.media.feed", "get_model", ["", "linkedin.account"], {});
            await this.orm.call("social.media.feed", "get_dashboard_data", [""]).then((results) => {
                self.state.accounts = results.dashboard_data;
                self.state.posts = results.posts;
                self.filterPosts()
            });
        });
    }

    OpenConnectModal(platform){
        this.state.selectedPlatform = platform;
        this.state.showConnectModal = true;
    }

    setActiveTab(ev,tab) {
        this.state.activeTab = tab;
        this.filterPosts()
    }
    filterPosts() {
        let filteredPosts = [];

        switch (this.state.activeTab) {
            case 'all':
                filteredPosts = this.state.posts;
                break;
            case 'facebook':
                filteredPosts = this.state.posts.filter(post => post.posted_on_facebook);
                break;
            case 'instagram':
                filteredPosts = this.state.posts.filter(post => post.posted_on_ig);
                break;
            case 'youtube':
                filteredPosts = this.state.posts.filter(post => post.posted_on_youtube);
                break;
            case 'linkedin':
                filteredPosts = this.state.posts.filter(post => post.posted_on_linkedin);
                break;
            default:
                filteredPosts = this.state.posts;
                break;
        }

        this.state.activePosts = filteredPosts;
    }

    CloseConnectModal() {
        this.state.showConnectModal = false;

        // Reset input fields
        this.state.facebookPageName = "";
        this.state.facebookAccessToken = "";
        this.state.facebookUserAccessToken = "";
        this.state.metaAppNumber = "";
        this.state.metaAppSecret = "";
        this.state.facebookInstaPageName = "";
        this.state.instagramAccessToken = "";
        this.state.instagramPageAccessToken = "";
        this.state.InstaMetaAppNumber = "";
        this.state.InstaMetaAppSecret = "";
        this.state.youtubeChannelName = "";
        this.state.clientNumber = "";
        this.state.clientSecret = "";
        this.state.linkedinUsername = "";
        this.state.linkedinAccountName = "";
        this.state.linkedinAccessToken = "";
    }


    async ConnectAccount() {
        let data = {};
        let message = false;

        switch (this.state.selectedPlatform) {
            case 'social.fb.account':
                data = {
                    facebook_page_name: this.state.facebookPageName,
                    facebook_access_token: this.state.facebookAccessToken,
                    facebook_user_access_token: this.state.facebookUserAccessToken,
                    meta_app_number: this.state.metaAppNumber,
                    meta_app_secret: this.state.metaAppSecret
                };

                if (!data.facebook_page_name) {
                    message = "Facebook Page Name is required";
                } else if (!data.facebook_access_token) {
                    message = "Facebook Access Token is required";
                } else if (!data.facebook_user_access_token) {
                    message = "Facebook User Access Token is required";
                } else if (!data.meta_app_number) {
                    message = "Meta App Number is required";
                } else if (!data.meta_app_secret) {
                    message = "Meta App Secret is required";
                }
                break;

            case 'social.insta.account':
                data = {
                    facebook_insta_page_name: this.state.facebookInstaPageName,
                    instagram_access_token: this.state.instagramAccessToken,
                    instagram_page_access_token: this.state.instagramPageAccessToken,
                    meta_app_number: this.state.InstaMetaAppNumber,
                    meta_app_secret: this.state.InstaMetaAppSecret
                };

                if (!data.facebook_insta_page_name) {
                    message = "Instagram Page Name is required";
                } else if (!data.instagram_access_token) {
                    message = "Instagram Access Token is required";
                } else if (!data.instagram_page_access_token) {
                    message = "Instagram Page Access Token is required";
                } else if (!data.meta_app_number) {
                    message = "Meta App Number is required";
                } else if (!data.meta_app_secret) {
                    message = "Meta App Secret is required";
                }
                break;

            case 'youtube.account':
                data = {
                    name: this.state.youtubeChannelName,
                    client_number: this.state.clientNumber,
                    client_secret: this.state.clientSecret
                };

                if (!data.name) {
                    message = "YouTube Channel Name is required";
                } else if (!data.client_number) {
                    message = "Client ID is required";
                } else if (!data.client_secret) {
                    message = "Client Secret is required";
                }
                break;

            case 'linkedin.account':
                var result = await this.orm.call("linkedin.account", "create", [{
                    name: this.state.linkedinAccountName || 'LinkedIn Account',
                    username: this.state.linkedinUsername,
                    linkedin_access_token: this.state.linkedinAccessToken || false,
                }]);
                if (result) {
                    if (!this.state.linkedinAccessToken) {
                        const action = await this.orm.call("linkedin.account", "action_connect_linkedin", [result]);
                        this.action.doAction(action);
                    } else {
                        // Manual token provided, account is already connected and synced in backend create()
                        this.CloseConnectModal();
                        // Refresh dashboard data
                        await this.orm.call("social.media.feed", "get_dashboard_data", [""]).then((results) => {
                            this.state.accounts = results.dashboard_data;
                            this.state.posts = results.posts;
                            this.filterPosts();
                        });
                    }
                }
                return;

            default:
                break;
        }

        if (message) {
            this.action.doAction({
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'warning',
                }
            });
        }

        try {
            var result = await this.orm.call("social.media.feed", "action_create_connect", ["", data, this.state.selectedPlatform], {});
            this.CloseConnectModal();
            if (result) {
                this.action.doAction({
                    type: "ir.actions.act_window",
                    res_model: "youtube.account",
                    res_id: result,
                    views: [[false, "form"]],
                    target: "current",
                });
            }
        } catch (error) {
            return false;
        }

    }
    async OpenView(model) {
        var model_exist = await this.orm.call("social.media.feed", "get_model", ["", model], {});
        if (!model_exist) {
            let message = '';
            if (model === 'social.fb.account') {
                message = 'Install Cyllo Facebook module';
            }
            else if (model === 'social.insta.account') {
                message = 'Install Cyllo Instagram module';
            }
            else if (model === 'youtube.account') {
                message = 'Install Cyllo YouTube module';
            }
            else if (model === 'linkedin.account') {
                message = 'Install Cyllo LinkedIn module';
            }
            else {
                message = 'Install the required module';
            }

            this.action.doAction({
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'info',
                }
            });
            return
        }
        this.OpenConnectModal(model);
    }

    ViewAccounts(account) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: account.platform,
            res_id: account.id,
            views: [[false, "form"]],
            target: "current",
        });
    }
    CreatePost() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: 'social.media.post',
            views: [[false, "form"]],
            target: "current",
        });
    }

    OpenFeed(feed) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: 'Feed',
            res_model: "social.media.feed",
            views: [[false, "kanban"]],
            domain: [["id", "=", feed]],
            target: "current",
        });
    }

    OpenModal() {
        this.state.showModal = true;
    }

    CloseModal() {
        this.state.showModal = false;
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
}

SocialMediaDashboard.template = "cyllo_social_media_marketing.SocialMediaDashboard";
actionRegistry.add("social_media_dashboard", SocialMediaDashboard);
