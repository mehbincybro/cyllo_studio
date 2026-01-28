/** @odoo-module **/

import { Component } from "@odoo/owl";

export class CogMenuUpload extends Component {
    setup() {
        // Bind the action to props
        this.props.uploadVisitingCard = this.uploadVisitingCard.bind(this);
    }

    uploadVisitingCard() {
        // Replace this with your real logic
        alert("Upload Visiting Card clicked!");
        console.log("Upload Visiting Card action executed");
    }
}
