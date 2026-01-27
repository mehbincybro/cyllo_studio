# -*- coding: utf-8 -*-
from odoo import models


class BarcodeDataReport(models.AbstractModel):
    """ Barcode Data Report"""
    _name = "report.cyllo_barcode.barcode_data_report"
    _description = "Cyllo Barcode Pdf Report"

    def _get_report_values(self, docids, data):
        """Return report datas"""
        model = data.get('mode')
        data = {
            'mode': model,
        }
        if model == 'product.product':
            data['items'] = self.env[model].search_read([], ['name', 'barcode'])
        elif model == 'stock.picking.type':
            data['items'] = self.env[model].search_read([], ['name', 'barcode'])
        elif model == 'stock.location':
            data['items'] = self.env['stock.location'].search_read([("usage", "=", "internal")], ['name', 'barcode'])
        return data
