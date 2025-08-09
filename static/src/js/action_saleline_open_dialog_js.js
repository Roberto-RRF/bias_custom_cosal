/** @odoo-module */

import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { Component, onWillStart, useState, useSubEnv } from "@odoo/owl";
import { Dialog } from '@web/core/dialog/dialog';
import { useService } from "@web/core/utils/hooks";
import js_open_dialog from '@bias_custom_cosal/js/js_saleline_open_dialog';

export class AdvancedDashboard extends Component {
    setup(){
        this.action = useService("action");
        this.rpc = this.env.services.rpc
    }
    loadData(){
        let self = this;
         rpc.query({
            model: 'partner.dashboard',
            method: 'get_values',
            args:[]
            }).then(function(data){
                console.log(data, 'dataaaa')
                self.AdvancedDashboard.data = data;
        });
    }
}
AdvancedDashboard.template = "client_action.advanced_dashboard"
registry.category("actions").add("advanced_dashboard", AdvancedDashboard)