/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { rpc } from "@web/core/network/rpc_service";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

class RecordSaleLineDialog extends Dialog {
    setup() {
        super.setup();
        this.record = this.props.record;
    }
}

RecordSaleLineDialog.template = "bias_custom_cosal.RecordSaleLineDialog";

async function action_saleline_open_dialog(recordId) {
    const dialog = new RecordSaleLineDialog(null, {
        title: 'Edit Record',
        record: {},
        buttons: [
            { text: "Close", close: true }
        ],
    });

}

registry.category("actions").add("action_open_dialog_js", action_saleline_open_dialog);

