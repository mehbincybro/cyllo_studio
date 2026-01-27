# -*- coding: utf-8 -*-
from odoo import fields, models


class IrAttachment(models.Model):
    """
        Extends the base ir.attachment model to add a field for storing
        Instagram public URLs for attachments.
    """
    _inherit = "ir.attachment"

    public_url = fields.Char(string="Url", compute="_compute_public_url", help="Url for the attachment")

    def _compute_public_url(self):
        """
        Computes the Instagram public URL for each attachment record.
        """
        for attachment in self:
            attachment.public_url = '%s/web/content/%s' % (attachment.get_base_url(), attachment.id)
