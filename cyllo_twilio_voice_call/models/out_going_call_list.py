# -*- coding: utf-8 -*-
from odoo import api, fields, models
try:
    from twilio.rest import Client
except ImportError:
    pass


class OutGoingCallList(models.Model):
    """The class is used to create the outgoing call list"""
    _name = 'out.going.call.list'
    _description = "Out Going Call List"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'reference'

    reference = fields.Char(readonly=True, copy=False, default='New', help="Reference to the model")
    from_number = fields.Char('From', help='From number to call any number')
    to_number = fields.Char('To', help='Receiving number for testing')
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user.id, string="Caller", readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id, readonly=True)
    start_time = fields.Datetime(help="To get the time and date, when the call is started")
    end_time = fields.Datetime(help="To get the time and date, when the call is ended")
    duration = fields.Char(help="Duration of the call")
    status = fields.Char(help="Status of the call")
    record_sid = fields.Char(string="Record Details", help="Record Sid of the call")
    call_sid = fields.Char(help="To get the call sid")
    image_1920 = fields.Image(string="Image", help="To get the image")
    partner_id = fields.Many2one('res.partner', string="Name")

    @api.model
    def create(self, vals):
        """Supering create function to add reference"""
        if vals.get('reference', 'New') == 'New':
            vals['reference'] = self.env['ir.sequence'].next_by_code('out.going.call.list') or 'New'
        return super(OutGoingCallList, self).create(vals)

    def action_call(self, num, Sid, id):
        """To create an outgoing call list when we're making a call """
        global partner_id
        account_sid = self.env["ir.config_parameter"].sudo().get_param("cyllo_twilio_voice_call.account_sid")
        auth_token = self.env["ir.config_parameter"].sudo().get_param("cyllo_twilio_voice_call.auth_token")
        from_number = self.env["ir.config_parameter"].sudo().get_param("cyllo_twilio_voice_call.from_number")
        client = Client(account_sid, auth_token)
        call = client.calls(Sid).fetch()
        image_1920 = False
        if id:
            partner_id = id
            partner = self.env['res.partner'].browse(partner_id)
            partner = partner[0] if len(partner) > 1 else partner
            image_1920 = partner.image_1920
        if not id:
            partner_id = False
        if call:
            self.env['out.going.call.list'].sudo().create({
                'from_number': from_number,
                'to_number': num,
                'start_time': fields.datetime.now(),
                'duration': call.duration,
                'call_sid': Sid,
                'image_1920': image_1920,
                'partner_id': partner_id
            })

    def action_making_call(self, num, Sid):
        """To create an outgoing call list when we're making a call """
        account_sid = self.env["ir.config_parameter"].sudo().get_param("cyllo_twilio_voice_call.account_sid")
        auth_token = self.env["ir.config_parameter"].sudo().get_param("cyllo_twilio_voice_call.auth_token")
        from_number = self.env["ir.config_parameter"].sudo().get_param("cyllo_twilio_voice_call.from_number")
        client = Client(account_sid, auth_token)
        call = client.calls(Sid).fetch()
        if call:
            self.env['out.going.call.list'].sudo().create({
                'from_number': from_number,
                'to_number': num,
                'start_time': fields.datetime.now(),
                'duration': call.duration,
                'call_sid': Sid,
            })

    def action_cancel(self, num, Sid):
        """The function performs when a call is disconnected"""
        # Retrieve Twilio credentials and phone numbers from configuration
        global partner_id
        account_sid = self.env["ir.config_parameter"].sudo().get_param("cyllo_twilio_voice_call.account_sid")
        auth_token = self.env["ir.config_parameter"].sudo().get_param("cyllo_twilio_voice_call.auth_token")
        from_number = self.env["ir.config_parameter"].sudo().get_param("cyllo_twilio_voice_call.from_number")
        client = Client(account_sid, auth_token)
        image_1920 = False
        if num:
            partner = self.env['res.partner'].search([('phone', '=', num)])
            if partner:
                partner = partner[0] if len(partner) > 1 else partner
                image_1920 = partner.image_1920
                partner_id = partner.id
            if not partner:
                partner_id = False
        # Retrieve the active call by its SID
        if Sid and Sid.startswith('CA'):
            active_call = client.calls(Sid).fetch()
            if active_call:
                call_duration = active_call.duration
                call_status = active_call.status
                # Calculate call duration and formatting
                total_seconds = int(call_duration)
                minutes, seconds = divmod(total_seconds, 60)
                duration_str = f"{minutes:02d}:{seconds:02d}"
                # Retrieve existing record based on call SID
                existing_record = self.env['out.going.call.list'].search([('call_sid', '=', Sid)])
                if existing_record:
                    # Update the existing record with call details
                    recording_url = f"""https://api.twilio.com/2010-04-01/Accounts/{client.recordings.list()[0]
                    .account_sid}/Recordings/{client.recordings.list()[0].sid}.mp3"""
                    existing_record.sudo().write({
                        'status': call_status,
                        'duration': duration_str,
                        'end_time': fields.datetime.now(),
                        'to_number': num,
                        'from_number': from_number,  # Include from_number here
                        'record_sid': recording_url,
                        'image_1920': image_1920,
                        'partner_id': partner_id
                    })
                    existing_record.update({
                        'to_number': num,
                    })
                else:
                    # Create a new record for the call
                    recording_url = f"""https://api.twilio.com/2010-04-01/Accounts/{client.recordings.list()[0]
                    .account_sid}/Recordings/{client.recordings.list()[0].sid}.mp3"""
                    self.env['out.going.call.list'].sudo().create({
                        'from_number': from_number,
                        'to_number': num,
                        'start_time': fields.datetime.now(),
                        'duration': duration_str,
                        'call_sid': Sid,
                        'end_time': fields.datetime.now(),
                        'status': call_status,
                        'record_sid': recording_url,
                        'image_1920': image_1920,
                        'partner_id': partner_id
                    })
                    # Return a success message or perform any other necessary actions
                return "Call details updated successfully."
            else:
                return "No active call found for the specified SID."

    def action_play_recording(self):
        """To play the recordings of the call"""
        if self.record_sid:
            return {
                'type': 'ir.actions.act_url',
                'url': self.record_sid,
                'target': 'new'
            }
        else:
            return False
