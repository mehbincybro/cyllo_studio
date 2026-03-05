from odoo import models, fields, api
from odoo.http import request

class AuditLog(models.Model):
    _name = 'audit.log'
    _description = 'Audit Log'
    _order = 'create_date desc'

    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user, readonly=True)
    user_name = fields.Char(related='user_id.name', store=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, readonly=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.name', store=True)
    model = fields.Char(related='model_id.model', store=True)
    res_id = fields.Integer(string='Record ID', required=True, readonly=True)
    record_name = fields.Char(string='Record Name', compute='_compute_record_name', store=True)
    # FIX: Add 'read' to the selection options
    operation = fields.Selection([
        ('create', 'Create'),
        ('write', 'Update'),
        ('unlink', 'Delete'),
        ('read', 'Read')  # Added read operation
    ], string='Operation', required=True, readonly=True)
    field_name = fields.Char(readonly=True)
    old_value = fields.Text(readonly=True)
    new_value = fields.Text(readonly=True)
    line_ids = fields.One2many('audit.log.line', 'log_id', string='Change Lines')
    log_level = fields.Selection([('info', 'Info'), ('warning', 'Warning'), ('critical', 'Critical')], string='Log Level', required=True, readonly=True)
    ip_address = fields.Char(readonly=True)
    session_id = fields.Many2one('audit.session', string='Audit Session', readonly=True)
    create_date = fields.Datetime(string='Change Date', default=fields.Datetime.now, readonly=True)

    @api.depends('user_id', 'create_date', 'operation', 'model_id', 'res_id')
    def _compute_display_name(self):
        for log in self:
            log.display_name = f"{log.user_id.name} - {log.operation} - {log.model_id.name} #{log.res_id} - {log.create_date}"

    @api.depends('model', 'res_id')
    def _compute_record_name(self):
        for log in self:
            try:
                rec = self.env[log.model].sudo().browse(log.res_id)
                log.record_name = rec.display_name if rec.exists() else f"#{log.res_id}"
            except Exception:
                log.record_name = f"#{log.res_id}"

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if 'ip_address' not in v:
                v['ip_address'] = (request.httprequest.environ.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.httprequest.remote_addr or '') if request else ''
            if 'session_id' not in v:
                session = self.env['audit.session'].sudo().get_or_create_session()
                v['session_id'] = session.id if session else False
        return super().create(vals_list)


class AuditLogLine(models.Model):
    _name = 'audit.log.line'
    _description = 'Audit Log Line'
    _order = 'log_id, id'

    log_id = fields.Many2one('audit.log', required=True, ondelete='cascade')
    field_name = fields.Char(required=True)
    field_label = fields.Char(compute='_compute_field_label', store=True)
    old_value = fields.Text()
    new_value = fields.Text()

    @api.depends('log_id.model_id', 'field_name')
    def _compute_field_label(self):
        for line in self:
            line.field_label = line.field_name.replace('_', ' ').title()
            if line.log_id.model_id:
                f = self.env['ir.model.fields'].search([
                    ('model_id', '=', line.log_id.model_id.id),
                    ('name', '=', line.field_name)
                ], limit=1)
                if f:
                    line.field_label = f.field_description