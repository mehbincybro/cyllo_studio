from odoo import models, fields


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    def _notify_shopfloor_view(self):
        """Broadcasts a websocket message to shopfloor channel."""
        for record in self:
            self.env['bus.bus']._sendone(
                'shopfloor_channel',
                'workorder_updated',
                {'workcenter_id': record.workcenter_id.id}
            )

    def button_start(self):
        res = super().button_start()
        self._notify_shopfloor_view()
        return res

    def button_pending(self):
        res = super().button_pending()
        self._notify_shopfloor_view()
        return res

    def button_finish(self):
        res = super().button_finish()
        self._notify_shopfloor_view()
        return res

    def button_block(self):
        # 1. Standard pause to stop the active timer
        super().button_pending()

        # 2. Programmatically block the workcenter with a default loss reason to avoid the wizard popup
        # for record in self:
        #     if record.workcenter_id.working_state != 'blocked':
        #         loss_reason = self.env['mrp.workcenter.productivity.loss'].search([], limit=1)
        #         self.env['mrp.workcenter.productivity'].create({
        #             'workcenter_id': record.workcenter_id.id,
        #             'loss_id': loss_reason.id,
        #             'date_start': fields.Datetime.now(),
        #         })

        self._notify_shopfloor_view()
        return True

    def button_unblock(self):
        # Uses the native Odoo unblock method
        res = super().button_unblock()
        self._notify_shopfloor_view()
        return res
