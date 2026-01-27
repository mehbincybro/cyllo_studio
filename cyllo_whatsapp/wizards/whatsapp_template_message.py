# -*- coding: utf-8 -*-
import base64

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class WhatsappTemplateMessage(models.TransientModel):
    """ Model to manage WhatsApp template messages."""
    _name = 'whatsapp.template.message'
    _description = 'WhatsApp Template Message'

    partner_id = fields.Many2one('res.partner', readonly=False, compute='_compute_partner_id')
    header_type = fields.Selection(help='Choose the header type here', related='wa_template_id.header_type')
    wa_template_id = fields.Many2one('whatsapp.template', string='Whatsapp Template',
                                     domain="[('state','=','approved')]")
    attachment_id = fields.Many2one('ir.attachment', compute='_compute_attachment_id',
                                    help='The attachment in the header of template')
    model_id = fields.Many2one('ir.model', string='Reference Model', help='The reference model for the template')
    res_id = fields.Integer(string='Record ID', help='The record ID for the template datas')
    body = fields.Html(compute="_compute_body", help='The body of whatsapp template')

    @api.depends('wa_template_id')
    def _compute_attachment_id(self):
        """Compute method to determine the attachment based on the header type."""
        self.attachment_id = False
        if self.header_type in ['document']:
            record = self.env[self.model_id.model].browse(self.res_id)
            report_content = self.env['ir.actions.report']._render_qweb_pdf(
                self.wa_template_id.report_id.id, record.id)[0]
            if self.wa_template_id.report_id.print_report_name:
                report_name = safe_eval(self.wa_template_id.report_id.print_report_name,
                                        {'object': record}) + '.' + 'pdf'
            else:
                report_name = f"{record.name}.pdf"
            ir_values = {
                'name': report_name,
                'type': 'binary',
                'datas': base64.b64encode(report_content),
                'mimetype': 'application/pdf',
                'res_model': 'whatsapp.template.message',
                'res_id': 0
            }
            attachment = self.env['ir.attachment'].create(ir_values)
            self.attachment_id = attachment.id

    @api.depends('wa_template_id')
    def _compute_body(self):
        """Compute method to determine the body of the WhatsApp template."""
        for record in self:
            preview_data = {
                'body': self.wa_template_id._get_formatted_template_body(record=record.res_id, demo_value=False),
                'header_text': self.wa_template_id._get_formatted_template_header(record=record.res_id,
                                                                                  demo_value=False),
                'attachment': self.attachment_id,
                'header_type': self.wa_template_id.header_type,
                'footer_text': self.wa_template_id.footer_text,
            } if record.wa_template_id else None
            record.body = self.env['ir.qweb']._render('cyllo_whatsapp.whatsapp_template_preview_templates',
                                                      preview_data) if preview_data else None

    @api.depends('model_id', 'res_id')
    def _compute_partner_id(self):
        """Compute method to determine the partner ID based on the model and record ID."""
        for rec in self:
            model = rec.model_id
            record = self.env[model.model].browse(rec.res_id)
            if hasattr(record, 'partner_id'):
                rec.partner_id = record.partner_id.id
            elif model.model == 'res.partner':
                rec.partner_id = record.id

    def action_send_template(self):
        """Action method to send a WhatsApp template."""
        if not self.wa_template_id:
            raise ValidationError(_('Please add template you want to send'))
        record = self.env[self.model_id.model].browse(self.res_id)
        self.wa_template_id.action_send_template(record, self.attachment_id, self.partner_id)

    def action_default_template(self):
        """Action method to set default values for the WhatsApp template message."""
        wa_template_id = self.env['whatsapp.template'].search([('model_id', '=', self.env.context['model']),
                                                               ('state', '=', 'approved')], limit=1)
        if not wa_template_id:
            raise ValidationError(_('No template found for this model'))
        context = {
            'default_wa_template_id': wa_template_id.id,
            'default_res_id': self.env.context['active_id'],
            'default_model_id': self.env['ir.model'].search([('model', '=', self.env.context['model'])]).id,
            'default_header_type': wa_template_id.header_type
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'whatsapp.template.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': context,
        }
