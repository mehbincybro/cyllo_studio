# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class FrontdeskVisitor(models.Model):
    _name = 'frontdesk.visitor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Frontdesk Visitor'
    _order = 'check_in desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True, copy=False, readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    visitor_type = fields.Selection([
        ('meeting', 'Meeting'),
        ('enquiry', 'Enquiry'),
    ], string='Visitor Type', default='meeting', required=True, tracking=True)

    partner_id = fields.Many2one('res.partner', string='Customer/Partner',
                                 tracking=True)
    visitor_name = fields.Char(string='Visitor Name', required=True,
                               tracking=True)

    phone = fields.Char(string='Phone', tracking=True)
    email = fields.Char(string='Email', tracking=True)
    company = fields.Char(string='Company', tracking=True)
    enquiry_id = fields.Many2one(
        'frontdesk.enquiry',
        string='Enquiry Reference',
        readonly=True,
        copy=False,
        tracking=True,
    )
    host_id = fields.Many2one('hr.employee', string='Host', help='Employee being visited', tracking=True)
    station_id = fields.Many2one('frontdesk.frontdesk', string='Station', required=True, tracking=True)
    is_host = fields.Boolean(related='station_id.is_host', string='Host Selection', readonly=True)
    is_drink = fields.Boolean(related='station_id.is_drink', string='Offer Drinks', readonly=True)
    drink_selection_ids = fields.Many2many('frontdesk.drink', related='station_id.drink_selection_ids', string='Drinks Offered', readonly=True)
    check_in = fields.Datetime(string='Check-In Time', readonly=True, tracking=True)
    check_out = fields.Datetime(string='Check-Out Time', readonly=True, tracking=True)
    drink_id = fields.Many2one('frontdesk.drink', string='Drink Requested', tracking=True)
    drink_served = fields.Boolean(string='Drink Served', default=False, tracking=True)
    state = fields.Selection([
        ('planned', 'Planned'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='planned', required=True, tracking=True)
    duration = fields.Float(string='Duration (Hours)', compute='_compute_duration', store=True)

    @api.onchange('station_id')
    def _onchange_station_id(self):
        if self.station_id:
            if not self.station_id.is_host:
                self.host_id = False
            if not self.station_id.is_drink:
                self.drink_id = False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.visitor_name = self.partner_id.name
            self.phone = self.partner_id.phone or self.partner_id.mobile
            self.email = self.partner_id.email
            self.company = self.partner_id.parent_id.name if self.partner_id.parent_id else (
                self.partner_id.name if self.partner_id.is_company else False
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'frontdesk.visitor') or _('New')
            if vals.get('station_id'):
                station = self.env['frontdesk.frontdesk'].browse(
                    vals['station_id'])
                if not station.is_host:
                    vals['host_id'] = False
                if not station.is_drink:
                    vals['drink_id'] = False
        return super().create(vals_list)


    def write(self, vals):
        if any(f in vals for f in ('station_id', 'host_id', 'drink_id')):
            for visitor in self:
                station = self.env['frontdesk.frontdesk'].browse(vals.get('station_id', visitor.station_id.id))
                if not station.is_host:
                    vals['host_id'] = False
                if not station.is_drink:
                    vals['drink_id'] = False
        return super().write(vals)

    @api.depends('check_in', 'check_out')
    def _compute_duration(self):
        for visitor in self:
            if visitor.check_in and visitor.check_out:
                diff = visitor.check_out - visitor.check_in
                visitor.duration = diff.total_seconds() / 3600.0
            elif visitor.check_in:
                diff = fields.Datetime.now() - visitor.check_in
                visitor.duration = diff.total_seconds() / 3600.0
            else:
                visitor.duration = 0.0

    def action_check_in(self):
        for visitor in self:
            if visitor.state != 'planned':
                raise UserError(_('Only planned visits can be checked in.'))
            visitor.write({
                'state': 'checked_in',
                'check_in': fields.Datetime.now()
            })
            visitor.message_post(body=_("Visitor checked in."))
            visitor._send_notifications()

    def action_check_out(self):
        for visitor in self:
            if visitor.state != 'checked_in':
                raise UserError(_('Only checked in visits can be checked out.'))
            visitor.write({
                'state': 'checked_out',
                'check_out': fields.Datetime.now()
            })
            visitor.message_post(body=_("Visitor checked out. Duration: %s hours.") % round(visitor.duration, 2))

    def action_cancel(self):
        for visitor in self:
            if visitor.state == 'checked_out':
                raise UserError(_('You cannot cancel a visit that is already checked out.'))
            visitor.write({
                'state': 'cancelled'
            })
            visitor.message_post(body=_("Visit cancelled."))

    def action_drink_served(self):
        for visitor in self:
            visitor.write({'drink_served': True})
            visitor.message_post(body=_("Drink served: %s") % (visitor.drink_id.name or _("N/A")))

    def action_create_enquiry(self):
        self.ensure_one()
        if self.visitor_type != 'enquiry':
            raise UserError(_("Only enquiry visitors can create an enquiry."))
        if self.enquiry_id:
            raise UserError(_("An enquiry is already linked to this visitor."))
        return {
            'name': _('Create Enquiry'),
            'type': 'ir.actions.act_window',
            'res_model': 'frontdesk.visitor.enquiry.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_visitor_id': self.id,
                'default_visitor_name': self.name,
                'default_phone': self.phone,
                'default_email': self.email,
                'default_company': self.company,
                'default_station_id': self.station_id.id,
                'default_handled_by': self.host_id.id,
            },
        }

    def _send_notifications(self):
        """Send notifications to host and/or station responsibles upon visitor check-in."""
        for visitor in self:
            station = visitor.station_id
            host = visitor.host_id
            
            # Formulate notification message
            drink_msg = f" (Requested Drink: {visitor.drink_id.name})" if visitor.drink_id else ""
            company_msg = f" from {visitor.company}" if visitor.company else ""
            msg_body = _("Visitor <b>%(visitor_name)s</b>%(company)s has checked in for <b>%(host_name)s</b> at %(station_name)s%(drink)s.") % {
                'visitor_name': visitor.name,
                'company': company_msg,
                'host_name': host.name if host else _("No Host Specified"),
                'station_name': station.name,
                'drink': drink_msg
            }

            # 1. Notify Host by Email / Discuss if configured
            if host:
                if station.notify_by_email and host.work_email:
                    self.env['mail.mail'].create({
                        'subject': _("Visitor Check-In: %(visitor_name)s") % {'visitor_name': visitor.name},
                        'body_html': f"<p>{msg_body}</p>",
                        'email_to': host.work_email,
                    }).send()

                if station.notify_by_discuss and host.user_id:
                    host.user_id.partner_id.message_post(
                        body=msg_body,
                        message_type='notification',
                        subtype_xmlid='mail.mt_comment'
                    )

            # 2. Notify Station Responsibles
            for responsible in station.responsible_ids:
                if station.notify_by_email and responsible.work_email:
                    self.env['mail.mail'].create({
                        'subject': _("Visitor Check-In at %(station_name)s: %(visitor_name)s") % {
                            'station_name': station.name,
                            'visitor_name': visitor.name
                        },
                        'body_html': f"<p>{msg_body}</p>",
                        'email_to': responsible.work_email,
                    }).send()

                if station.notify_by_discuss and responsible.user_id:
                    responsible.user_id.partner_id.message_post(
                        body=msg_body,
                        message_type='notification',
                        subtype_xmlid='mail.mt_comment'
                    )

            # 3. Notify Drink preparation team if visitor requested a drink
            if visitor.drink_id and visitor.drink_id.notify_user_ids:
                drink_body = _("Drink requested: <b>%(drink_name)s</b> for visitor <b>%(visitor_name)s</b> at %(station_name)s.") % {
                    'drink_name': visitor.drink_id.name,
                    'visitor_name': visitor.name,
                    'station_name': station.name
                }
                for drink_notify in visitor.drink_id.notify_user_ids:
                    if drink_notify.work_email:
                        self.env['mail.mail'].create({
                            'subject': _("Drink Request: %(drink_name)s") % {'drink_name': visitor.drink_id.name},
                            'body_html': f"<p>{drink_body}</p>",
                            'email_to': drink_notify.work_email,
                        }).send()
                    if drink_notify.user_id:
                        drink_notify.user_id.partner_id.message_post(
                            body=drink_body,
                            message_type='notification',
                            subtype_xmlid='mail.mt_comment'
                        )
