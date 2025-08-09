/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { SaleOrderLineProductField } from '@sale/js/sale_product_field';
import { serializeDateTime } from "@web/core/l10n/dates";
import { x2ManyCommands } from "@web/core/orm_service";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(SaleOrderLineProductField.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.dialog = useService("dialog");
    },
    async _onProductTemplateUpdate() {
        super._onProductTemplateUpdate(...arguments);
        const result = await this.orm.call(
            'product.template',
            'get_single_product_variant',
            [this.props.record.data.product_template_id[0]],
            {
                context: this.context,
            }
        );
        if(result && result.product_id) {
            if (this.props.record.data.product_id != result.product_id.id) {
                if (result.has_optional_products) {
                    this._openProductConfiguratorCosal();
                } else {
                    await this.props.record.update({
                        product_id: [result.product_id, result.product_name],
                    });
                    this._onProductUpdate();
                }
            }else {
                this._openProductConfiguratorCosal();
            }
        }else {
            this._openProductConfiguratorCosal();
        }
    },

    configurationButtonFAIcon() {
        return "fa-pencil";
    },    
    _editProductConfiguration() {
        super._editProductConfiguration(...arguments);
        if (this.props.record.data.is_configurable_product) {
            this._openProductConfiguratorCosal(true);
        }
    },

    async _openProductConfiguratorCosal(edit=false){
        console.log("-------- edit", edit);
        const saleId = this.props.record.evalContext.context.params.id;
        const context = { ...this.context };
        context.default_order_id = saleId;
        context.order_id = saleId
        context.default_product_template_id = this.props.record.data.product_template_id[0]

        await this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'sale.product.configuration',
            views: [[false, 'form']],
            target: 'new',
            context: context,
        });


    },


    _onClose(res) {
        return res?.special || this.props.reloadReport();
    },

    async loadMilestones() {
        var aa = this.$("#product_template_id")
        console.log("---aa ", aa);

        console.log("-----------conte ", JSON.stringify(this.context));
        var product_template_id = $('#product_template_id').val();
        console.log("---- product_template_id", product_template_id);
        const milestones = await this.orm.call(
            'sale.order.line',
            'add_product_configurator_cosal',
            {
                'product_template_id': product_template_id,
            },
            { context: this.context },
        );
        this.state.data.milestones = milestones;
        return milestones;
    },

});
