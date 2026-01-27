# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import io

from PIL import Image

from collections import OrderedDict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import is_html_empty
from odoo.tools.pdf import PdfFileWriter, PdfFileReader
from odoo.tools.safe_eval import time


class IrActionsReport(models.Model):
    """Extension of ir.actions.report to enhance rendering and PDF handling."""
    _inherit = 'ir.actions.report'

    def _get_report(self, report_ref):
        """Get the report (with sudo) from a reference
        report_ref: can be one of
            - ir.actions.report id
            - ir.actions.report record
            - ir.model.data reference to ir.actions.report
            - ir.actions.report report_name
        """
        ReportSudo = self.env['ir.actions.report'].sudo()
        if isinstance(report_ref, int):
            return ReportSudo.browse(report_ref)
        if isinstance(report_ref, models.Model):
            if report_ref._name != self._name:
                raise ValueError("Expected report of type %s, got %s" % (self._name, report_ref._name))
            return report_ref.sudo()
        report = ReportSudo.search([('report_name', '=', report_ref)], limit=1)
        if report:
            return report
        report = self.env.ref(report_ref)
        if report:
            if report._name != "ir.actions.report":
                raise ValueError("Fetching report %r: type %s, expected ir.actions.report" % (report_ref, report._name))
            return report.sudo()
        raise ValueError("Fetching report %r: report not found" % report_ref)

    def _render_template(self, template, values=None):
        """Allow to render a QWeb template python-side. This function returns the 'ir.ui.view'
        render but embellish it with some variables/methods used in reports.
        :param values: additional methods/variables used in the rendering
        :returns: html representation of the template2
        :rtype: bytes
        """
        if values is None:
            values = {}

        # Browse the user instead of using the sudo self.env.user
        user = self.env['res.users'].browse(self.env.uid)
        view_obj = self.env['ir.ui.view'].with_context(inherit_branding=False)
        values.update(
            time=time,
            context_timestamp=lambda t: fields.Datetime.context_timestamp(self.with_context(tz=user.tz), t),
            user=user,
            res_company=self.env.company,
            web_base_url=self.env['ir.config_parameter'].sudo().get_param('web.base.url', default=''),
        )
        return view_obj._render_template(template, values).encode()

    def _render_qweb_html(self, report_ref, docids, data=None):
        """Render QWeb report to HTML."""
        if not data:
            data = {}
        data.setdefault('report_type', 'html')
        report = self._get_report(report_ref)

        data = self._get_rendering_context(report, docids, data)
        return self._render_template(report.report_name, data), 'html'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        """Prepare and split PDF streams for the given report."""
        if not data:
            data = {}
        data.setdefault('report_type', 'pdf')

        # access the report details with sudo() but evaluation context as current user
        report_sudo = self._get_report(report_ref)
        has_duplicated_ids = res_ids and len(res_ids) != len(set(res_ids))

        collected_streams = OrderedDict()

        # Fetch the existing attachments from the database for later use.
        # Reload the stream from the attachment in case of 'attachment_use'.
        if res_ids:
            records = self.env[report_sudo.model].browse(res_ids)
            for record in records:
                res_id = record.id
                if res_id in collected_streams:
                    continue

                stream = None
                attachment = None
                if not has_duplicated_ids and report_sudo.attachment and not self._context.get(
                        "report_pdf_no_attachment"):
                    attachment = report_sudo.retrieve_attachment(record)

                    # Extract the stream from the attachment.
                    if attachment and report_sudo.attachment_use:
                        stream = io.BytesIO(attachment.raw)

                        # Ensure the stream can be saved in Image.
                        if attachment.mimetype.startswith('image'):
                            img = Image.open(stream)
                            new_stream = io.BytesIO()
                            img.convert("RGB").save(new_stream, format="pdf")
                            stream.close()
                            stream = new_stream

                collected_streams[res_id] = {
                    'stream': stream,
                    'attachment': attachment,
                }

        # Call 'wkhtmltopdf' to generate the missing streams.
        res_ids_wo_stream = [res_id for res_id, stream_data in collected_streams.items() if not stream_data['stream']]
        all_res_ids_wo_stream = res_ids if has_duplicated_ids else res_ids_wo_stream
        is_whtmltopdf_needed = not res_ids or res_ids_wo_stream

        if is_whtmltopdf_needed:

            if self.get_wkhtmltopdf_state() == 'install':
                # wkhtmltopdf is not installed
                # the call should be catched before (cf /report/check_wkhtmltopdf) but
                # if get_pdf is called manually (email template), the check could be
                # bypassed
                raise UserError(_("Unable to find Wkhtmltopdf on this system. The PDF can not be created."))

            # Disable the debug mode in the PDF rendering in order to not split the assets bundle
            # into separated files to load. This is done because of an issue in wkhtmltopdf
            # failing to load the CSS/Javascript resources in time.
            # Without this, the header/footer of the reports randomly disappear
            # because the resources files are not loaded in time.
            # https://github.com/wkhtmltopdf/wkhtmltopdf/issues/2083
            additional_context = {'debug': False}

            html = \
                self.with_context(**additional_context)._render_qweb_html(report_ref, all_res_ids_wo_stream, data=data)[
                    0]

            bodies, html_ids, header, footer, specific_paperformat_args = self.with_context(
                **additional_context)._prepare_html(html, report_model=report_sudo.model)

            if not has_duplicated_ids and report_sudo.attachment and set(res_ids_wo_stream) != set(html_ids):
                raise UserError(_(
                    "The report's template %r is wrong, please contact your administrator. \n\n"
                    "Can not separate file to save as attachment because the report's template does not contains the"
                    " attributes 'data-oe-model' and 'data-oe-id' on the div with 'article' classname.",
                    report_sudo.name,
                ))

            pdf_content = self._run_wkhtmltopdf(
                bodies,
                report_ref=report_ref,
                header=header,
                footer=footer,
                landscape=self._context.get('landscape'),
                specific_paperformat_args=specific_paperformat_args,
                set_viewport_size=self._context.get('set_viewport_size'),
            )
            pdf_content_stream = io.BytesIO(pdf_content)

            # Printing a PDF report without any records. The content could be returned directly.
            if has_duplicated_ids or not res_ids:
                return {
                    False: {
                        'stream': pdf_content_stream,
                        'attachment': None,
                    }
                }

            # Split the pdf for each record using the PDF outlines.

            # Only one record: append the whole PDF.
            if len(res_ids_wo_stream) == 1:
                collected_streams[res_ids_wo_stream[0]]['stream'] = pdf_content_stream
                return collected_streams

            # In case of multiple docs, we need to split the pdf according the records.
            # In the simplest case of 1 res_id == 1 page, we use the PDFReader to print the
            # pages one by one.
            html_ids_wo_none = [x for x in html_ids if x]
            reader = PdfFileReader(pdf_content_stream)
            if reader.numPages == len(res_ids_wo_stream):
                for i in range(reader.numPages):
                    attachment_writer = PdfFileWriter()
                    attachment_writer.addPage(reader.getPage(i))
                    stream = io.BytesIO()
                    attachment_writer.write(stream)
                    collected_streams[res_ids_wo_stream[i]]['stream'] = stream
                return collected_streams

            # In cases where the number of res_ids != the number of pages,
            # we split the pdf based on top outlines computed by wkhtmltopdf.
            # An outline is a <h?> html tag found on the document. To retrieve this table,
            # we look on the pdf structure using pypdf to compute the outlines_pages from
            # the top level heading in /Outlines.
            if len(res_ids_wo_stream) > 1 and set(res_ids_wo_stream) == set(html_ids_wo_none):
                root = reader.trailer['/Root']
                has_valid_outlines = '/Outlines' in root and '/First' in root['/Outlines']
                if not has_valid_outlines:
                    return {False: {
                        'report_action': self,
                        'stream': pdf_content_stream,
                        'attachment': None,
                    }}

                outlines_pages = []
                node = root['/Outlines']['/First']
                while True:
                    outlines_pages.append(root['/Dests'][node['/Dest']][0])
                    if '/Next' not in node:
                        break
                    node = node['/Next']
                outlines_pages = sorted(set(outlines_pages))

                # The number of outlines must be equal to the number of records to be able to split the document.
                has_same_number_of_outlines = len(outlines_pages) == len(res_ids_wo_stream)

                # There should be a top-level heading on first page
                has_top_level_heading = outlines_pages[0] == 0

                if has_same_number_of_outlines and has_top_level_heading:
                    # Split the PDF according to outlines.
                    for i, num in enumerate(outlines_pages):
                        to = outlines_pages[i + 1] if i + 1 < len(outlines_pages) else reader.numPages
                        attachment_writer = PdfFileWriter()
                        for j in range(num, to):
                            attachment_writer.addPage(reader.getPage(j))
                        stream = io.BytesIO()
                        attachment_writer.write(stream)
                        collected_streams[res_ids_wo_stream[i]]['stream'] = stream

                    return collected_streams

            collected_streams[False] = {'stream': pdf_content_stream, 'attachment': None}

        return collected_streams

    def _get_rendering_context(self, report, docids, data):
        """Build and return rendering context for a report."""
        # If the report is using a custom model to render its html, we must use it.
        # Otherwise, fallback on the generic html rendering.
        report_model = self._get_rendering_context_model(report)

        data = data and dict(data) or {}

        if report_model is not None:
            data.update(report_model._get_report_values(docids, data=data))
        else:
            docs = self.env[report.model].browse(docids)
            data.update({
                'doc_ids': docids,
                'doc_model': report.model,
                'docs': docs,
            })
        data['is_html_empty'] = is_html_empty
        return data

    def get_values(self):
        """Return metadata of available reports."""
        reports = self.search([])
        test = self.search_read([])
        for tes in reports:
            qweb_view = self.env['ir.ui.view'].search([('xml_id', '=', tes.report_name)])
        return [{'id': rec.id, 'name': rec.name, 'model_id': rec.model_id, 'model': rec.model,
                 'report_name': rec.report_name} for rec in reports]

    @api.model
    def get_qweb(self, data):
        """Return QWeb templates related to a report."""
        qweb_code = self.env['ir.ui.view'].search(
            [('name', 'ilike', data['report_name'].split('.')[1]), ('type', '=', 'qweb')])
        return [{'arch': views.arch} for views in qweb_code]
