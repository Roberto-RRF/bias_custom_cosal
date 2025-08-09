# -*- coding: utf-8 -*-
import logging

from odoo import models, fields

class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    attribute_cosal = fields.Selection(selection=[
        ('', ''),
        ('familia', 'Familia'),
        ('subfamilia', 'Subfamilia'),
        ('tipo', 'Tipo'),
        ('color', 'Color'),
        ('gramos', 'Gramos'),
        ('ancho', 'Ancho'),
        ('largo', 'Largo'),
        ('centro', 'Centro'),
        ('diametro', 'Diametro'),
        ('certificado', 'Certificado'),        
    ], string="Tipo Atributo", default="")

# largo => Disponible solo Hoja
# centro / diametro => Disponible solo Rollo