from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Pricelist(models.Model):
    _inherit = "product.pricelist"

    subscription_pricing_ids = fields.One2many(
        comodel_name='subscription.pricing',
        inverse_name='pricelist_id',
        string="Time Based Price Rules",
        copy=True)


    def _get_time_based_price_rule(self,product_template_id,subscription_unit,duration,date,product_uom_qty):
            suitable_price_rule = self.env['subscription.pricing'].search([
                ('id', 'in', self.subscription_pricing_ids.ids),
                ('product_tmpl_id', '=', product_template_id),
                ('subscription_unit', '=',subscription_unit),
                ('duration', '=',duration),
                '|', ('date_start', '=', False), ('date_start', '<=',date),
                '|', ('date_end', '=', False), ('date_end', '>=', date),
                ('min_quantity', '<=',product_uom_qty)],order='min_quantity desc', limit=1)
            return suitable_price_rule



