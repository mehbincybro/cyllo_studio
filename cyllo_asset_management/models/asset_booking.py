from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta


class AssetBooking(models.Model):
    _name = 'asset.booking'
    _order = 'date_from'

    asset_id = fields.Many2one('asset.asset', required=True)
    booking_type = fields.Selection([
        ('maintenance', 'Maintenance'),
        ('lease', 'Lease'),
        ('rental', 'Rental'),
    ], required=True)

    date_from = fields.Datetime(required=True)
    date_to = fields.Datetime(required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], default='draft')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company,
                                 help='Select the company')
    partner_id = fields.Many2one('res.partner')
    res_model = fields.Char(index=True)
    res_id = fields.Integer(index=True)

    def write(self, vals):
        if vals.get('state') != 'confirmed':
            return super().write(vals)
        for booking in self:
            conflict = self.search([('asset_id', '=', booking.asset_id.id), ('state', '=', 'confirmed'),
                                    ('id', '!=', booking.id), ], limit=1)
            if conflict:
                raise ValidationError(_("Asset '%s' already has a confirmed booking (%s → %s). "
                                        "Only one confirmed booking is allowed."
                                        ) % (booking.asset_id.display_name, conflict.date_from, conflict.date_to,))
        return super().write(vals)

    def _get_buffered_end(self, asset, date_to):
        """Return date_to extended by asset buffer"""
        if not asset.buffer_duration:
            return date_to
        if asset.buffer_period == 'hour':
            return date_to + timedelta(hours=asset.buffer_duration)
        elif asset.buffer_period == 'day':
            return date_to + timedelta(days=asset.buffer_duration)
        elif asset.buffer_period == 'week':
            return date_to + timedelta(weeks=asset.buffer_duration)

        return date_to

    def _check_overlap(self, asset_id, date_from, date_to, exclude_id=False):
        asset = self.env['asset.asset'].browse(asset_id)
        buffered_date_to = self._get_buffered_end(asset, date_to)
        domain = [('asset_id', '=', asset_id), ('state', 'in', ['draft', 'confirmed']),
                  ('date_from', '<', buffered_date_to), ('date_to', '>', date_from), ]
        if exclude_id:
            domain.append(('id', '!=', exclude_id))
        if self.search_count(domain):
            raise ValidationError(_('Asset is not available due to cooldown period.'))

    @api.model
    def create_or_update_booking(self, *, asset, date_from, date_to,
                                 booking_type, partner=None, res_model=None, res_id=None):
        booking = self.search([('res_model', '=', res_model), ('res_id', '=', res_id), ], limit=1)
        self._check_overlap(
            asset.id, date_from, date_to,
            exclude_id=booking.id if booking else False
        )
        vals = {
            'asset_id': asset.id,
            'booking_type': booking_type,
            'date_from': date_from,
            'date_to': date_to,
            'partner_id': partner.id if partner else False,
            'res_model': res_model,
            'res_id': res_id,
            'state': 'draft',
        }
        return booking.write(vals) and booking if booking else self.create(vals)
