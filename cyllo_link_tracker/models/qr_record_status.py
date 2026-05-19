# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class QrRecordStatus(models.Model):
    """
    SQL View: one row per (qr.download.token × record_id).
    Aggregates scan events to show status per record across all models.
    """
    _name = 'qr.record.status'
    _description = 'QR Code Status per Record'
    _auto = False
    _rec_name = 'record_name'
    _order = 'record_name, token_name'

    token_id = fields.Many2one('qr.download.token', string='QR Token', readonly=True)
    token_name = fields.Char(string='Token Name', readonly=True)
    report_name = fields.Char(string='Report', readonly=True)
    record_id = fields.Integer(string='Record ID', readonly=True)
    record_name = fields.Char(string='Record Name', readonly=True)
    is_scanned = fields.Boolean(string='Scanned', readonly=True)
    scan_count = fields.Integer(string='Scan Count', readonly=True)
    last_scanned_at = fields.Datetime(string='Last Scanned At', readonly=True)
    track_analytics = fields.Boolean(string='Analytics On', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW qr_record_status AS (
                SELECT
                    MIN(se.id)                      AS id,
                    t.id                            AS token_id,
                    'Token #' || t.id::VARCHAR      AS token_name,
                    rpt.name->>'en_US'              AS report_name,
                    se.record_id                    AS record_id,
                    se.record_reference             AS record_name,
                    TRUE                            AS is_scanned,
                    COUNT(se.id)                    AS scan_count,
                    MAX(se.scanned_at)              AS last_scanned_at,
                    t.track_analytics               AS track_analytics
                FROM qr_scan_event se
                JOIN qr_download_token t ON t.id = se.token_id
                JOIN ir_act_report_xml rpt ON rpt.id = t.report_id
                GROUP BY t.id, rpt.name, se.record_id, se.record_reference, t.track_analytics
            )
        """)
