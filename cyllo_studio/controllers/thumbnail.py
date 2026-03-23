# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class ReportThumbnailController(http.Controller):
    @http.route('/cyllo_studio/save_report_thumbnail', type='json', auth='user')
    def save_report_thumbnail(self, report_id=None, report_name=None, image_base64=None, **kwargs):
        """
        Save a base64 image as the thumbnail for a specific report.
        """
        print("[Cyllo Studio] save_report_thumbnail called for report_id:", report_id, " name:", report_name)
        if not image_base64:
            print("[Cyllo Studio] Missing image data")
            return {'success': False, 'error': 'Missing image data'}
        
        # Remove data:image uri prefix if present
        if 'base64,' in image_base64:
            image_base64 = image_base64.split('base64,')[1]
            
        Report = request.env['ir.actions.report'].sudo()
        report = False
        if report_id:
            report = Report.browse(int(report_id)).exists()
        
        if not report and report_name:
            report = Report.search([('report_name', '=', report_name)], limit=1)
            
        if report:
            print("[Cyllo Studio] Found report record:", report.name, " (ID:", report.id, ")")
            try:
                report.write({'report_thumbnail': image_base64})
                print("[Cyllo Studio] Successfully saved thumbnail.")
                return {'success': True}
            except Exception as e:
                print("[Cyllo Studio] Failed to save thumbnail:", str(e))
                return {'success': False, 'error': str(e)}
        
        print("[Cyllo Studio] Report record NOT found")
        return {'success': False, 'error': 'Report not found'}
