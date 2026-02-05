# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AssetReservation(models.Model):
    """Model for reserving the assets"""
    _name = 'asset.reservation'
    _description = 'Reserve the Assets'
    _rec_name = 'asset_id'
    _inherit = ['mail.thread']

    asset_id = fields.Many2one('asset.asset', required=True)
    start_date = fields.Date(string="Period", required=True, tracking=True)
    end_date = fields.Date(string="End", required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    reservation_note = fields.Text(string="Notes")
    email = fields.Char(related='employee_id.work_email')
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company, help='Select the company')
    date = fields.date.today()
    status = fields.Selection(
        [('draft', 'Draft'), ('reserve', 'Reserve'), ('assign', 'Assign'), ('lease', 'Lease'), ('rent', 'Rent'),
         ('cancel', 'Cancel')], default='draft', tracking=True, copy=False)
    active = fields.Boolean(default=True)

    @api.onchange('start_date', 'end_date')
    def _onchange_reservation_date(self):
        """Function for checking starting and ending date"""
        purchase_date = self.asset_id.date
        if self.start_date and self.end_date and purchase_date:
            if self.end_date < self.start_date:
                raise UserError(_('The End Date should be greater than the Start Date'))
            elif (self.start_date < purchase_date) or (self.end_date < purchase_date):
                raise UserError(
                    _(f'The Asset is Purchased on {purchase_date}. The Start Date and End Date should be greater than the Purchase Date'))

    def unlink(self):
        """Function for unlink the records"""
        for rec in self:
            if rec.status == 'reserve':
                raise UserError(_('You cannot delete the record that is in Reserved state.'))
        else:
            self.asset_id.is_reserve = False
            return super().unlink()

    def action_reserve(self):
        """Button action for reserving the assets"""
        if self.asset_id.is_reserve:
            raise UserError(_('You cannot complete this operation, The related asset is already Reserved.'))
        open_requests = self.env['maintenance.request'].sudo().search([('asset_id', '=', self.asset_id.id),
                                                                       ('stage_done', '=', False), ])
        if open_requests:
            raise UserError(
                _('You cannot complete this operation, The related asset is already taken for a another '
                  'operation'))
        else:
            context = {
                'asset': self.asset_id.name,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'employee': self.employee_id.name
            }
            template = self.env.ref(
                'cyllo_asset_management.mail_template_asset_reservation',
                raise_if_not_found=False)
            email_values = {
                'email_to': self.email
            }
            template.with_context(**context).send_mail(res_id=self.id, email_values=email_values, force_send=True)
            self.asset_id.is_reserve = True
            self.asset_id.status = 'reserved'
            self.status = 'reserve'
            return {'type': 'ir.actions.act_window_close'}

    def action_assign_asset(self):
        """Button action for assigning the assets"""
        return {
            'name': _('Assign'),
            'view_id': self.env.ref('cyllo_asset_management.view_asset_assign_form2').id,
            'view_mode': 'form',
            'res_model': 'asset.assign',
            'type': 'ir.actions.act_window',
            'context': {
                'default_asset_id': self.asset_id.id,
                'default_employee_id': self.employee_id.id,
                'default_reservation_id': self.id,
            },
            'target': 'new'
        }

    def action_lease_asset(self):
        """Button action for leasing the assets"""
        if not self.asset_id.is_lease_asset:
            raise UserError(_('You cannot complete this operation, The related asset is not a lease asset.'))
        return {
            'name': _('Lease'),
            'view_id': self.env.ref('cyllo_asset_management.view_asset_lease_form2').id,
            'view_mode': 'form',
            'res_model': 'asset.lease',
            'type': 'ir.actions.act_window',
            'context': {
                'default_asset_id': self.asset_id.id,
                'default_customer_id': self.employee_id.work_contact_id.id,
                'default_reservation_id': self.id
            },
            'target': 'new'
        }

    def action_rental_asset(self):
        """Button action for rental the assets"""
        if not self.asset_id.is_rental_asset:
            raise UserError(_('You cannot complete this operation, The related asset is not a rental asset.'))
        return {
            'name': _('Rental'),
            'view_id': self.env.ref('cyllo_asset_management.view_asset_rental_form2').id,
            'view_mode': 'form',
            'res_model': 'asset.rental',
            'type': 'ir.actions.act_window',
            'context': {
                'default_asset_id': self.asset_id.id,
                'default_customer_id': self.employee_id.work_contact_id.id,
                'default_reservation_id': self.id
            },
            'target': 'new'
        }

    def action_unreserve(self):
        """Button action for unreserving the assets"""
        asset_id=self.sudo().asset_id
        self.status = 'cancel'
        asset_id.is_reserve = False
        if asset_id.is_confirm == True:
            asset_id.status = 'running'
        else:
            asset_id.status = 'draft'

    def action_reset_to_draft(self):
        """Button action for reset the records to draft  state"""
        if self.asset_id.status in ('sell', 'disposed', 'cancel', 'lost', 'rented'):
            raise UserError(_(f'You cannot reset to draft.The related asset is in {self.asset_id.status} state.'))
        self.status = 'draft'
