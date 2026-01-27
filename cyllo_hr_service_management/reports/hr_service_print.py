# -*- coding: utf-8 -*-
from odoo import api, models


class HrServicePrint(models.AbstractModel):
    """class to print form view"""
    _name = 'report.cyllo_hr_service_management.hr_service_report_document'
    _description = 'Hr service request form report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """function to print form view"""
        return {
            'hr_service_request': self.env['hr.service'].browse(docids),
        }
