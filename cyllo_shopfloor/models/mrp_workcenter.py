from odoo import models, fields


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    def button_block_custom(self):
        """Silently blocks the workcenter with an actual blocking reason"""
        for record in self:
            if record.working_state != 'blocked':
                # FIX: Explicitly search for a loss reason that is NOT productive
                loss_reason = self.env['mrp.workcenter.productivity.loss'].search(
                    [('loss_type', '!=', 'productive')], limit=1
                )

                # Fallback if no specific loss reason is found
                if not loss_reason:
                    loss_reason = self.env['mrp.workcenter.productivity.loss'].search([], limit=1)

                self.env['mrp.workcenter.productivity'].create({
                    'workcenter_id': record.id,
                    'loss_id': loss_reason.id,
                    'date_start': fields.Datetime.now(),
                    'company_id': record.company_id.id
                })

        # Broadcast update to all tablets
        self.env['bus.bus']._sendone('shopfloor_channel', 'workorder_updated', {'workcenter_id': self.id})
        return True

    def unblock_custom(self):
        """Unblocks and broadcasts the update"""
        self.unblock()  # Standard Odoo method ends the productivity loss
        for record in self:
            self.env['bus.bus']._sendone('shopfloor_channel', 'workorder_updated', {'workcenter_id': record.id})
        return True