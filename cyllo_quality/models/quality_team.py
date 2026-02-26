# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools.populate import compute


class QualityTeam(models.Model):
    _name = 'quality.team'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Quality Team'

    name = fields.Char(string='Name', required=True)
    leader_id = fields.Many2one('hr.employee', string='Team Lead')
    member_ids = fields.Many2many('hr.employee', string='Team Members',compute='_compute_member_ids',readonly=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    is_mail = fields.Boolean(string='Send Email', default=True)
    @api.depends('leader_id')
    def _compute_member_ids(self):

        for record in self:
            record.member_ids = False
            if record.leader_id:
                record.member_ids = [fields.Command.link(record.leader_id.id)]


