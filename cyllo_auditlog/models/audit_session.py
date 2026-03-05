from odoo import models, fields, api

class AuditSession(models.Model):
    _name = 'audit.session'
    _description = 'User Audit Session'
    _order = 'login_time desc'

    name = fields.Char(string='Session ID', required=True, readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True, readonly=True)
    ip_address = fields.Char(string='IP Address', readonly=True)
    user_agent = fields.Text(string='User Agent', readonly=True)
    login_time = fields.Datetime(string='Login Time', default=fields.Datetime.now, readonly=True)
    last_activity = fields.Datetime(string='Last Activity', default=fields.Datetime.now, readonly=True)
    active = fields.Boolean(string='Active', default=True)

    log_count = fields.Integer(string='Logs', compute='_compute_log_count')

    def _compute_log_count(self):
        for session in self:
            session.log_count = self.env['audit.log'].search_count([('session_id', '=', session.id)])

    @api.model
    def get_or_create_session(self, sid=None):
        """Get or create audit.session record concisely."""
        from odoo.http import request
        if not (sid := sid or (request and getattr(request.session, 'sid', False))):
            return False

        session_rec = self.sudo().search([('name', '=', sid)], limit=1)
        if session_rec:
            session_rec.sudo().write({'last_activity': fields.Datetime.now()})
            return session_rec

        user = self.env.user
        if not user or user._is_public():
            return False
        user_id = user.id

        # Compact IP/UA extraction
        ip = request.httprequest.remote_addr if request else ''
        if request and 'HTTP_X_FORWARDED_FOR' in request.httprequest.environ:
            ip = request.httprequest.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()

        return self.sudo().create({
            'name': sid,
            'user_id': user_id,
            'ip_address': ip,
            'user_agent': request.httprequest.environ.get('HTTP_USER_AGENT', '') if request else '',
            'login_time': fields.Datetime.now(),
        })
