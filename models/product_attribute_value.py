# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    parent_ids = fields.Many2many('product.attribute.value', 'product_attribute_value_parent_rel', 'child_id', 'parent_id', string='Valor Padre')

    




