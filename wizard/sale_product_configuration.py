# -*- coding: utf-8 -*-
import json
from odoo import _, api, fields, tools, models, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tests import Form, tagged

import logging
_logger = logging.getLogger(__name__)

LOG = 0

class SaleProductConfigurationCortes(models.Model):
    _name = 'sale.product.configuration.cortes'
    _description = _('Sale Product Configuration')

    name = fields.Char('Name', default="")
    sequence = fields.Integer('Sequence',  default=1, help="The first in the sequence is the default one.")
    product_id = fields.Many2one('product.product', string ='Producto')
    product_no_corte = fields.Integer(string ="Numero de Corte", default=1)
    select_product = fields.Boolean('Seleccionar Producto', store=True, compute='_compute_product_wide', precompute=True)
    product_template_id = fields.Many2one(
        comodel_name ='product.template', 
        string ='Template',
        compute='_compute_product_wide',
        store=True, readonly=False, required=True, precompute=True, 
        ondelete='restrict')
    product_wide = fields.Float(
        string ="Ancho",
        compute='_compute_product_wide',
        store=True, readonly=False, required=True, precompute=True)
    product_rm_wide = fields.Float(
        string ="Ancho MP",
        compute='_compute_product_wide',
        store=True, readonly=False, required=True, precompute=True)
    product_long = fields.Float(
        string ="Largo",
        #compute='_compute_product_wide', precompute=True, store=True, required=True, 
        readonly=False)
    product_quantity = fields.Float(
        string ="Cantidad",
        digits='Product Unit of Measure',
        compute='_compute_product_wide',
        store=True, readonly=False, required=True, precompute=True)
    product_quantity_uom = fields.Selection([
        ('kg', 'Kilos'),
        ('millares', 'Millares')
    ], string ="Cantidad UdM", default="kg")
    product_cosal = fields.Selection(related='product_template_id.product_cosal')
    product_tail = fields.Float('Sobrante')
    product_tail_type = fields.Selection([
        ('equal', 'Igual'),
        ('greater', 'Mayor'),
        ('lower', 'Menor'),
    ], string ="Tipo de Cola", default="equal")
    product_subproduct = fields.Selection([
        ('product', 'Cliente'),
        ('subproduct', 'Inventario'),
        ('scrap', 'Merma'),
    ], string ="Subproduct", default="product", required=True)
    sale_type = fields.Selection([
        ('exact', 'Cantidad Exacta'),
        ('complete', 'Rollo Completo'),
    ], string ="Tipo de Venta", default="complete", required=True)
    old_subproduct = fields.Char()
    product_weight = fields.Float('Kg/Millar PT')
    product_rm_weight = fields.Float('Kg/Millar MP')
    product_centro = fields.Many2one(
        comodel_name = 'product.template.attribute.value', 
        string ="Centro",
        change_default =True,
        domain ="[('product_tmpl_id','=',product_template_id), ('attribute_id.attribute_cosal', '=', 'centro')]")
    product_diametro = fields.Many2one(
        comodel_name = 'product.template.attribute.value', 
        string ="Diametro",
        change_default =True,
        domain ="[('product_tmpl_id','=',product_template_id), ('attribute_id.attribute_cosal', '=', 'diametro')]")
    product_certificado = fields.Many2one(
        comodel_name = 'product.template.attribute.value', 
        string ="Certificado",
        change_default =True,
        domain ="[('product_tmpl_id','=',product_template_id), ('attribute_id.attribute_cosal', '=', 'certificado'), ('id','=',product_certificado_id)]")
    product_certificado_id = fields.Integer(string ="Certificado ID")
    
    wizard_id = fields.Many2one('sale.product.configuration.combination', 'Combination', ondelete='cascade')
    # ==== Precio Producto ====
    product_price = fields.Float('Precio KG')
    product_price_inter = fields.Float('Flete Inter Almacen')
    product_price_cliente = fields.Float('Flete Cliente')
    product_price_empaquetado = fields.Float('Empaquetado')
    product_price_hojeado = fields.Float('Hojeado')
    product_price_guillotinado = fields.Float('Guillotinado')
    product_price_rebobinado = fields.Float('Rebobinado')
    product_price_centro = fields.Float('Centro')
    product_price_diametro = fields.Float('Diametro')
    product_price_cortes = fields.Float('Cortes')
    product_price_total = fields.Float('Importe', store=True, compute='_compute_product_total')
    product_add_flete_inter = fields.Boolean('Incluir Flete Inter', default=True)
    product_add_flete_cliente = fields.Boolean('Incluir Flete Cliente', default=True)
    product_price_new = fields.Float('Precio Actualizado')
    product_price_factor = fields.Float('Factor Merma', digits=(16,6))
    product_price_factor_fp = fields.Float('Factor PT', digits=(16,6))
    product_factor_share = fields.Float('Factor Share', digits=(16,6))
    product_factor_tail = fields.Float('Factor Tail', digits=(16,6))
    product_factor_weight = fields.Float('Factor Peso', digits=(16,6))

    # ==== Comentarios ====
    product_comment = fields.Text(string ='Comentarios')

    #=== COMPUTE METHODS ===#
    @api.depends('wizard_id', 'sequence')
    def _compute_product_wide(self):
        if LOG == 1: _logger.info('******* 1')
        for corte in self:
            cortes_ids = corte.wizard_id.product_cortes_ids
            if not corte.wizard_id:
                continue
            if not len(cortes_ids):
                continue
            product_quantity = corte.product_quantity
            if len(cortes_ids) == 1:
                select_product = True
                # product_quantity = 0
                product_tmpl_id = corte.wizard_id.product_id.product_tmpl_id or False
                old_subproduct = 'product'
            else:
                product_quantity = cortes_ids[0].product_quantity
                product_tmpl_id = cortes_ids[0].product_template_id
                old_subproduct = cortes_ids[(len(cortes_ids)-2)].old_subproduct
                self.product_centro  = cortes_ids[0].product_centro # TODO
                self.product_diametro  = cortes_ids[0].product_diametro # TODO
                select_product = False
                if product_tmpl_id.product_cosal=='hoja':
                    select_product = True
            
            corte.select_product = select_product
            corte.product_template_id = product_tmpl_id
            corte.product_rm_wide = corte.wizard_id.product_wide or 0.0
            corte.product_quantity = product_quantity
            corte.old_subproduct = old_subproduct
            #corte.product_long = corte.wizard_id.product_long or 0.0

    @api.depends(
        'product_price',
        'product_price_new',
        'product_price_inter', 
        'product_price_cliente',
        'product_price_empaquetado',
        'product_price_hojeado',
        'product_price_guillotinado',
        'product_price_rebobinado',
        'product_price_centro',
        'product_price_diametro',
        'product_price_cortes',
        'product_add_flete_inter', 
        'product_add_flete_cliente')
    def _compute_product_total(self):
        if LOG == 1: _logger.info('******* 2')
        for corte in self:
            product_price = corte.product_price_new if corte.product_price_new else corte.product_price
            product_total = (product_price +
                             corte.product_price_empaquetado +
                             corte.product_price_hojeado +
                             corte.product_price_guillotinado +
                             corte.product_price_rebobinado +
                             corte.product_price_centro +
                             corte.product_price_diametro +
                             corte.product_price_cortes)
            if corte.product_add_flete_inter:
                product_total += corte.product_price_inter
            if corte.product_add_flete_cliente:
                product_total += corte.product_price_cliente
            #_logger.info('***** _compute_product_total: %s'%product_price)
            corte.product_price_total = product_total


    #=== ONCHANGE METHODS ===#
    @api.onchange('product_template_id')
    def _onchange_product_template_id(self):
        if LOG == 1: _logger.info('******* 3')
        self.product_price = self.wizard_id.product_id.list_price

    @api.onchange('product_template_id', 'product_wide', 'product_long', 'product_quantity_uom', 'product_no_corte')#, 'product_subproduct')
    def _onchange_parameters(self):
        if LOG == 1: _logger.info('******* 4')
        conf = self.wizard_id
        product_wide = product_long = 0
        vals, product_quantity_uom, product_subproduct = {}, "kg", False
        rm_wide = conf.product_wide / 100
        fp_wide = self.product_wide / 100
        pt_lenght = self.product_long / 100
        cut_no = self.product_no_corte
        certificado_id = conf.product_id.product_template_variant_value_ids.filtered(lambda v: v.attribute_id.attribute_cosal == 'certificado').id 
        tail = self.get_tail()

        if self.product_template_id.product_cosal == 'rollo':   # PT: "Kg"
            if self.select_product:
                vals.update(product_centro = conf.product_id.product_template_variant_value_ids.filtered(lambda v: v.attribute_id.attribute_cosal == 'centro').id )
                vals.update(product_diametro = conf.product_id.product_template_variant_value_ids.filtered(lambda v: v.attribute_id.attribute_cosal == 'diametro').id )
        elif self.product_template_id.product_cosal == 'hoja':  # PT: "millares"
            product_quantity_uom = "millares"
            if not self.product_wide:
                vals.update(product_wide = self.get_product_wide())
            if not self.product_long:
                vals.update(product_long = self.get_product_long())
        if len(conf.product_cortes_ids) > 1:
            product_subproduct = conf.product_cortes_ids[len(conf.product_cortes_ids)-2].product_subproduct
            
        vals.update(product_tail = tail * 100)
        vals.update(product_certificado = certificado_id)
        vals.update(product_certificado_id = certificado_id)
        vals.update(product_quantity_uom = product_quantity_uom)

        if not (fp_wide and cut_no):
            if product_subproduct:
                vals.update(product_subproduct = product_subproduct)
            self.write(vals)
            return  # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

        tail_type = 'equal' if fp_wide==tail else 'lower' if tail < fp_wide else 'greater' if tail > fp_wide else False
        vals.update(product_tail_type = tail_type)
        if not tail_type:
            raise ValidationError('Error al calcular cola.')
        if not (self.product_template_id and self.product_quantity):
            if product_subproduct:
                vals.update(product_subproduct = product_subproduct)
                self.write(vals)
            return  # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            
        if self.old_subproduct == self.product_subproduct:
            if tail_type == 'lower':
                if tail <= 0.10:
                    product_subproduct = 'scrap'
                else:
                    product_subproduct = 'subproduct'
            elif tail_type == 'equal':
                product_subproduct = 'subproduct'
            if product_subproduct:
                vals.update(product_subproduct = product_subproduct)
        vals.update(old_subproduct = product_subproduct or self.product_subproduct)
        
        if any([c.get_tail() for c in conf.product_cortes_ids]):
            if tail == 0:
                raise ValidationError(u'El último corte es innecesario')
            elif tail < 0:
                raise ValidationError("El ancho de la materia no es suficiente, la suma de cortes se pasa por: %s cm"%(-tail*100))
            elif (cut_no * fp_wide) > rm_wide:
                raise UserError(u"El ancho del componente es menor que el ancho total de los cortes definidos para fabricar el producto a vender") 
            elif fp_wide > rm_wide:
                raise UserError(u"El ancho del componente es menor que el Ancho definido para el producto a vender") 
            elif (fp_wide == rm_wide):
                raise UserError(u"El ancho del componente es igual que el Ancho definido no se necesitan cortes") 
            elif product_quantity_uom == "kg" and self.product_quantity > conf.available_quantity:
                raise ValidationError("La cantidad del producto terminado (KG): '%s' es mayor que la materia prima: '%s' "%(round(self.product_quantity,2), round(conf.available_quantity,2)) )
        self.write(vals)
        for indx, corte in enumerate(conf.product_cortes_ids):
            factors = corte.get_factor(indx, flag='corte')
            self.write_factor(factors)

    def get_product_wide(self):
        if LOG == 1: _logger.info('******* 4.1')
        conf = self.wizard_id
        product_wide = conf.product_wide
        if len(conf.product_cortes_ids) > 1:
            product_wide = conf.product_cortes_ids[-2].product_tail
        return product_wide or conf.product_long

    def get_product_long(self):
        if LOG == 1: _logger.info('******* 4.2')
        conf = self.wizard_id
        product_long = conf.product_cortes_ids[0].product_long
        return product_long or conf.product_long

    def get_tail(self):
        if LOG == 1: _logger.info('******* 5')
        conf = self.wizard_id
        tail = 0
        actual = conf.product_cortes_ids[-1]
        if actual.product_wide == 0:
            product_cortes_ids = conf.product_cortes_ids - actual
        else:
            product_cortes_ids = conf.product_cortes_ids.filtered(lambda c: actual.sequence >= c.sequence and ('virtual' in str(c) and actual.sequence != c.sequence or 'virtual' not in str(c))  )

        if not product_cortes_ids and actual.product_wide == 0 and self.product_cosal=='rollo':
            tail = conf.product_wide / 100
        elif all([conf.product_wide == c.product_wide for c in product_cortes_ids]):
            tail = 0
        else:
            rm_wide = conf.product_wide / 100
            sum_fp_wide = sum([c.product_wide * c.product_no_corte for c in product_cortes_ids]) / 100
            tail = round(rm_wide - sum_fp_wide, 3)
        return tail

    def get_factor(self, indx, flag, product_id=False, product_wide=False, product_flag=False): #   product_flag: 1.Producto, 2.Sobrante Rollo, 3.Sobrante Hoja    
        if LOG == 1: _logger.info('******* 6')
        price_factor_fp = factor_share = weight_rm = weight_fp = 0
        corte, conf, cut_no = self, self.wizard_id, self.product_no_corte if not product_wide else 1
        if not cut_no:
            raise ValidationError(u'Falta introducir el número de cortes en la definición de cortes de uno de los productos.')

        rm_wide = conf.product_wide                                                 #/ 100           
        fp_wide = (product_wide or corte.product_wide)                              #/ 100
        pt_lenght = corte.product_long                                              #/ 100
        product_cortes_ids = conf.product_cortes_ids
        last = product_cortes_ids[-1]
        last_wide = last.product_tail
        sum_fp_wide = sum([c.product_wide * c.product_no_corte for c in product_cortes_ids])    

        if product_flag != 2:                                                       #corte.product_subproduct != 'scrap' and #if product_cortes_ids[-1].product_subproduct in ('product', 'subproduct'):
            factor_share = (fp_wide * cut_no) / (rm_wide)                           # 
        factor_tail = last_wide/ rm_wide
        
        factor_price = 1
        price_factor_fp = (fp_wide * cut_no) / (rm_wide - last_wide)
        if last.product_subproduct == 'product':
            price_factor_fp = (fp_wide * cut_no) / rm_wide
        if last.product_subproduct in ('product', 'subproduct'):
            factor_fp = (fp_wide * cut_no) / (rm_wide - last_wide)
            if product_wide:                                                        # factores de un subproducto no de un corte
                factor_fp = fp_wide / rm_wide
        else:
            factor_fp = (fp_wide * cut_no) / rm_wide
            factor_price = rm_wide / sum_fp_wide
        
        price_unit = self._get_price_unit(flag, product_id)

        if conf.product_id.product_cosal == 'rollo':                                # MP
            if pt_lenght and corte.product_quantity_uom == "millares":              # PT
                weight_rm, weight_fp = self.get_weight(product_wide=False)                
                if rm_wide == fp_wide:                                              # TODO calcular factor_fp de todos los casos de millares
                    factor_fp = corte.product_long / sum([c.product_long for c in product_cortes_ids])
                    factor_price = 1
                else:
                    pass
                corte.product_weight = weight_fp
                corte.product_rm_weight = factor_price * weight_fp
                self.validate_qty(factor_price, weight_fp)

                price_unit = self._get_price_unit(flag, product_id) # Price / Kg

        factor_weight = (fp_wide * corte.product_no_corte / rm_wide)
        #_logger.info('***** get_factor: %s %s %s'%(factor_fp, product_cortes_ids[0].product_no_corte, factor_weight))
        return {
            'product_price': price_unit,
            'product_price_factor': factor_price,
            'product_price_new': price_unit * factor_price,
            'product_price_factor_fp': price_factor_fp,     # Factor de cantidad de producto en la línea de la SO, la suma de todas las líneas debe ser 100%
            'product_factor_share': factor_share,
            'product_factor_tail': factor_tail,
            'product_factor_weight': factor_weight #1 / fp_wide * product_cortes_ids[0].product_no_corte,
        }

    def get_factor_new(self, indx, flag, product_id=False, product_wide=False, product_flag=False): #   product_flag: 1.Producto, 2.Sobrante Rollo, 3.Sobrante Hoja    
        if LOG == 1: _logger.info('******* 6')
        price_factor_fp = factor_share = weight_rm = weight_fp = 0
        corte, conf, cut_no = self, self.wizard_id, self.product_no_corte
        if not cut_no:
            raise ValidationError(u'Falta introducir el número de cortes en la definición de cortes de uno de los productos.')
        rm_wide = conf.product_wide                                                 #/ 100           
        fp_wide = (product_wide or corte.product_wide)                              #/ 100
        pt_lenght = corte.product_long                                              #/ 100
        product_cortes_ids = conf.product_cortes_ids
        last = product_cortes_ids[-1]
        last_wide = last.product_tail
        sum_fp_wide = sum([c.product_wide * cut_no for c in product_cortes_ids])    #/ 100
        if product_flag != 2:                                                       #corte.product_subproduct != 'scrap' and #if product_cortes_ids[-1].product_subproduct in ('product', 'subproduct'):
            factor_share = (fp_wide * cut_no) / (rm_wide)                           # 
        factor_price = rm_wide / sum_fp_wide + last_wide
        factor_tail = last_wide/ rm_wide
        
        price_factor_fp = (fp_wide * cut_no) / (rm_wide - last_wide)
        if last.product_subproduct in ('product', 'subproduct'):
            factor_fp = price_factor_fp
            if product_wide:                                                        # factores de un subproducto no de un corte
                factor_fp = fp_wide / rm_wide
        else:
            factor_fp = (fp_wide * cut_no) / rm_wide
        
        price_unit = self._get_price_unit(flag, product_id)
        price_new = price_unit / factor_fp
        if product_wide: 
            price_new = corte.product_price_new

        if conf.product_id.product_cosal == 'rollo':                                # MP
            if pt_lenght and corte.product_quantity_uom == "millares":              # PT
                weight_rm, weight_fp = self.get_weight(product_wide=False)                
                if rm_wide == fp_wide:                                              # TODO calcular factor_fp de todos los casos de millares
                    factor_fp = corte.product_long / sum([c.product_long for c in product_cortes_ids])
                    factor_price = 1
                else:
                    pass
                corte.product_weight = weight_fp
                corte.product_rm_weight = factor_price * weight_fp
                self.validate_qty(factor_price, weight_fp)

                price_unit = self._get_price_unit(flag, product_id) # Price / Kg
                price_new = price_unit * factor_price

        factor_weight = (factor_tail * product_cortes_ids[0].product_no_corte) / (sum_fp_wide / rm_wide) # sobrante por número de cortes del primer corte / factor de producto terminado
        return {
            'product_price': price_unit,
            'product_price_factor': factor_price,
            'product_price_new': price_new, #price_unit * factor_price,
            'product_price_factor_fp': price_factor_fp, #factor_fp,
            'product_factor_share': factor_share,
            'product_factor_tail': factor_tail,
            'product_factor_weight': 1 / product_cortes_ids[0].product_wide * product_cortes_ids[0].product_no_corte,
        }

    def get_weight(self, product_wide=False ):
        if LOG == 1: _logger.info('******* 6.1')
        corte, conf, cut_no = self, self.wizard_id, self.product_no_corte
        rm_wide = conf.product_wide / 100
        fp_wide = (product_wide or corte.product_wide) / 100
        pt_lenght = corte.product_long / 100
        grams = int(conf.product_id.product_template_attribute_value_ids.filtered(lambda l: l.attribute_id.name=='Gramos').name)
        weight_rm =  rm_wide * pt_lenght * grams 
        weight_fp =  fp_wide * pt_lenght * grams
        return weight_rm, weight_fp

    def validate_qty(self, factor_price, weight):
        if LOG == 1: _logger.info('******* 6.2')
        corte, conf = self, self.wizard_id
        kg_needed = factor_price * weight * corte.product_quantity
        if kg_needed > conf.available_quantity:
            diff = (kg_needed - conf.wizard_id.product_sum_qty)
            """ VALIDATION """
            params = (corte.product_quantity, '{:,.2f}'.format(kg_needed), conf.product_id.name, '{:,.2f}'.format(conf.wizard_id.product_sum_qty), '{:,.2f}'.format(diff))
            msg = u"Seleccionaste %s (Millares) de producto terminado que representa %s kg de %s y en esta selección solo hay %s Kg, "
            msg += "te falta seleccionar %s Kg mas."
            raise ValidationError(msg%params)

    def write_factor(self, factors):
        if LOG == 1: _logger.info('******* 6.3')
        self.write(factors)
        
    def _get_price_unit(self, flag, product_id=False):
        if LOG == 1: _logger.info('******* 6.4')
        price_unit = 0
        order_id = self.wizard_id.wizard_id.order_id 
        if flag == 'corte':                     # < _onchange_parameters en configuración de cortes
            price_unit = self.product_price 
        else:                                   # < _process_product_id en creación de líneas de SO
            price_unit = order_id.pricelist_id._get_product_price(product=product_id, quantity=1.0, currency=order_id.currency_id, date=order_id.date_order) # , **kwargs
            if not price_unit and product_id:
                for price_matrix_id in self.env['product.price.matrix'].search([('price_list_id','=',order_id.pricelist_id.id)]):
                    product_id.create_matrix_line(price_matrix_id.id)
            price_unit = order_id.pricelist_id._get_product_price(product=product_id, quantity=1.0, currency=order_id.currency_id, date=order_id.date_order) # , **kwargs
            if not price_unit:
                price_unit = 0  # TODO volver a activar RAISE
                #params = (product_id.display_name, product_id.id, product_id.mapped('additional_product_tag_ids.name'), order_id.pricelist_id.display_name)
                #raise ValidationError(u'El producto: %s [ID: %s, TAG: %s] no tiene asignado precio en la lista: %s'%params)
        return price_unit

    #=== ACTIONS METHODS ===#

    #=== CONSTRAINT METHODS ===#
    @api.constrains('product_template_id', 'product_price_total')
    def _check_product_template_id(self):
        if LOG == 1: _logger.info('******* 7')
        for corte in self:
            if not corte.product_template_id:
                raise ValidationError("Favor de seleccionar la plantilla del producto")
            #elif float_is_zero(corte.product_price, 2):
            #    raise ValidationError("Favor de configurar el precio del producto en el configurador del la SO: %s"%corte.wizard_id.wizard_id.order_id.name)

    @api.constrains('product_long')
    def _check_product_long(self):
        if LOG == 1: _logger.info('******* 8.0')
        for corte in self:
            if (corte.product_cosal == 'hoja') and not corte.product_long:
                raise ValidationError(_(u"El largo es requerido en productos de tipo hoja."))

    @api.constrains('product_wide','product_quantity')
    def _check_product_quantity(self):
        if LOG == 1: _logger.info('******* 8.1')
        for corte in self:
            if not corte.product_quantity:
                raise ValidationError(u'Se requiere establecer Cantidad de producto terminado.')
            elif not corte.product_wide:
                raise ValidationError(u'Se requiere establecer el Ancho del corte.')

