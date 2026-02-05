from odoo import _, api, fields, models


class AssetAssetInsurance(models.Model):
    """Model for assigning the assets"""
    _name = 'asset.asset.insurance'
    _description = 'Asset Insurance'
    _rec_name = 'name'

    name = fields.Char(compute="_compute_name", store=True)
    partner_id = fields.Many2one('res.partner',string="Insurance Provider")
    type = fields.Char(string="Insurance Type")

    @api.depends('partner_id', 'type')
    def _compute_name(self):
        """function for assigning the name of insurance based on provider and type"""
        for record in self:
            if record.partner_id and record.type:
                record.name = f"{record.partner_id.name} ({record.type})"
            else:
                record.name = False
