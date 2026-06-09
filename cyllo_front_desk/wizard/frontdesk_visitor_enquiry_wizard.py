# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class FrontdeskVisitorEnquiryWizard(models.TransientModel):
    _name = 'frontdesk.visitor.enquiry.wizard'
    _description = 'Create Enquiry from Visitor'

    visitor_id = fields.Many2one('frontdesk.visitor', string='Visitor', required=True, readonly=True)
    visitor_name = fields.Char(string='Visitor Name', required=True)
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    company = fields.Char(string='Company / Organization')
    station_id = fields.Many2one('frontdesk.frontdesk', string='Station', required=True)
    handled_by = fields.Many2one('hr.employee', string='Handled By')
    enquiry_type = fields.Selection([
        ('general', 'General Information'),
        ('product', 'Product / Service'),
        ('pricing', 'Pricing & Quotation'),
        ('support', 'Support / Complaint'),
        ('career', 'Career / Recruitment'),
        ('other', 'Other'),
    ], string='Enquiry Type', required=True, default='general')
    subject = fields.Char(string='Subject', required=True)
    description = fields.Text(string='Enquiry Details')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'High'),
        ('2', 'Urgent'),
    ], string='Priority', default='0')
    follow_up_date = fields.Date(string='Follow-Up Date')
    follow_up_notes = fields.Text(string='Follow-Up Notes')

    def action_create_enquiry(self):
        self.ensure_one()
        visitor = self.visitor_id
        if visitor.enquiry_id:
            raise UserError(_("An enquiry is already linked to this visitor."))

        enquiry = self.env['frontdesk.enquiry'].create({
            'visitor_name': self.visitor_name,
            'phone': self.phone,
            'email': self.email,
            'company': self.company,
            'station_id': self.station_id.id,
            'handled_by': self.handled_by.id,
            'enquiry_type': self.enquiry_type,
            'subject': self.subject,
            'description': self.description,
            'priority': self.priority,
            'follow_up_date': self.follow_up_date,
            'follow_up_notes': self.follow_up_notes,
            'visitor_id': visitor.id,
        })
        visitor.enquiry_id = enquiry.id
        visitor.message_post(
            body=_("Enquiry created: <a href='#' data-oe-model='frontdesk.enquiry' data-oe-id='%d'>%s</a>") % (enquiry.id, enquiry.name)
        )
        enquiry.message_post(
            body=_("Created from visitor: <a href='#' data-oe-model='frontdesk.visitor' data-oe-id='%d'>%s</a>") % (visitor.id, visitor.name)
        )

        return {
            'name': _('Enquiry'),
            'type': 'ir.actions.act_window',
            'res_model': 'frontdesk.enquiry',
            'res_id': enquiry.id,
            'view_mode': 'form',
            'target': 'current',
        }
