from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _authenticate(cls, endpoint):
        """
        Capture session on successful authentication/capture for all interactive requests
        if session tracking is enabled.
        """
        res = super()._authenticate(endpoint)
        if request and request.uid:
            # Check if any active audit rule has track_session enabled
            # This ensures we only create audit.session records when necessary
            # Use request.env because it's available in this context
            domain = [('active', '=', True), ('track_session', '=', True)]
            if request.env['audit.rule'].sudo().search_count(domain) > 0:
                request.env['audit.session'].sudo().get_or_create_session()
        return res
