# -*- coding: utf-8 -*-
from ast import literal_eval
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MarketingFilter(models.Model):
    """
        This model is used to define filter domains that can be applied to
        marketing campaigns to target specific groups of participants based on
        certain conditions in the associated target models.
    """
    _name = "marketing.filter"
    _description = "Marketing Filter"
    _inherit = 'mail.thread'

    name = fields.Char(string="Filter Name", help="Enter a name for the filter", required=True)
    user_id = fields.Many2one('res.users', string="Created By", default=lambda self: self.env.user,
                              readonly=True, help='Responsible user ')
    model_id = fields.Many2one('ir.model', string="Target Model", ondelete='cascade',
                               help='Choose target model to filter records')
    model_name = fields.Char(related='model_id.model', store=True, help='Model Name')
    domain = fields.Char(help='Domain to filter the records')

    @api.constrains('domain', 'model_id')
    def _check_domain(self):
        """ Check that if the mailing domain is set, it is a valid one """
        for filters in self:
            if filters.domain != "[]":
                try:
                    self.env[filters.model_id.model].search_count(literal_eval(filters.domain))
                except:
                    raise ValidationError(_("The filter domain is not valid for this target model."))
