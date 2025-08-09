# -*- coding: utf-8 -*-

import datetime
from odoo import _, api, fields, tools, models, Command
from odoo.tools.float_utils import float_is_zero
from odoo.tests import Form, HttpCase, tagged
from odoo.exceptions import UserError, ValidationError
from markupsafe import Markup

import logging
_logger = logging.getLogger(__name__)

LOG = 1


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _skip_procurement(self, procurement):
        res = super(ProcurementGroup, self)._skip_procurement(procurement)
        rule = self._get_rule(procurement.product_id, procurement.location_id, procurement.values)
        if rule:
            action = 'pull' if rule.action == 'pull_push' else rule.action
            if action == 'manufacture':
                #raise UserError('_skip_procurement: %s %s'%(procurement, procurement.product_id))
                #if not procurement.values.get('bom_id'):
                #    raise ValidationError('El abastecimiento de: %s en la línea del producto: %s no tiene asignado lista de materiales.'%(procurement.origin, procurement.product_id.display_name))
                res = procurement.values.get('bom_id') and procurement.product_id != procurement.values['bom_id'].product_id
        return res

class StockMove(models.Model):
    _inherit = 'stock.move'

    ###### GERMAN PONCE (CHERMAN)  -  JUL-AGOS 2025 ##########
    n_cuts = fields.Integer("Numero de Cortes", default=1)
    ##########################################################

    def _prepare_procurement_values(self):
        values = super()._prepare_procurement_values()
        group_id = values.get('group_id')
        if group_id:
            bom_ids = group_id.sale_id.mapped('order_line.bom_id')#.filtered(lambda b: )
            if len(bom_ids) == 1:
                values['bom_id'] = bom_ids
                if len(bom_ids.bom_line_ids) == 1:
                    values['bom_line_id'] = bom_ids.bom_line_ids.id
            else:
                values['bom_id'] = bom_ids.filtered(lambda b: b.product_id == self.product_id)            
        return values

