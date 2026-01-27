# -*- coding: utf-8 -*-
from odoo import models


class ResConfigSettings(models.TransientModel):
    """
    Class ResConfigSettings used to print barcode of the location, products and
    inventory commands
    """
    _inherit = 'res.config.settings'

    def action_print_barcode(self):
        """Action for printing different barcodes of the locations, product and
        inventory commands"""
        if self.env.context.get('model') == 'product.product':
            report_name = "Products"
        elif self.env.context.get('model') == 'stock.picking.type':
            report_name = "Operation Types"
        elif self.env.context.get('model') == 'stock.location':
            report_name = "Locations"
        else:
            report_name = "Inventory Commands"
        report = self.env.ref('cyllo_barcode.report_barcode_pdf_download')
        report.name = 'Barcode of ' + report_name
        return (self.env.ref('cyllo_barcode.report_barcode_pdf_download').
                report_action(self, data={'mode': self.env.context.get('model')}))
