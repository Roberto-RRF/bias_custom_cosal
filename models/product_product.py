# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, tools, models, Command

class ProductTemplate(models.Model):
    _inherit = "product.template"

    product_wide = fields.Float(
        string="Wide",
        digits='Product Unit of Measure', default=1.0)
    product_cosal = fields.Selection(selection=[
        ('', ''),
        ('rollo', 'Rollo'),
        ('hoja', 'Hoja')
    ], string="Rollo/Hoja", default="")

    def get_attributte_product_cosal(self, product_filter, product_qty):
        ProductAttribute = self.env['product.attribute']
        ProductAttributeValue = self.env['product.attribute.value']
        att_id = ProductAttribute.search([
            ('attribute_cosal', '=', 'ancho')
        ])
        att_value_id = self.attribute_line_ids.filtered(lambda p: 
            p.attribute_id.attribute_cosal == product_filter
        )
        att_values_id = att_value_id.value_ids.filtered(lambda p: float('0.0' if p.name == '-' else p.name) == product_qty)
        if not att_values_id:
            wide_id = ProductAttributeValue.search([
                ('attribute_id', '=', att_id.id)
            ]).filtered(lambda p: float('0.0' if p.name == '-' else p.name) == product_qty)
            if not wide_id:
                wide_id = ProductAttributeValue.create({
                    'name': str(product_qty),
                    'attribute_id': att_id and att_id.id or False
                })
            att_value_id.write({'value_ids':[(4,wide_id.id)]})
        self.env.cr.commit()
        return att_value_id


class Product(models.Model):
    _inherit = "product.product"

    product_wide_qty = fields.Float(
        compute='_compute_product_wide_qty', store=True,)
    product_long_qty = fields.Float(
        compute='_compute_product_wide_qty', store=True,)
    product_center_qty = fields.Float(
        compute='_compute_product_wide_qty', store=True,)
    product_diameter_qty = fields.Float(
        compute='_compute_product_wide_qty', store=True,)
    product_subfamilia = fields.Char(
        compute='_compute_product_wide_qty', store=True,)

    @api.depends('product_template_attribute_value_ids', 'product_template_attribute_value_ids.attribute_id.attribute_cosal')
    def _compute_product_wide_qty(self):
        for product in self:
            ancho = product.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.attribute_cosal == 'ancho')
            largo = product.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.attribute_cosal == 'largo')
            centro = product.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.attribute_cosal == 'centro')
            diametro = product.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.attribute_cosal == 'diametro')
            subfamilia = product.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.attribute_cosal == 'subfamilia')
            product.product_wide_qty = float(ancho.name) if ancho.name != '-' else '0.0'
            product.product_long_qty = float(largo.name) if largo.name != '-' else '0.0'
            product.product_center_qty = float(centro.name) if centro.name != '-' else '0.0'
            product.product_diameter_qty = float(diametro.name) if diametro.name != '-' else '0.0'
            product.product_subfamilia = subfamilia.name or ''

    def _get_domain_product_template_attribute_value_ids(self):
        p_ids = self.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.attribute_cosal != 'ancho')
        return p_ids.ids

    def _get_domain_product_template_attribute_value(self):
        values = {}
        for product in self:
            familia = product.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.attribute_cosal == "familia")
            subfamilia = product.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.attribute_cosal == "subfamilia")
            tipo = product.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.attribute_cosal == "tipo")
            color = product.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.attribute_cosal == "color")
            gramos = product.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.attribute_cosal == "gramos")
            certificado = product.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.attribute_cosal == "certificado")

            ancho = product.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.attribute_cosal == "ancho")
            largo = product.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.attribute_cosal == "largo")
            centro = product.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.attribute_cosal == "centro")
            diametro = product.product_template_attribute_value_ids.filtered(lambda p: p.attribute_id.attribute_cosal == "diametro")

            values.update({
                "familia": familia.name or "",
                "subfamilia": subfamilia.name or "",
                "tipo": tipo.name or "",
                "color": color.name or "",
                "gramos": gramos.name or "",
                "certificado": certificado.name or "",
                "ancho": float(ancho.name or '0.0'),

                "familia_id": familia and familia.id or False,
                "subfamilia_id": subfamilia and subfamilia.id or False,
                "tipo_id": tipo and tipo.id or False,
                "color_id": color and color.id or False,
                "gramos_id": gramos and gramos.id or False,
                "certificado_id": certificado and certificado.id or False,

                "ancho_id": ancho and ancho.id or False,
                "largo_id": largo and largo.id or False,
                "centro_id": centro and centro.id or False,
                "diametro_id": diametro and diametro.id or False,

                "millares": (float(ancho.name or '0.0') * float(largo.name or '0.0') * float(gramos.name or '0.0')) / 10000
            })
            if largo and largo.name.isnumeric():
                values.update({"largo": float(largo.name or '0.0')})
            if centro and centro.name.isnumeric(): 
                values.update({"centro": float(centro.name or '0.0')})
            if diametro and diametro.name.isnumeric():
                values.update({"diametro": float(diametro.name or '0.0')})

        return values

    def action_update_quantity_on_hand_cosal(self):
        res = self.product_tmpl_id.with_context(default_product_id=self.id, create=False).action_update_quantity_on_hand()
        res["view_mode"] = 'tree'
        res["target"] = 'new'
        return res


