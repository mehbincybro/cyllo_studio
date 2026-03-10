from odoo import http, fields
from odoo.http import request
from odoo.addons.web.controllers.session import Session

class AuditSessionController(Session):
    @http.route('/web/session/logout', type='http', auth="none")
    def logout(self):
        if request and getattr(request, 'session', False):
            session_rec = request.env['audit.session'].sudo().search([('name', '=', request.session.sid)], limit=1)
            if session_rec:
                session_rec.sudo().write({'logout_time': fields.Datetime.now()})
        return super(AuditSessionController, self).logout()
