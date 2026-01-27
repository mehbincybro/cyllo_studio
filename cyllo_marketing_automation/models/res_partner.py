# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import ValidationError


class ResUser(models.Model):
    """Inherited module res.partner to add methods"""
    _inherit = 'res.partner'

    def unlink(self):
        """Preventing the deletion of the record which is a participant """
        records = self.env['marketing.participant'].search([])
        for rec in records:
            if rec.record_id == self.id:
                raise ValidationError(_("You can not delete a partner which is a participant \n "
                                        "in a Marketing Campaign"))
        return super().unlink()
