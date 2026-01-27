# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """class involves adding fields to crm settings"""
    _inherit = 'res.config.settings'
    deal_reminder = fields.Boolean(string="Deal Reminder",
                                   config_parameter='Cyllo_Crm.'
                                                    'deal_reminder')
    deal_reminder_days = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10'),
    ], string='reminder', default='10',
        config_parameter='Cyllo_Crm.deal_reminder_days')

    is_exit_criteria_configured = fields.Boolean()

    stage_activity_ids = fields.Many2many('crm.stage.activity')

    module_cyllo_crm_advance_lead = fields.Boolean(string="Advance Lead")

    @api.onchange('module_cyllo_crm_advance_lead')
    def _onchange_module_cyllo_crm_advance_lead(self):
        if self.module_cyllo_crm_advance_lead:
            self.group_use_lead = True

    def set_values(self):
        """Override set_values to handle module uninstallation properly"""
        super(ResConfigSettings, self).set_values()

        # Uninstall the modules if group_use_lead is not enabled
        if not self.group_use_lead:
            modules_to_uninstall = ['cyllo_crm_review',
                                    'cyllo_crm_advance_lead']
            module_model = self.env['ir.module.module'].sudo()

            for module_name in modules_to_uninstall:
                module = module_model.search(
                    [('name', '=', module_name), ('state', '=', 'installed')],
                    limit=1)
                if module:
                    # Defer uninstall using a post-commit hook to avoid uninstalling while still using the field
                    self.env.cr.postcommit.add(
                        lambda m=module: m.button_immediate_uninstall())

    def action_configure_exit_criteria(self):
        """trigger a popup in crm settings and load previously created exit criterias"""
        self.ensure_one()

        # Get all CRM stages
        stages = self.env['crm.stage'].search([])

        # Create wizard record
        wizard = self.env['crm.stage.exit.criteria'].create({
            'stage_ids': [(6, 0, stages.ids)],
        })

        # Fetch existing exit criteria and add them to the wizard
        existing_criteria = self.env['crm.stage.activity'].search(
            [('is_exit_criteria', "=", True)])
        if existing_criteria:
            criteria_vals = []
            for criteria in existing_criteria:
                criteria_vals.append((0, 0, {
                    'stage_id': criteria.stage_id.id,
                    'activity_id': criteria.activity_id.id,
                    'user_id': criteria.user_id.id if hasattr(criteria,
                                                              'user_id') else False,
                }))
            wizard.write({'exit_criteria_ids': criteria_vals})

        # Check if no data was added to the wizard
        has_criteria = bool(wizard.exit_criteria_ids)

        return {
            'name': 'Configure Stage Exit Criteria',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.stage.exit.criteria',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
            'context': {'has_criteria': has_criteria}  # Pass this to the view
        }
