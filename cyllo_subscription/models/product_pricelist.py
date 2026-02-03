from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Pricelist(models.Model):
    _inherit = "product.pricelist"

    subscription_pricing_ids = fields.One2many(
        comodel_name='subscription.pricing',
        inverse_name='pricelist_id',
        string="Time Based Price Rules",
        copy=True)



