# -*- coding: utf-8 -*-
from odoo import tools, fields, models


class AssetReport(models.Model):
    _name = "asset.report"
    _description = "Asset Activity Analysis"
    _auto = False
    _rec_name = "asset_id"

    asset_id = fields.Many2one('asset.asset', string="Asset", readonly=True)
    activity_type = fields.Selection([
        ('maintenance', 'Maintenance'),
        ('lease', 'Lease'),
        ('rent', 'Rental'),], string="Activity Type", readonly=True)
    activity_count = fields.Integer(string="Count", readonly=True)
    original_value = fields.Float(string="Original Value", readonly=True)
    salvage_value = fields.Float(string="Salvage Value", readonly=True)

    def init(self):
        """Drop the existing SQL view (if any) and recreate it for the asset activity report."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER() AS id,
                    a.id AS asset_id,
                    'lease' AS activity_type,
                    COUNT(l.id) AS activity_count,
                    a.original_value,
                    a.salvage_value
                FROM asset_asset a
                LEFT JOIN asset_lease l
                    ON l.asset_id = a.id
                GROUP BY a.id, a.original_value, a.salvage_value
                UNION ALL
                SELECT
                    row_number() OVER() + 10000 AS id,
                    a.id AS asset_id,
                    'rent' AS activity_type,
                    COUNT(r.id) AS activity_count,
                    a.original_value,
                    a.salvage_value
                FROM asset_asset a
                LEFT JOIN asset_rental r
                    ON r.asset_id = a.id
                GROUP BY a.id, a.original_value, a.salvage_value
                UNION ALL
                SELECT
                    row_number() OVER() + 20000 AS id,
                    a.id AS asset_id,
                    'maintenance' AS activity_type,
                    COUNT(m.id) AS activity_count,
                    a.original_value,
                    a.salvage_value
                FROM asset_asset a
                LEFT JOIN maintenance_request m
                    ON m.asset_id = a.id
                GROUP BY a.id, a.original_value, a.salvage_value
            )""" % self._table)