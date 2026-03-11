from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _init_messaging(self):
        values = super()._init_messaging()
        helpdesk_shortcodes = self.env['helpdesk.canned.response'].sudo().search_read(
            [],
            ['source', 'substitution'],
        )
        existing_sources = {item['source'] for item in values.get('shortcodes', []) if item.get('source')}
        for shortcode in helpdesk_shortcodes:
            if shortcode.get('source') and shortcode['source'] not in existing_sources:
                values.setdefault('shortcodes', []).append(shortcode)
        return values