class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _should_auto_confirm_procurement_mo(self, p):
        if self.env.context.get('not_confirm'):
            return False
        return super(StockRule, self)._should_auto_confirm_procurement_mo(p)

    def _get_matching_bom(self, product_id, company_id, values):
        if values.get('bom_id', False):
            return values['bom_id']
        if values.get('orderpoint_id', False) and values['orderpoint_id'].bom_id:
            return values['orderpoint_id'].bom_id
        return self.env['mrp.bom']._bom_find(product_id, picking_type=self.picking_type_id, bom_type='normal', company_id=company_id.id)[product_id]

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    ###### GERMAN PONCE (CHERMAN)  -  JUL-AGOS 2025 ##########
    n_cuts = fields.Integer("Numero de Cortes", default=1)
    ##########################################################

    @api.model_create_multi
    def create(self, vals_list):
        res = super(MrpProduction, self).create(vals_list)
        return res

    def _prepare_stock_lot_values(self):
        values = super(MrpProduction, self)._prepare_stock_lot_values()
        return values

    def _get_move_raw_values(self, product_id, product_uom_qty, product_uom, operation_id=False, bom_line=False):
        data = super(MrpProduction, self)._get_move_raw_values(product_id, product_uom_qty, product_uom, operation_id=operation_id, bom_line=bom_line)
        return data 

    def _get_moves_raw_values(self):
        moves = super(MrpProduction, self)._get_moves_raw_values()
        return moves

    def _get_moves_finished_values(self): # TODO borrar este método para que opere el original
        moves = []
        for production in self:
            if production.product_id in production.bom_id.byproduct_ids.mapped('product_id'):
                _logger.info('05 ********** cosal _get_moves_finished_values: bom: %s bom_prod: %s FP: %s MP: %s'%(production.bom_id, production.bom_id.product_id, production.product_id, production.bom_id.byproduct_ids.mapped('product_id')))
                raise UserError(_("03 You cannot have %s  as the finished product and in the Byproducts", self.product_id.name))
            moves.append(production._get_move_finished_values(production.product_id.id, production.product_qty, production.product_uom_id.id))
            for byproduct in production.bom_id.byproduct_ids:
                if byproduct._skip_byproduct_line(production.product_id):
                    continue
                product_uom_factor = production.product_uom_id._compute_quantity(production.product_qty, production.bom_id.product_uom_id)
                qty = byproduct.product_qty * (product_uom_factor / production.bom_id.product_qty)
                moves.append(production._get_move_finished_values(
                    byproduct.product_id.id, qty, byproduct.product_uom_id.id,
                    byproduct.operation_id.id, byproduct.id, byproduct.cost_share))
        return moves


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    product_name = fields.Char(
        related="product_id.name",
        string="Name")
    product_wide_qty = fields.Float(
        related="product_id.product_wide_qty",
        string='Ancho')
    product_subfamilia = fields.Char(
        related="product_id.product_subfamilia",
        string='Subfamilia')

    @api.depends('location_id', 'lot_id', 'package_id', 'owner_id')
    def _compute_display_name(self):
        """name that will be displayed in the detailed operation"""
        name = super(StockQuant, self)._compute_display_name()
        for record in self:
            if record.product_id.product_wide_qty and record.warehouse_id:
                display_name = record.display_name
                display_name = "[%s] %s - %s "%(record.warehouse_id.name, record.product_id.name, record.product_id.product_wide_qty)
                record.display_name = display_name

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super(SaleOrder, self.with_context(not_confirm=True)).action_confirm()
        for mo in self.mrp_production_ids:
            self.action_process_mrp(mo)
        return res

    def action_process_mrp(self, mo=False):
        for rec in self.order_line.filtered(lambda l: l.product_id == mo.product_id and l.wiz_component_id and l.bom_id and not l.mrp_id):
            vals = {
                "source": rec.id,
                "sale_line_id": rec.id,
                "analytic_distribution": rec.analytic_distribution,
                "product_comment": rec.mrp_notes or "",
            }
            mo.write(vals)
            moves_raw_values = mo._get_moves_raw_values()
            
            # Variables para información de cortes
            cortes_info = []
            mo_n_cuts = 1  # Valor por defecto
            
            #------------------------
            # Agrega Nota de los cortes requeridos TODO agregar nota y subproductos
            #------------------------
            to_cut = millares_vendidos = kilos = 0
            medida = ''
            mo_n_cuts_top = 1
            for conf in rec.wiz_component_id:
                for comp in conf.product_component_ids.filtered(lambda c: c.selected):
                    for indx, corte in enumerate(comp.product_cortes_ids):
                        note = f"<p>Fecha: %s</p>"%datetime.date.today()
                        if corte.product_cosal == 'hoja':
                            note += f"<p><strong>HOJEADO DE ROLLO</strong></p>" 
                        elif corte.product_cosal == 'rollo':
                            note += f"<p><strong>CORTE DE ROLLO</strong></p>" 
                        note += f"<p><ul><li>Requiere %s corte%s</li>"%( corte.product_no_corte, ('s' if corte.product_no_corte > 1 else '') ) 
                        note += f"<li>Ancho: %s</li>"%( corte.product_wide )
                        if corte.product_cosal == 'hoja':
                            note += f"<li>Largo: %s</li>"%( corte.product_long )
                        note += f"</ul></p>"
                        product_comment = 'Tipo de Venta: %s\n%s'%(corte.sale_type, corte.product_comment)
                        if product_comment:
                            if '\n' in product_comment:
                                product_comment = '<ul><li>' + '</li><li>'.join(map(str, product_comment.split('\n'))) + '</li>' 
                            note += f"<p><strong>COMENTARIOS DE VENTAS</strong></br>" + product_comment
                            note += f"</p>"
                        mo.message_post(body=Markup(note))
                        
                        # Recolectar información de cortes
                        cortes_info.append({
                            'product_id': rec.product_id.id,
                            'product_no_corte': corte.product_no_corte,
                            'corte_id': corte.id,
                            'product_wide': corte.product_wide,
                            'product_long': corte.product_long
                        })
                        
                        #### Numero de Cortes #####
                        if corte.product_no_corte > mo_n_cuts_top:
                            mo_n_cuts_top = corte.product_no_corte

                        to_cut += corte.product_no_corte
                        millares_vendidos += corte.product_quantity if corte.product_cosal == 'hoja' else 0
                        medida += ', ' if medida else ''
                        medida += '%s x %s cm '%(corte.product_wide, corte.product_long) if corte.product_cosal == 'hoja' else '%s cm'%corte.product_wide
                        kilos += corte.product_weight if corte.product_cosal == 'hoja' else corte.product_quantity
                        
                    # Actualizar la orden de producción con el n_cuts específico del producto
                    mo.write({
                        'sale_type': corte.sale_type, 
                        'to_cut': 0, 
                        'millares_vendidos': millares_vendidos,
                        'n_cuts': mo_n_cuts  # n_cuts específico del producto de la MO
                    })
            # Actualizar n_cuts en los subproductos
            self._update_n_cuts_in_byproducts(mo, cortes_info)
            mo.write({
                        'n_cuts': mo_n_cuts_top  # n_cuts específico del producto de la MO
                    })
        self._compute_mrp_production_ids()

    def _update_n_cuts_in_byproducts(self, mo, cortes_info):
        """Actualiza el campo n_cuts en los subproductos basado en la información de cortes"""
        if LOG == 1: 
            _logger.info('******* UPDATING N_CUTS IN BYPRODUCTS')
        
        # Actualizar subproductos en move_byproduct_ids
        for move in mo.move_byproduct_ids:
            # Buscar el corte correspondiente por product_id
            n_cuts_value = 0
            for line in self.order_line:
                # Aquí puedes ajustar la lógica de matching según tus necesidades
                # Por ejemplo, si el subproducto está relacionado con un corte específico
                if move.product_id.id == line.product_id.id:
                    n_cuts_value = line.n_cuts
                    break

            if n_cuts_value == 0 and cortes_info:
                corte_match = next((c for c in cortes_info if c['product_id'] == move.product_id.id), None)
                move.write({'n_cuts': corte_match['product_no_corte']})
                if corte_match:
                    n_cuts_value = corte_match['product_no_corte']

            move.write({'n_cuts': n_cuts_value})
            if LOG == 1:
                _logger.info('******* Updated n_cuts=%s for byproduct %s' % (
                    corte_match['product_no_corte'], move.product_id.name))

            
    def get_value_att_val(self, att_cosal, product_att, product_tmpl_id):
        ProductAttribute = self.env['product.attribute']
        ProductAttributeValue = self.env['product.attribute.value']
        TemplateAttributeValue = self.env["product.template.attribute.value"]
        att_val = TemplateAttributeValue.search([
            ('attribute_id.attribute_cosal', '=', att_cosal), 
            ('product_tmpl_id', '=', product_tmpl_id.id)
        ]).filtered(lambda p: float('0.0' if p.name == '-' else p.name) == product_att)
        if not att_val:
            attribute_id = ProductAttribute.search([('attribute_cosal', '=', att_cosal)])
            attribute_value_id = product_tmpl_id.attribute_line_ids.filtered(lambda p: p.attribute_id == attribute_id)
            wide_id = ProductAttributeValue.search([
                ('attribute_id', '=', attribute_id.id)
            ]).filtered(lambda p: float('0.0' if p.name == '-' else p.name) == product_att)
            if not wide_id:
                wide_id = ProductAttributeValue.create({
                    'name': product_att,
                    'attribute_id': attribute_id and attribute_id.id or False
                })
            attribute_value_id.write({'value_ids':[(4,wide_id.id)]})

            att_val = TemplateAttributeValue.search([
                ('attribute_id.attribute_cosal', '=', att_cosal), 
                ('product_tmpl_id', '=', product_tmpl_id.id)
            ]).filtered(lambda p: float('0.0' if p.name == '-' else p.name) == product_att)
        return att_val

    def get_configurations_components_ids(self, product_template_id=None):
        ProductProduct = self.env['product.product']
        for line_id in self:
            product_attrs = line_id.product_id.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.exclude_search == False)
            product_ids = ProductProduct.search([
                ('product_tmpl_id', '=', line_id.product_template_id.id), 
                ('id', '!=', line_id.product_id.id)
            ], order="product_wide").filtered(lambda p: 
                p._get_domain_product_template_attribute_value_ids() == product_attrs.ids and 
                float_is_zero(p.qty_available, precision_rounding=line_id.product_uom.rounding) != True and 
                p.product_wide >= line_id.product_wide)
            return product_ids


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    _description = _('Sale_order Line')

    requiere_corte = fields.Boolean(string="Requiere Corte")
    is_configurable_product = fields.Boolean(
        string="Is the product configurable?",
        related='product_template_id.has_configurable_attributes',
        depends=['product_id'])
    product_template_attribute_value_ids = fields.Many2many(
        related='product_id.product_template_attribute_value_ids',
        depends=['product_id'])
    #product_component_wiz = fields.Text(string="Wiz Components")

    wiz_component_id = fields.Many2one('sale.product.configuration', string='Configurador', copy=False)
    wiz_corte_id = fields.Many2one('sale.product.configuration.cortes', string='Corte', copy=False)
    product_components = fields.Char(string="Components")
    bom_id = fields.Many2one(
        'mrp.bom', string='Bill of Material', 
        copy=False, 
        help="Bill of materials for the product")

    mrp_location_src_id = fields.Many2one('stock.location', string='Location', copy=False)
    mrp_id = fields.Many2one('mrp.production', string='Mrp Order', copy=False)
    mrp_notes = fields.Text(string='Notas')
    
    n_cuts = fields.Integer("Numero de Cortes", default=1)


    def _prepare_procurement_values(self, group_id=False): 
        """ Prepare specific key for moves or other components that will be created from a stock rule
        coming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        values = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        self.ensure_one()
        values.update({
            'bom_id': self.bom_id,
        })
        return values

    def action_open_wizard_components(self):
        ctx = dict(self.env.context)
        if self.wiz_component_id:
            wiz_id = self.wiz_component_id
            if wiz_id:
                wiz_form_id = self.env.ref('bias_custom_cosal.view_sale_component_configuration_form', raise_if_not_found=False)
                ctx["default_id"] = wiz_id.id
                return {
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'sale.product.configuration',
                    'views': [(False, 'form')],
                    'view_id': wiz_form_id,
                    'target': 'new',
                    'res_id': wiz_id.id,
                    'context': ctx,
                }
        return True

    #=== ACTION METHODS ===#
    def action_add_from_configurations(self):
        ctx = dict(self.env.context)
        return {
            'name': _('Configurador de Productos'),
            'view_mode': 'form',
            'res_model': 'sale.product.configuration',
            'view_id': self.env.ref('bias_custom_cosal.view_sale_filter_configuration_form').id,
            'type': 'ir.actions.act_window',
            'context': ctx,
            'target': 'new'
        }

    """def _action_launch_mrp_sale_configuration(self, previous_product_uom_qty=False):
        for rec in self:
            if rec.bom_id:
                mo = self.env['mrp.production'].search([('sale_line_id', '=', rec.id)])
                if mo:
                    move = self.env['stock.move'].search([('sale_line_id', '=', rec.id)])
                    if not move.created_production_id:
                        move.created_production_id = mo.id
    """




""" 
            line_vals = eval(rec.product_component_wiz)
            line_vals["line_id"] = rec.id
            product_component_ids = [item for item in (line_vals.get("product_component_ids") or []) if item['selected'] == True]

            #------------------------
            # Valida que el Producto Terminado y Componente sean diferente
            #------------------------
            val_continue = False
            for comp in product_component_ids:
                product_id = ProductProduct.browse(comp["product_id"])
                val_continue = True if product_id == rec.product_id else False
            if val_continue:
                continue
            #------------------------

            location_id = False
            for com in product_component_ids:
                quant_id = StockQuants.browse(com["quant_id"])
                location_id = quant_id and quant_id.location_id or False

            mo_id = self.env['mrp.production'].search([('sale_line_id', '=', rec.id)], limit=1)
            if not mo_id:
                mo_form = Form(MrpProduction)
                mo_form.product_id = rec.product_id
                mo_form.product_uom_id = rec.product_uom
                mo_form.product_qty = rec.product_uom_qty
                mo_form.origin = self.name
                mo_form.location_src_id = location_id  or self.warehouse_id.lot_stock_id
                mo_form.location_dest_id = self.warehouse_id.lot_stock_id
                mo_form.analytic_distribution = rec.analytic_distribution
                mo_form.product_comment = line_vals.get("product_comment", "") or ""
                mo_id = mo_form.save()
                mo_id.write({
                    'source': rec.id,
                    'sale_line_id': rec.id
                })
            with Form(mo_id) as mo:
                for comp in product_component_ids:
                    product_id = ProductProduct.browse(comp["product_id"])
                    with mo.move_raw_ids.new() as mline:
                        mline.product_id = product_id
                        mline.product_uom_qty = rec.product_uom_qty
                        mline.product_uom = rec.product_uom


        #    else:
        #        vals.update({
        #            "product_id": rec.product_id.id,
        #            "product_uom_id": rec.product_id.uom_id.id,
        #            "origin": self.name,
        #            "company_id": self.env.user.company_id.id,
        #            "product_qty": rec.product_uom_qty,
        #            "bom_id": rec.bom_id.id,
        #        })
        #        mo = self.env["mrp.production"].create(vals)
        """


