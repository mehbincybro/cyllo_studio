# -*- coding: utf-8 -*-
from odoo import fields, models, _


class HelpDeskTeam(models.Model):
    _inherit = 'helpdesk.team'

    return_count = fields.Integer(compute='_compute_return_count', string="Returns")

    def _compute_return_count(self):
        for team in self:
            team.return_count = self.env['stock.picking'].search_count([
                ('helpdesk_ticket_id.team_id', '=', team.id),
                ('picking_type_code', '=', 'outgoing'),
            ])

    def action_view_team_returns(self):
        self.ensure_one()
        return {
            'name': _('Returns'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('helpdesk_ticket_id.team_id', '=', self.id), ('picking_type_code', '=', 'outgoing')],
            'target': 'current',
        }
