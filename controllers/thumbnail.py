# -*- coding: utf-8 -*-
import base64
import fitz
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

    @http.route('/cyllo_studio/generate_report_thumbnail', type='json', auth='user')
    def generate_report_thumbnail(self, report_id=None, record_id=None, **kwargs):
        """
        Generate a thumbnail by rendering the report PDF and converting the first page to an image.
        """
        if not report_id or not record_id:
            return {'success': False, 'error': 'Missing report_id or record_id'}

        Report = request.env['ir.actions.report'].sudo()
        report = Report.browse(int(report_id)).exists()

        if not report:
            return {'success': False, 'error': 'Report not found'}

        try:
            # 1. Generate PDF using Odoo's native QWeb engine
            pdf_content, _ = report.with_context(
                report_pdf_no_attachment=True,
                cyllo_studio_pdf=True,
            )._render_qweb_pdf(report_id, [record_id])

            # 2. Convert to Image using PyMuPDF (fitz)
            doc = fitz.open("pdf", pdf_content)
            page = doc.load_page(0)
            
            # Scale down for thumbnail
            zoom = 0.5  # 50% scale
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Get JPEG data
            img_data = pix.tobytes("jpeg", jpg_quality=70)
            
            # Encode base64
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            # 3. Save to report
            report.write({'report_thumbnail': img_base64})
            
            return {'success': True}
        except Exception as e:
            print(f"[Cyllo Studio] Failed to generate thumbnail server-side: {e}")
            return {'success': False, 'error': str(e)}
