/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

const actionRegistry = registry.category("actions");

export class SocialMediaFeed extends Component {
    async setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            Feeds: false,
            fields: ['id', 'description', 'author_name', 'author_link', 'posted_date', 'author_link_url', 'posted_image', 'profile_image_url', 'posted_image_url', 'profile_image', 'likes_count', 'comments_count', 'post_id'],
            demo:false
        });
        onWillStart(async () => {
            this.state.Feeds = await this.orm.searchRead('social.media.feed', [], this.state.fields)
            this.state.FbFeeds = this.state.Feeds.filter(r => r.fb_media_number !== false)
            this.state.InstaFeeds = this.state.Feeds.filter(r => r.ig_media_number !== false)
            this.state.YoutubeFeeds = this.state.Feeds.filter(r => r.youtube_number !== false)
            this.detailsRefresh(this)
        })
    }

    detailsRefresh(self) {
        self.state.FbTotalComments = 0;
        self.state.IgTotalComments = 0;
        self.state.FbTotalLikes = 0;
        self.state.IgTotalLikes = 0;
        self.state.YtTotalComments = 0;
        self.state.YtTotalLikes = 0;
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
    DisplayDemo(){
        if(this.state.demo){
            this.state.demo=false
        }
        else{
            this.state.demo=true
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
}

SocialMediaFeed.template = "cyllo_social_media_marketing.SocialMediaFeed";
actionRegistry.add("social_media_feed_dashboard_tag", SocialMediaFeed);