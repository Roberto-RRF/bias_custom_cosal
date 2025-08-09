# -*- coding: utf-8 -*-
{
    'name': 'Bias Custom Cosal',
    'version': '17.0.0.58',
    'summary': """ Bias Custom Cosal Summary """,
    'author': 'OpenBIAS',
    'website': 'https://bias.com.mx',
    'category': 'Uncategorized',
    'depends': ['base', 'product', 'stock', 'mrp', 'sale'],
    "data": [
        "security/ir.model.access.csv",
        "views/product_product_views.xml",
        "views/sale_order_views.xml",
        "views/product_attribute_value_views.xml",
        "wizard/sale_product_configuration_views.xml"
    ],
    'assets': {
        'web.assets_backend': [
            # 'bias_custom_cosal/static/src/**/*',
        ],
    },       
    'application': False,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
