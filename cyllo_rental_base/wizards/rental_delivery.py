# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import ValidationError


class RentalDelivery(models.TransientModel):
    """ Pickup wizard """
    _name = 'rental.delivery'
    _description = 'Rental Delivery wizard'

    rental_id = fields.Many2one(string='Name', comodel_name='rental.order', help="Pickup product and details")
    rental_line_ids = fields.One2many(comodel_name='rental.delivery.line', inverse_name='delivery_id',
                                      help="Pickup product and details")

    def action_create_delivery(self):
        """Create a new delivery """
        if self.rental_line_ids:
            picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'outgoing'),
                                                                     ('company_id', '=', self.env.company.id)], limit=1)
            pickup = self.env['stock.picking'].sudo().create([{
                'partner_id': self.rental_id.partner_shipping_id.id,
                'picking_type_id': picking_type_id.id,
                'rental_id': self.rental_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'origin': self.rental_id.name,
                'state': 'draft',
            }])
            for line in self.rental_line_ids:
                line_id = line.line_id
                if line.product_id.is_extra_cost:
                    self.rental_id.is_extra_cost = True
                source_location = line.product_location_id
                availability = self.rental_id.check_product_availability(source_location, line.product_id)
                if not availability:
                    raise ValidationError(_(f"{line.product_id.name} not available in {source_location.display_name}"))
                dest_location = self.env.ref('stock.stock_location_customers')
                pickup.update({'move_ids': [fields.Command.create({
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'name': line.product_id.name,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_uom_id.id,
                    'location_id': source_location.id,
                    'location_dest_id': dest_location.id,
                })], })
                line.line_id.qty_delivered += line.quantity
                if line_id.product_uom_qty == line_id.qty_delivered:
                    line_id.is_picked = True
                if all(line.is_picked for line in self.rental_id.order_line_ids):
                    self.rental_id.is_picked_up = True
                pickup.move_ids.write({'lot_ids': [fields.Command.set(line.line_id.lot_ids.ids)]})
                line.line_id.pickup_id = pickup.id

            self.rental_id.picking_ids = [fields.Command.link(pickup.id)]
            self.rental_id.can_be_returned = True
            mail_template = self.env.ref('cyllo_rental_base.mail_template_pickup_mail_notify')
            mail_template['email_from'] = self.env.user.email
            mail_template['email_to'] = self.rental_id.partner_id.email
            mail_template.send_mail(self.rental_id.id, force_send=True)
            return {
                'type': 'ir.actions.act_window',
                'target': 'self',
                'name': pickup.name,
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'res_id': pickup.id,
            }


class RentalDeliveryLine(models.TransientModel):
    """ Pickup wizard lines """
    _name = 'rental.delivery.line'
    _description = 'Rental Delivery Line'

    delivery_id = fields.Many2one('rental.delivery', string='Order Delivery',
                                  help="Corresponding Delivery order")
    product_id = fields.Many2one('product.product', help="Product to pickup")
    line_id = fields.Many2one('rental.order.line')
    product_uom_id = fields.Many2one('uom.uom', string="Unit of Measure")
    quantity = fields.Integer(help="Product quantity")
    product_location_id = fields.Many2one('stock.location', help="Location of the product")
