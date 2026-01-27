/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.SupportTicketPortal = publicWidget.Widget.extend({
    selector: '.cyllo_register_support_ticket_form',
    events: {
        'mouseover .star': '_onMouseoverRating',
        'mouseout .star': '_onMouseOutRating',
        'click .star': 'onClickStar',
    },

     /**
     * The  methods defined here are used for adding the comments and rating at
     * the time of confirmation of orders and different styles were applied at
     * the time of occurrence of some events like button click, mouseout etc.
     */
    _onMouseoverRating: function(ev) {
        var onStar = parseInt(ev.currentTarget.getAttribute("value"), 10);
        this.$(".star").each(function(e) {
            if (e < onStar) {
                $(this).addClass("hover");
            } else {
                $(this).removeClass("hover");
            }
        });
    },
    /**
    while mouse out remove the class "hover"
    */
    _onMouseOutRating: function(ev) {
        this.$(".star").each(function(e) {
            $(this).removeClass("hover");
        })
    },
    onClickStar: function(event){
        var onStar = parseInt(event.currentTarget.getAttribute("value"), 10);
        var stars = this.$(".star");
        for (var i = 0; i < stars.length; i++) {
            stars[i].classList.remove("selected");
        }
        for (var i = 0; i < onStar; i++) {
            stars[i].classList.add("selected");
        }
        this.$('.rate_value').val(onStar)
    }
})