class SaleProductConfigurationCombination(models.Model):
    _name = 'sale.product.configuration.combination'
    _description = _('Sale Product Configuration')
    _order = 'sequence, id'

    name = fields.Char(_('Name'))
    product_cosal = fields.Selection(selection=[
        ('', ''),
        ('rollo', 'Rollo'),
        ('hoja', 'Hoja')
    ], string ="Tipo de Producto", default="")

    sequence = fields.Integer('Sequence', default=1)
    selected = fields.Boolean(string ="Activar", default=False)

    is_warehouse = fields.Boolean(default=False)
    warehouse_name = fields.Char("Nombre Almacen")
    warehouse_id = fields.Many2one('stock.warehouse', string ='Almacen')
    product_id = fields.Many2one('product.product', string ='Producto')
    product_uom_id = fields.Many2one('uom.uom', string ='Unidad')
    product_qty = fields.Float(
        string ="Cantidad",
        digits='Product Unit of Measure',
        default=1.0)

    product_family = fields.Char(string ="Familia")
    product_subfamily = fields.Char(string ="Subfamilia")
    product_type = fields.Char(string ="Tipo")
    product_color = fields.Char(string ="Color")
    product_grams = fields.Char(string ="Gramos")
    product_certificate = fields.Char(string ="Certificado")

    product_wide = fields.Float(string ="Ancho")
    product_long = fields.Float(string ="Largo")
    product_centro = fields.Float(string ="Centro")
    product_diametro = fields.Float(string ="Diametro")
    product_millares = fields.Float(string ="Millar(es)")
    available_quantity = fields.Float(string ='Inventario KG')

    requiere_corte = fields.Boolean(string ="Requiere Ajustes")
    product_cortes_ids = fields.One2many(
        comodel_name ='sale.product.configuration.cortes',
        inverse_name='wizard_id',
        string ="Cortes",
        copy=True, auto_join=True)

    wizard_id = fields.Many2one(comodel_name ='sale.product.configuration', string ='Configuration', ondelete='cascade')

    product_wide_sum = fields.Float(string ="SUM Ancho", compute='_compute_sum_product_ancho_largo')
    product_long_sum = fields.Float(string ="SUM Largo", compute='_compute_sum_product_ancho_largo')

    #=== COMPUTE METHODS ===#
    @api.depends('requiere_corte', 'product_cortes_ids.product_wide', 'product_cortes_ids.product_long')
    def _compute_sum_product_ancho_largo(self):
        if LOG == 1: _logger.info('******* 9')
        for comb in self:
            ctx = dict(comb.env.context)
            ctx["wiz_conf_id"] = comb.id
            comb.env.context = ctx            
            ancho = sum(comb.product_cortes_ids.mapped('product_wide')) if comb.requiere_corte else 0.0
            largo = sum(comb.product_cortes_ids.mapped('product_long')) if comb.requiere_corte else 0.0
            comb.product_wide_sum = ancho
            comb.product_long_sum = largo
        return True
    #=== CRUD METHODS ===#

