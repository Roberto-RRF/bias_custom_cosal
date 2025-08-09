# -*- coding: utf-8 -*-

from odoo import models, fields

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    source = fields.Char(
        string='Source of Order',
        help='Sale Order from which this Manufacturing Order created.')
    sale_line_id = fields.Many2one(
        'sale.order.line', string='Sale Line',
        help="Corresponding sale order line id")
    qty_to_produce = fields.Float(
        string='Quantity to Produce',
        help='The number of products to be produced.')
    product_comment = fields.Html(string='Comentarios')

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    order_id = fields.Many2one(
        'sale.order', string='Sale Order',
        help="Corresponding sale order")
    product_wide = fields.Float(
        string="Wide",
        digits='Product Unit of Measure', default=1.0)
    product_number_cuts = fields.Float(
        string="Number of cuts",
        digits='Product Unit of Measure', default=1.0)
