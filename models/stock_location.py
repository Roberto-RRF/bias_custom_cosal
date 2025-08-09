# -*- coding: utf-8 -*-
from odoo import fields, models

class StockLocation(models.Model):
    _inherit = 'stock.location'

    x_consider_for_cosal_quoter = fields.Boolean(
        string="Considerar para cotizador COSAL",
        help="Si se marca, el inventario en esta ubicación será considerado por el cotizador de productos COSAL."
    )