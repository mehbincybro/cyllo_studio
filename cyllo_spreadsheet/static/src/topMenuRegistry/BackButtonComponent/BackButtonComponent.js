/** @odoo-module */
import {Component, useState, useRef} from "@odoo/owl";

export class BackButtonComponent extends Component {
    static template = 'BackButtonComponent';

    setup() {
        this.root = useRef('root')
    }

    handleOnClickBack() {
        window.history?.back();
    }

}