class SaleProductConfiguration(models.Model):
    _name = 'sale.product.configuration'
    _description = _('Sale Product Configuration')

    name = fields.Char(_('Name'))
    state = fields.Selection([
        ('01', 'Configurador'),
        ('02', 'Componentes'),
    ], string ="Estado", default="01", index=True)

    # ==== Informacion de la Venta ====
    order_id = fields.Many2one('sale.order', 'Orden de Venta', ondelete='cascade')
    warehouse_id = fields.Many2one(
        'stock.warehouse', 
        'Almacen')
    order_state = fields.Char('State')

    # ==== Filtro de Almacen ====
    products_warehouse_ids = fields.Many2many(
        'stock.warehouse', 
        string ='Warehouse')

    # ==== Filtro de Cantidades ====
    product_quantity = fields.Float(
        string ="Cantidad",
        digits='Product Unit of Measure',
        default=1.0)
    product_quantity_uom = fields.Selection([
        ('kg', 'Kilos'),
        ('millares', 'Millares')
    ], string ="Cantidad UdM", default="kg")

    # ==== Configurador de Componente y Lista de Material ====
    product_family = fields.Many2one(
        comodel_name ='product.attribute.value',
        string ="Familia",
        change_default =True,
        domain ="[('attribute_id.attribute_cosal', '=', 'familia')]")
    product_subfamily = fields.Many2one(
        comodel_name ='product.attribute.value',
        string ="Subfamilia",
        change_default =True,
        domain ="[('attribute_id.attribute_cosal', '=', 'subfamilia'), ('parent_ids','in',product_family)]") 
    product_type = fields.Many2one(
        comodel_name ='product.attribute.value',
        string ="Tipo",
        change_default =True,
        domain ="[('attribute_id.attribute_cosal', '=', 'tipo'), ('parent_ids','in',product_subfamily)]")
    product_color = fields.Many2one(
        comodel_name ='product.attribute.value',
        string ="Color",
        change_default =True,
        domain ="[('attribute_id.attribute_cosal', '=', 'color'), ('parent_ids','in',product_subfamily)]")
    product_grams = fields.Many2one(
        comodel_name ='product.attribute.value',
        string ="Gramos",
        change_default =True,
        domain ="[('attribute_id.attribute_cosal', '=', 'gramos'), ('parent_ids','in',product_type)]")
    product_wide = fields.Many2one(
        comodel_name ='product.attribute.value',
        string ="Anchos",
        change_default =True,
        domain ="[('attribute_id.attribute_cosal', '=', 'ancho')]")
    product_long = fields.Many2one(
        comodel_name ='product.attribute.value',
        string ="Largos",
        change_default =True,
        domain ="[('attribute_id.attribute_cosal', '=', 'largo')]")
    product_centro = fields.Many2one(
        comodel_name ='product.attribute.value',
        string ="Centros",
        change_default =True,
        domain ="[('attribute_id.attribute_cosal', '=', 'centro')]")
    product_diametro = fields.Many2one(
        comodel_name ='product.attribute.value',
        string ="Diametros",
        change_default =True,
        domain ="[('attribute_id.attribute_cosal', '=', 'diametro')]")
    product_certificate = fields.Many2one(
        comodel_name ='product.attribute.value',
        string ="Certificado",
        change_default =True,
        domain ="[('attribute_id.attribute_cosal', '=', 'certificado')]")
    product_wide_qty = fields.Float('Ancho')
    product_long_qty = fields.Float('Largo')
    product_center_qty = fields.Float('Centro')
    product_diameter_qty = fields.Float('Diametro')
    #use_structure = fields.Boolean(string ="Usar Estructura", default=True)

    # ==== Informacion de los componentes ====
    product_component_ids = fields.One2many(
        comodel_name ='sale.product.configuration.combination',
        inverse_name='wizard_id',
        string ="Componentes",
        copy=True, auto_join=True)

    product_sum_qty = fields.Float(string ="SUM Inventario", compute='_compute_sum_product_qty_millar', store=True)
    product_sum_millar = fields.Float(string ="SUM Millar(es)", compute='_compute_sum_product_qty_millar', store=True)

    #=== COMPUTE METHODS ===#
    @api.depends('product_component_ids.selected')
    def _compute_sum_product_qty_millar(self):
        if LOG == 1: _logger.info('******* 10')
        for rec in self:
            product_sum_qty, product_sum_millar = 0.0, 0.0
            for line in rec.product_component_ids:
                if line.selected:
                    product_sum_qty = product_sum_qty + line.available_quantity
                    product_sum_millar = product_sum_millar + line.product_millares
            rec.product_sum_qty = product_sum_qty or 0.0
            rec.product_sum_millar = product_sum_millar or 0.0

    #=== BASE METHODS ===#
    @api.model
    def default_get(self, fields):
        if LOG == 1: _logger.info('******* 11')
        ctx = dict(self.env.context)
        res = super(SaleProductConfiguration, self).default_get(fields)
        if self.env.context.get('order_id'):
            sale_id = self.env['sale.order'].browse(self.env.context['order_id'])
            res['order_id'] = sale_id.id
            res['warehouse_id'] = sale_id.warehouse_id.id
            res['order_state'] = sale_id.state or 'draft'
            ctx["warehouse"] = sale_id.warehouse_id.id
            ctx["default_warehouse_id"] = sale_id.warehouse_id.id
            ctx["default_warehouse"] = sale_id.warehouse_id.id
        self.env.context = ctx
        return res


    #=== ONCHANGE METHODS ===#
    #==== ACTION METHODS ====#
    def action_search_components(self):
        if LOG == 1: _logger.info('******* 12')
        ctx = dict(self.env.context)
        ctx["configuration_id"] = self.id
        self.env.context = ctx

        if self.state == "01":
            self.write({
                'state': '02',
                'product_component_ids': [Command.clear()]
            })
            self.get_domain_search_components_filters()
            return {
                'name': _('Configurador de Productos'),
                'view_mode': 'form',
                'res_model': 'sale.product.configuration',
                'res_id': self.id,
                'view_id': self.env.ref('bias_custom_cosal.view_sale_component_configuration_form').id,
                'type': 'ir.actions.act_window',
                'context': ctx,
                'target': 'new'
            }
        elif self.state == "02":
            self.write({'state': '01'})
            return {
                'name': _('Configurador de Productos'),
                'view_mode': 'form',
                'res_model': 'sale.product.configuration',
                'res_id': self.id,
                'view_id': self.env.ref('bias_custom_cosal.view_sale_filter_configuration_form').id,
                'type': 'ir.actions.act_window',
                'context': ctx,
                'target': 'new'
            }

    def action_create_sale_line(self):
        if LOG == 1: _logger.info('******* 13')
        bom_id = self.env['mrp.bom']
        no_certificate = self.env['product.attribute.value'].search([('attribute_id.attribute_cosal', '=', 'certificado'), ('name','=','-')])
        comp_ids = self.product_component_ids.filtered(lambda p: p.selected == True)
        if not comp_ids:
            raise ValidationError("Por favor seleccione un producto")
        cortes_ids = self.mapped('product_component_ids.product_cortes_ids')
        if not cortes_ids:
            raise ValidationError("Por favor configure los cortes del producto seleccionado")
        self.order_id.order_line.unlink()
        for comp in comp_ids:
            cortes_ordered = comp.product_cortes_ids.sorted(
                    key=lambda x: (x.product_no_corte or 0), 
                    reverse=True
                )
            top_product_no_corte = 0
            for corte in cortes_ordered:
                if corte.product_no_corte > top_product_no_corte:
                    top_product_no_corte = corte.product_no_corte

            if comp.product_cortes_ids[0].product_no_corte < top_product_no_corte:
                raise UserError("El producto con mayor no. de cortes debe ser el producto principal y la linea inicial del configurador.")
            for indx, corte in enumerate(comp.product_cortes_ids):
                is_last = (indx+1) == len(comp.product_cortes_ids)
                product_tail = round(corte.product_tail,2)
                n_cuts = corte.product_no_corte
                rm_wide, fp_wide, pt_lenght, cut_no = comp.product_wide / 100, corte.product_wide / 100, corte.product_long / 100, corte.product_no_corte
                product_id, factors = self._process_product_id(indx, comp, corte, product_wide=False, product_flag=1)
                #raise UserError('TEST: %s'%( factors ) )
                if corte.product_cosal == 'rollo': 
                    # CREA UNA LÍNEA EN LA SO POR CADA CORTE
                    if indx == 0:
                        bom_id = self.create_bom_id(comp, corte, product_id, indx, product_id)
                    else:
                        subproduct_id = product_id

                    # CREA LA LÍNEA EN LA SO
                    _logger.info('********** action_create_sale_line: %s %s'%(indx, corte.product_subproduct))
                    if True: #corte.product_subproduct == 'product':
                        self._process_order_line(indx, comp, corte, product_id, bom_id, {}, n_cuts, log=1)

                    # SI ES EL ÚLTIMO CORTE REVISA SI EL SOBRANTE ESTA CONFIGURADO PARA ENTREGAR AL CLIENTE CREA LA LÍNEA EN LA SO
                    if is_last and bool(product_tail):
                        if corte.product_subproduct == 'product':
                            product_id, factors = self._process_product_id(indx, comp, corte, product_wide=product_tail, product_flag=2)
                            self._process_order_line(indx, comp, corte, product_id, bom_id, factors, n_cuts, log=2)
                    # CREA LOS SUBRODUCTOS EN EL BOM PARA ROLLO
                    if len(comp.product_cortes_ids) == 1 and product_tail and corte.product_subproduct != 'scrap' and product_tail != corte.product_wide:
                        self._create_byproducts(indx, comp, corte, bom_id, product_id)
                    elif indx > 0 and product_tail: 
                        self._create_byproducts(indx, comp, corte, bom_id, product_id, subproduct_id)
                elif corte.product_cosal == 'hoja':
                    if rm_wide == fp_wide:
                        bom_id = self.create_bom_id(comp, corte, product_id, indx, product_id)
                    elif indx == 0:
                        bom_id = self.create_bom_id(comp, corte, product_id, indx, product_id)
                    else:
                        subproduct_id = product_id
                    self._process_order_line(indx, comp, corte, product_id, bom_id, {}, n_cuts, log=3)

                    # SI ES EL ÚLTIMO CORTE REVISA SI ESTA CONFIGURADO PARA ENTREGAR EL SOBRANTE AL CLIENTE
                    if is_last:    
                        product_id, factors = self._process_product_id(indx, comp, corte, product_wide=product_tail, product_flag=3)
                        if corte.product_subproduct == 'product':
                            self._process_order_line(indx, comp, corte, product_id, bom_id, factors, n_cuts, log=4)

                    # CREA LOS SUBRODUCTOS EN EL BOM PARA HOJA
                    if len(comp.product_cortes_ids) == 1 and product_tail and corte.product_subproduct != 'scrap' and product_tail != corte.product_wide:
                        self._create_byproducts(indx, comp, corte, bom_id, product_id)
                    elif indx > 0 and product_tail: 
                        self._create_byproducts(indx, comp, corte, bom_id, product_id, subproduct_id)

    def _process_order_line(self, indx, comp, corte, product_id, bom_id, factors={}, n_cuts=0, log=''):
        if LOG == 1: _logger.info('******* 13.1 - %s'%log)
        #_logger.info('********** _process_order_line: %s %s'%(indx, corte.product_subproduct))
        line_vals = self.get_line_vals(indx, comp, corte, product_id, bom_id, factors)
        if n_cuts:
            line_vals['n_cuts'] = n_cuts
        order_line = self.order_id.order_line.filtered(lambda l: l.wiz_corte_id == corte and l.product_id == product_id)
        if factors and order_line and corte.product_tail == corte.product_wide:                                             # SUMA EL SOBRANTE A LA CANTIDAD DE LA LÍNEA DE SO PORQUE SON DEL MISMO ANCHO
            line_vals.update({'product_uom_qty': order_line.product_uom_qty + line_vals['product_uom_qty']})
        if order_line:
            order_line.write(line_vals)
        else:
            self.order_id.write({'order_line': [(0, None, line_vals)]})

    def _process_product_id(self, indx, comp, corte, product_wide=False, product_flag=False):
        if LOG == 1: _logger.info('******* 13.2')
        combination = self.get_combination_from_template(comp, corte, product_wide=product_wide)
                     
        product_id = corte.product_template_id._create_product_variant(combination, log_warning=True) # TODO correr defaults para agregar cuentas contables y código SAT
        product_id.weight = 1 if corte.product_cosal == 'rollo' else corte.product_weight/1000
        tag = self.env['product.tag'].search([('name','=','Medida Especial')])
        unspsc_code_id = self.env.ref('product_unspsc.unspsc_code_14111500')
        vals = {
            'unspsc_code_id':unspsc_code_id.id,
            'l10n_mx_edi_hazardous_material_code':0,
        }
        if tag and not tag in product_id.additional_product_tag_ids:
            vals.update({'additional_product_tag_ids':[Command.link(tag.id)]})
        product_id.write(vals)
        factors = corte.get_factor(indx, flag='line', product_id=product_id, product_wide=product_wide, product_flag=product_flag)
        if not product_wide:
            corte.write_factor(factors)
        #raise UserError('Factors: %s'%factors)
        return product_id, factors

    def _create_byproducts(self, indx, comp, corte, bom_id, product_id, subproduct_id=False):
        if LOG == 1: _logger.info('******* 13.3')
        org_product_id = product_id
        len_comp = len(comp.product_cortes_ids)
        
        # CREATE BYPRODUCT BY LINE
        if len_comp > 1 and indx > 0 and subproduct_id:
            byproduct_vals = self.get_byproduct_vals(indx, corte, subproduct_id)                           
            byproduct_line_id = bom_id.byproduct_ids.filtered(lambda l: l.sequence == indx and l.product_id == subproduct_id)
            if byproduct_line_id:
                byproduct_line_id.update(byproduct_vals)
            else:
                bom_id.update({'byproduct_ids': [Command.create(byproduct_vals)]})

        # CREATE BYPRODUCT BY TAIL        #if 'scrap' not in comp.product_cortes_ids[-1].product_subproduct:
        if (indx+1) == len_comp and corte.product_subproduct != 'scrap' :
            product_id, factors = self._process_product_id(indx, comp, corte, product_wide=corte.product_tail, product_flag=4)  # Crea o trae el subproducto 
            byproduct_vals = self.get_byproduct_vals(indx, corte, product_id, factors=factors)                                  # Genera los valores de la línea de subproductos del bom
            byproduct_line_id = bom_id.byproduct_ids.filtered(lambda l: l.product_id == product_id)                             # Busca si ya existe una línea de subproductos con este producto
            if byproduct_line_id:
                byproduct_vals.update({'product_qty':byproduct_line_id.product_qty + byproduct_vals['product_qty']})            # 
                byproduct_line_id.update(byproduct_vals)                                                                        # Actualiza la línea de subproductos del bom
            else:
                bom_id.update({'byproduct_ids': [Command.create(byproduct_vals)]})                                              # Crea la línea de subproductos del bom

    def create_bom_id(self, comp, corte, product_id, indx, bom_product_id):
        if LOG == 1: _logger.info('******* 13.4')
        # OBTENER VALORES DE LA LÍNEA DEL BOOM
        values_bom_line = self.get_values_bom_line(indx, comp, corte)
        
        # CREAR/ACTUALIZAR BOM
        vals = self.get_bom_vals(corte, product_id, bom_product_id)
        bom_id = self.order_id.mapped('order_line.bom_id').filtered(lambda b: b.product_id == bom_product_id)   #bom_id = self.order_id.order_line[0].bom_id if self.order_id.order_line else False
        if not bom_id:
            bom_id = product_id.bom_ids.filtered(lambda b: \
                b.product_qty == 1 and \
                comp.product_id in b.mapped('bom_line_ids.product_id') and \
                bom_product_id == b.product_id and \
                self.order_id == b.order_id)

        if bom_id:  # WRITE BOM
            bom_line_id = bom_id.bom_line_ids.filtered(lambda l: comp.product_id == l.product_id )
            if bom_line_id:
                bom_line_id.write(values_bom_line)
            bom_id.write(vals)
        else:       # CREATE BOM
            vals.update({'bom_line_ids': [Command.create(values_bom_line)]})
            bom_id = self.env['mrp.bom'].create(vals)
        return bom_id
    
    def get_line_vals(self, indx, comp, corte, product_id, bom_id, factors={}):
        # RETURN SALE ORDER LINE VALS
        if LOG == 1: _logger.info('******* 14')
        last = comp.product_cortes_ids[-1]
        factor_fp = factors.get('product_price_factor_fp') or corte.product_price_factor_fp
        product_uom_qty = corte.product_quantity * factor_fp
        #_logger.info('***** get_line_vals: %s : %s : %s'%(product_uom_qty, corte.product_quantity, factor_fp))
        product_uom = product_id.uom_id.id
        price_unit = corte.product_price_total
        if factors:
            price_unit = corte._get_price_unit(False, product_id)
        if product_id.product_cosal == 'hoja':
            unit_categ_id = self.env.ref('uom.product_uom_categ_unit').id
            uom_1000 = self.env['uom.uom'].search([('category_id','=',unit_categ_id), ('factor','=',1/1000), ('uom_type','=','bigger'), ('active','=',True)], limit=1)
            product_uom = uom_1000
            #if product_uom != uom_1000:
            #    product_uom_qty = uom_1000._compute_quantity(qty=product_uom_qty, to_unit=product_id.uom_id, round=True, rounding_method='UP', raise_if_failure=True)
            price_unit = price_unit * product_uom.factor_inv
            product_uom = product_uom.id

        line_vals = {
            'order_id': self.order_id.id,
            'product_id': product_id.id,                    
            'product_template_id': product_id.product_tmpl_id.id,
            'is_configurable_product': True,
            'price_unit': price_unit, # corte.product_price_total,                                                 
            "product_uom_qty": product_uom_qty,
            "product_uom": product_uom,
            "wiz_component_id": self.id,
            "wiz_corte_id": corte.id,
            'mrp_notes': corte.product_comment,
            'route_id': self.env.ref('mrp.route_warehouse0_manufacture').id,
            'mrp_location_src_id': comp.warehouse_id.lot_stock_id.id,          # TODO revisar si quitando esto toma las rutas configuradas
            'sequence': indx + 1, 
            'bom_id': bom_id.id,
            #'mrp_location_src_id': self.order_id.warehouse_id.lot_stock_id.id,
        }
        
        return line_vals
        
    def get_bom_vals(self, corte, product_id, bom_product_id):
        if LOG == 1: _logger.info('******* 14.1')
        uom_id = product_id.uom_id
        if product_id.product_cosal == 'hoja':
            uom_id = self.env['uom.uom'].search([('category_id','=',1), ('factor','=',0.001), ('uom_type','=','bigger')])   # GET UOM Millar
            product_qty = 1 # corte.product_no_corte
        elif product_id.product_cosal == 'rollo':
            #cortes_ids = corte.wizard_id.product_cortes_ids #.filtered(lambda c: c.product_wide == corte.product_wide)
            #product_qty = corte.product_factor_weight * corte.product_wide * len(cortes_ids)
            product_qty = 1 
            if corte.product_tail == corte.product_wide and corte.product_subproduct == 'product':
                product_qty += 1                                                                    
            elif corte.product_tail == corte.product_wide and corte.product_subproduct == 'subproduct':
                product_qty += 1                                                                    
            elif corte.product_tail == corte.product_wide and corte.product_subproduct == 'scrap':
                product_qty += 0
        vals = {
            'product_id': bom_product_id.id,
            'product_tmpl_id': bom_product_id.product_tmpl_id.id,
            'product_uom_id': uom_id.id,
            'product_qty': product_qty,                                       
            'type': 'normal',
            'order_id': self.order_id.id,
            'byproduct_ids': False,
        }
        return vals

    def get_byproduct_vals(self, indx, corte, product_id, factors={}, product_factor_share=0, cost_share=0, product_wide=0): # byproduct: 40185 $3.25
        if LOG == 1: _logger.info('******* 16')
        comp = corte.wizard_id
        if factors:
            product_factor_share = corte.product_factor_tail
            cost_share = corte.product_factor_tail
            product_wide = corte.product_tail
        factor_weight = factors.get('product_factor_weight') or corte.product_factor_weight
        product_wide = product_wide or corte.product_wide * corte.product_no_corte                              # SUBPRODUCT_WIDE OR TAIL
        CORTE_0 = comp.product_cortes_ids[0]
        FACTOR_MP = 1 / (CORTE_0.product_wide * CORTE_0.product_no_corte / comp.product_wide)                   # 1 / (WIDE_PT_0 * CORTES_PT_0 / ROLLO_MP)
        product_qty = FACTOR_MP * (product_wide / comp.product_wide)                                            # FACTOR_MP * (PRODUCT_WIDE / ROLLO_MP)
        _logger.info('***** get_byproduct_vals: : %s : %s : %s '%(product_qty, FACTOR_MP, product_wide ))

        cost_share = cost_share or corte.product_factor_share
        product_factor_share = product_factor_share  or corte.product_factor_share
        product_uom = product_id.uom_id
        unit_categ_id = self.env.ref('uom.product_uom_categ_unit')

        if product_id.product_cosal == 'hoja':
            product_qty = factor_weight * product_wide  # Kg of raw material for 1 kg of finish product... 
            domain = [('category_id','=',unit_categ_id.id), ('factor','=',1/1000), ('uom_type','=','bigger'), ('active','=',True)]
            uom_1000 = self.env['uom.uom'].search(domain, limit=1)   # GET UOM Millar
            if product_id.uom_id.category_id == unit_categ_id:  # If is unit category #if corte.wizard_id.product_id.uom_id.category_id == unit_categ_id: 
                if corte.product_no_corte == 1:
                    product_uom = uom_1000
                    product_qty = 1
            else:
                raise ValidationError('Método de calculo de subproducto no implementado')
            #else:
            #    product_qty = uom_1000._compute_quantity(qty=product_qty, to_unit=product_id.uom_id, round=True, rounding_method='UP', raise_if_failure=True)
        return {
            "company_id": self.env.company.id,
            "product_uom_category_id": product_id.uom_id.category_id.id,
            "sequence": indx + (1 if factors else 0),
            "product_id": product_id.id,
            "product_qty": product_qty, 
            "product_uom_id": product_uom.id, # product_id.uom_id.id,
            "cost_share": cost_share,
        }
    
    def get_values_bom_line(self, indx, comp, corte):
        if LOG == 1: _logger.info('******* 14.2')
        CORTE_0 = comp.product_cortes_ids[0]  
        product_qty = 1 / (CORTE_0.product_wide * CORTE_0.product_no_corte / comp.product_wide)                 # 1 / (WIDE_PT_0 * CORTES_PT_0 / ROLLO_MP)
        uom_id = comp.product_id.uom_id
        unit_categ_id = self.env.ref('uom.product_uom_categ_unit')                                              # Categoría UOM: UNIDAD
        if comp.product_id.uom_id.category_id == unit_categ_id:                                                 # Si tiene categoría UOM: UNIDAD    # 
            uom_id = self.env['uom.uom'].search([('category_id','=',1), ('factor','=',0.001), ('uom_type','=','bigger')])  # GET UOM Millar
            product_qty = 1                                                                                     # corte.product_rm_weight  
        elif corte.product_quantity_uom != 'kg':
            product_qty = corte.product_rm_weight                                                               # Kg de MP por un millar de PT...
        values_bom_line = {
            'product_id': comp.product_id.id,
            'product_tmpl_id': comp.product_id.product_tmpl_id.id,
            'product_uom_id': uom_id.id,
            'product_qty': product_qty,
            'sequence': indx + 1,
        }
        return values_bom_line

    def get_combination_from_template(self, comp, corte, product_wide=False):
        if LOG == 1: _logger.info('******* 17')
        centro_id = self.env["product.template.attribute.value"]
        diametro_id = self.env["product.template.attribute.value"]
        attribute_line_ids = corte.product_template_id.valid_product_template_attribute_line_ids
        combination = self.env["product.template.attribute.value"].browse()      
        for line in attribute_line_ids.filtered(lambda l: l.attribute_id.attribute_cosal=='familia'):
            combination |= line.product_template_value_ids.filtered(lambda v: v.name == comp.product_family)
        for line in attribute_line_ids.filtered(lambda l: l.attribute_id.attribute_cosal=='subfamilia'):
            combination |= line.product_template_value_ids.filtered(lambda v: v.name == comp.product_subfamily)
        for line in attribute_line_ids.filtered(lambda l: l.attribute_id.attribute_cosal=='tipo'):
            combination |= line.product_template_value_ids.filtered(lambda v: v.name == comp.product_type)
        for line in attribute_line_ids.filtered(lambda l: l.attribute_id.attribute_cosal=='color'):
            combination |= line.product_template_value_ids.filtered(lambda v: v.name == comp.product_color)
        for line in attribute_line_ids.filtered(lambda l: l.attribute_id.attribute_cosal=='gramos'):
            combination |= line.product_template_value_ids.filtered(lambda v: v.name == comp.product_grams)
        for line in attribute_line_ids.filtered(lambda l: l.attribute_id.attribute_cosal=='certificado'):
            combination |= line.product_template_value_ids.filtered(lambda v: v.name == comp.product_certificate)
        for line in attribute_line_ids.filtered(lambda l: l.attribute_id.attribute_cosal=='centro'):
            product_centro = str(comp.product_centro).split('.')
            centros = [str(comp.product_centro)]
            if len(product_centro) == 2 and product_centro[1] == '0':
                centros += [product_centro[0]]
            centro_id = line.product_template_value_ids.filtered(lambda v: v.name in centros)
        for line in attribute_line_ids.filtered(lambda l: l.attribute_id.attribute_cosal=='diametro'):
            product_diametro = str(comp.product_diametro).split('.')
            diametros = [str(comp.product_diametro)]
            if len(product_diametro) == 2 and product_diametro[1] == '0':
                diametros += [product_diametro[0]]
            diametro_id = line.product_template_value_ids.filtered(lambda v: v.name in diametros)

        product_wide = product_wide or corte.product_wide
        att_ancho = self.get_value_att_val("ancho", product_wide, corte.product_template_id)    # > 19
        combination |= att_ancho
        if corte.product_template_id.product_cosal == 'hoja':
            att_largo = self.get_value_att_val("largo", corte.product_long, corte.product_template_id)
            combination |= att_largo
        if corte.product_template_id.product_cosal == 'rollo':
            combination |= corte.product_centro
            combination |= corte.product_diametro
        if not comp.product_certificate:
            attribute_line = corte.product_template_id.attribute_line_ids.filtered(lambda l: l.attribute_id.attribute_cosal == 'certificado')
            cert_value = attribute_line.product_template_value_ids.filtered(lambda v: v.product_attribute_value_id == no_certificate)
            combination |= cert_value
        return combination

    #==== HELPERS ====#
    def get_domain_search_components_filters(self):
        if LOG == 1: _logger.info('******* 18')
        StockWarehouse = self.env['stock.warehouse']
        ProductProduct = self.env['product.product']
        WizCombination = self.env["sale.product.configuration.combination"]

        for conf in self:
            wh_ids = conf.products_warehouse_ids if conf.products_warehouse_ids else StockWarehouse.search([])
            domain = []
            if conf.product_family:
                domain += [
                    ("product_template_attribute_value_ids", "=", conf.product_family.name),
                    ('product_template_attribute_value_ids.attribute_id.attribute_cosal', '=', 'familia')
                ]
            if conf.product_subfamily:
                domain += [
                    ("product_template_attribute_value_ids", "=", conf.product_subfamily.name),
                    ('product_template_attribute_value_ids.attribute_id.attribute_cosal', '=', 'subfamilia')
                ]
            if conf.product_type:
                domain += [
                    ("product_template_attribute_value_ids", "=", conf.product_type.name),
                    ('product_template_attribute_value_ids.attribute_id.attribute_cosal', '=', 'tipo')
                ]
            if conf.product_color:
                domain += [
                    ("product_template_attribute_value_ids", "=", conf.product_color.name),
                    ('product_template_attribute_value_ids.attribute_id.attribute_cosal', '=', 'color')
                ]
            if conf.product_grams:
                domain += [
                    ("product_template_attribute_value_ids", "=", conf.product_grams.name),
                    ('product_template_attribute_value_ids.attribute_id.attribute_cosal', '=', 'gramos')
                ]
            if conf.product_certificate:
                domain += [
                    ("product_template_attribute_value_ids", "=", conf.product_certificate.name),
                    ('product_template_attribute_value_ids.attribute_id.attribute_cosal', '=', 'certificado')
                ]
            if conf.product_center_qty:
                domain += [
                    ("product_center_qty", "=", conf.product_center_qty),
                    ('product_template_attribute_value_ids.attribute_id.attribute_cosal', '=', 'centro')
                ]
            if conf.product_diameter_qty:
                domain += [
                    ("product_diameter_qty", ">=", conf.product_diameter_qty),
                    ('product_template_attribute_value_ids.attribute_id.attribute_cosal', '=', 'diametro')
                ]
            if conf.product_wide_qty:
                domain += [
                    ("product_wide_qty", ">=", conf.product_wide_qty ),
                    ('product_template_attribute_value_ids.attribute_id.attribute_cosal', '=', 'ancho')
                ]
            product_ids = ProductProduct.search(domain) if domain else ProductProduct
            
            indx10 = 10
            indx100 = 100
            for product_id in product_ids:
                for indx, ws in enumerate(wh_ids):
                    qty_available = product_id.with_context(warehouse=ws.id).qty_available
                    if float_is_zero(qty_available, precision_rounding=2):
                        continue
                    largo = False
                    is_warehouse = True if ws == conf.warehouse_id else False
                    sequence = indx10 if ws == conf.warehouse_id else indx100 + indx
                    product_atts = product_id._get_domain_product_template_attribute_value()
                    if conf.product_quantity:
                        if conf.product_quantity_uom == 'kg' and qty_available < conf.product_quantity:
                            continue
                        if conf.product_quantity_uom == 'millares' and product_atts.get("millares") < conf.product_quantity:
                            continue
                        largo = self.env['product.template.attribute.value'].browse(product_atts.get('largo_id')).name if product_atts.get('largo_id') else False
                    vals_tmp = {
                        "sequence": sequence,
                        "name": product_id.name,
                        "is_warehouse": is_warehouse,
                        "product_id": product_id.id,
                        "product_uom_id": product_id.uom_id.id,
                        "product_cosal": product_id.product_tmpl_id.product_cosal,
                        "warehouse_name": ws.name or '',
                        "warehouse_id": ws.id,
                        "available_quantity": qty_available or 0.0,
                        "product_wide": product_atts.get("ancho"),
                        "product_long": product_atts.get("largo") or largo,
                        "product_centro": product_atts.get("centro"),
                        "product_diametro": product_atts.get("diametro"),
                        "product_family": product_atts.get("familia"),
                        "product_subfamily": product_atts.get("subfamilia"),
                        "product_type": product_atts.get("tipo"),
                        "product_color": product_atts.get("color"),
                        "product_grams": product_atts.get("gramos"),
                        "product_millares": product_atts.get("millares"),
                        "product_certificate": product_atts.get("certificado"),
                        "wizard_id": conf.id
                    }
                    WizCombination.create(vals_tmp)
        return True

    def get_value_att_val(self, att_cosal, product_att, product_tmpl_id):
        if LOG == 1: _logger.info('******* 19 IN')
        ProductAttribute = self.env['product.attribute']
        ProductAttributeValue = self.env['product.attribute.value']
        TemplateAttributeValue = self.env["product.template.attribute.value"]
        if att_cosal in ["ancho", "largo", "centro", "diametro"]:
            att_val = TemplateAttributeValue.search([
                ('attribute_id.attribute_cosal', '=', att_cosal), 
                ('product_tmpl_id', '=', product_tmpl_id.id)
            ]).filtered(lambda p: float('0.0' if p.name == '-' else p.name) == product_att)
        else:
            att_val = TemplateAttributeValue.search([
                ('attribute_id.attribute_cosal', '=', att_cosal), 
                ('product_tmpl_id', '=', product_tmpl_id.id),
                ('name', '=', product_att)
            ])
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
    """
    def get_combination(self, comp): # TODO, esta función ya no se usa hay que borrarla
        if LOG == 1: _logger.info('******* 20')
        AttrValue = self.env["product.template.attribute.value"]
        combination = AttrValue.browse()
        atts = comp.product_id._get_domain_product_template_attribute_value()
        combination |= AttrValue.browse(atts.get('familia_id'))
        combination |= AttrValue.browse(atts.get('subfamilia_id'))
        combination |= AttrValue.browse(atts.get('tipo_id'))
        combination |= AttrValue.browse(atts.get('color_id'))
        combination |= AttrValue.browse(atts.get('gramos_id'))
        if comp.product_certificate:
            combination |= AttrValue.browse(atts.get('certificado_id'))
        ancho_id = AttrValue.browse(atts.get('ancho_id'))
        centro_id = AttrValue.browse(atts.get('centro_id'))
        diametro_id = AttrValue.browse(atts.get('diametro_id'))
        return combination, ancho_id, centro_id, diametro_id
    """

