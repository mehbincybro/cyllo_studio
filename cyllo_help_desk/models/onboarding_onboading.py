from odoo import api, models


class OnboardingOnboarding(models.Model):
    _inherit = 'onboarding.onboarding'

    @api.model
    def action_close_panel_helpdesk_ticket(self):
        self.action_close_panel('cyllo_help_desk.onboarding_onboarding_helpdesk_ticket')
