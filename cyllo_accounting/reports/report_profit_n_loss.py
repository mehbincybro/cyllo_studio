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
import json
import xlsxwriter

from odoo import api, models


class PnlReport(models.AbstractModel):
    """
    Abstract model for generating a Profit and Loss Report.

    This model serves as a template for creating specific Profit and Loss reports.

    Attributes:
        _name (str): The technical name of the model ('report.pnl_report').
        _description (str): A brief description of the model ('Profit and Loss Report').
    """
    _name = "report.cyllo_accounting.report_profit_n_loss"
    _description = "Report Cyllo Accounting Report PNL"

    @api.model
    def _get_report_values(self, docids, data=None):
        """
           Retrieves the necessary data for generating the Profit and Loss report.

           This method is called by the report engine to fetch the required data for rendering the report.

           Args:
               docids (list): A list of document IDs (not used in this case).
               data (dict): A dictionary containing the report parameters, such as the report name, filter data, filter by, periods, comparison, and comparison type.

           Returns:
               dict: A dictionary containing the report data, including the periods, filter by, PDF data, report name, comparison, comparison type, journal names, account names, analytic account names, and the currency symbol.
        """
        report_name = data.get('reportName', "")
        filter_data = data.get('filterData', {})
        filter_by = data.get('filterBy', "")
        periods = data.get('periods', {})
        comparison = filter_data.get('comparison_value', 1)
        comparison_type = filter_data.get('comparison_type_value', 'month')
        journals = [self.env['account.journal'].browse(rec).name for rec in data['filterData']['journal_ids']]
        accounts = [self.env['account.account'].browse(rec).name for rec in data['filterData']['account_ids']]
        account_analytic = [self.env['account.analytic.account'].browse(rec).name for rec in
                            data['filterData']['analytic_ids']]
        pdf_data = self.env["abstract.financial.report"].get_report(comparison, comparison_type, **filter_data)
        currency_symbol = [item['currency_symbol'] for item in pdf_data[0]]
        return {
            'doc_ids': docids,
            'doc_model': 'report.cyllo_accounting.report_profit_n_loss',
            'periods': periods,
            'filter_by': filter_by,
            'pdf_data': pdf_data,
            'report_name': report_name,
            'comparison': comparison,
            'comparison_type': comparison_type,
            'journals': journals,
            'accounts': accounts,
            'account_analytic': account_analytic,
            'data': data,
            'currency_symbol': currency_symbol,
            'self': self
        }

    def get_account_lines(self, filter_key, data):
        """
            Retrieves the account lines based on the specified filter key.

            Args:
                filter_key (str): The key to use for filtering the data.
                data (list): The data to be filtered.

            Returns:
                list: The filtered account lines, or an empty list if all amounts are zero.
        """
        values = [item[filter_key] for item in data[0]]
        should_have_data = any(item[filter_key][2] != 0 for item in data[0])
        return values if should_have_data else []

    def get_account_line(self, account_id, account_lines):
        """
            Retrieves the account line information for the specified account ID.

            Args:
                account_id (str or dict): The ID of the account to retrieve the line for.
                account_lines (list): The full account lines data.

            Returns:
                list: The account line information, or an empty list if the amount is zero.
        """
        account_info = [acc for sublist in account_lines for acc in sublist[0] if acc['id'] == account_id]
        return account_info if any(item['amount'] != 0 for item in account_info) else []

    @api.model
    def get_xlsx_report(self, data, response, report_name):
        """
            Generate an Excel report based on the provided data.

            Args:
                data (str): JSON string containing filter data.
                response: Response object to write the Excel file to.
                report_name (str): Name of the report.

            Returns:
                None
        """
        symbol = ''
        data = json.loads(data)
        filter_data = data['filterData']
        comparison = filter_data.get('comparison_value', 1)
        comparison_type = filter_data.get('comparison_type_value', 'month')
        pdf_data = self.env["abstract.financial.report"].get_report(comparison, comparison_type, **filter_data)

        start_date = data['filterData']['start_date'] if \
            data['filterData']['start_date'] else ''
        end_date = data['filterData']['end_date'] if \
            data['filterData']['end_date'] else ''
        journals = [self.env['account.journal'].browse(rec).name for rec in
                    data['filterData']['journal_ids']]
        account_analytic = [
            self.env['account.analytic.account'].browse(rec).name for rec in
            data['filterData']['analytic_ids']]

        account_names = self.env['account.account'].browse(
            data['filterData']['account_ids']).mapped('name') if data['filterData']['account_ids'] else []

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format(
            {'font_size': 15, 'align': 'center', 'bold': True})
        sub_heading = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px',
             'border': 1,
             'border_color': 'black'})
        filter_head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px',
             'border': 1, 'bg_color': '#D3D3D3',
             'border_color': 'black'})
        filter_body = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px'})
        side_heading_sub = workbook.add_format(
            {'align': 'left', 'bold': True, 'font_size': '10px',
             'border': 1,
             'border_color': 'black'})
        side_heading_sub.set_indent(1)
        txt_name = workbook.add_format({'font_size': '10px', 'border': 1})

        txt_name.set_indent(2)
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, len(data['periods']) * 2 + 4, 18)
        sheet.write('B1:D1', data['reportName'], head)
        sheet.write('B3:b4', 'Date Range', filter_head)
        sheet.write('B4:b4', 'Comparison', filter_head)
        sheet.write('B5:b4', 'Journal', filter_head)
        sheet.write('B6:b4', 'Account', filter_head)
        sheet.write('B7:b4', 'Analytic Account', filter_head)
        sheet.write('B8:b4', 'Option', filter_head)
        if report_name:
            sheet.merge_range('B1:D1', report_name,
                              head)
        if start_date or end_date:
            sheet.merge_range('C3:G3', f"{start_date} to {end_date}",
                              filter_body)
        if data['filterData']['comparison_value']:
            sheet.merge_range('C4:G4',
                              f"{data['filterData']['comparison_type_value']} : {data['filterData']['comparison_value']}",
                              filter_body)
        if journals:
            display_names = [journal for
                             journal in journals]
            display_names_str = ', '.join(display_names)
            sheet.merge_range('C5:G5', display_names_str, filter_body)
        sheet.merge_range('C6:G6', ', '.join(account_names), filter_body)
        if account_analytic:
            account_keys = [account for
                            account in account_analytic]
            account_keys_str = ', '.join(account_keys)
            sheet.merge_range('C7:G7', account_keys_str, filter_body)
        if data['filterData']['target_move']:
            option_keys = list(data['filterData']['target_move'])
            option_keys_str = ', '.join(option_keys)
            sheet.merge_range('C8:G8', option_keys_str, filter_body)

        rows = 11
        cols = 0
        if report_name == 'Profit and Loss':
            for periods in data['periods']:
                cols = cols + 1
                sheet.write(rows, cols + 1, periods, sub_heading)
                sheet.write(12, cols + 1, "Balance", sub_heading)
            cols = 0
            rows = 13
            for data in pdf_data[0]:
                symbol = data['currency_symbol']
                cols = cols + 1
                sheet.write(rows + 1, cols + 1, f"{data['currency_symbol']} {data['total']}")
                sheet.write(rows + 2, cols + 1, f"{data['currency_symbol']}{data['total_income']}")
                sheet.write(rows + 3, cols + 1, f"{data['currency_symbol']}{data['gross_profit']}")
                sheet.write(rows + 4, cols + 1, f"{data['currency_symbol']}{data['income'][1]}")
            sheet.write(rows + 1, 0, 'Net Profit', sub_heading)
            sheet.write(rows + 2, 0, 'Income', side_heading_sub)
            sheet.write(rows + 3, 0, 'Gross Profit')
            sheet.write(rows + 4, 0, 'Operating Income')
            account_lines = self.get_account_lines('income', pdf_data)
            rows = 18
            cols = 0
            for account in account_lines[0][0] if account_lines else []:
                accAmountIncome = self.get_account_line(account['id'], account_lines)
                if len(accAmountIncome):
                    sheet.write(rows, 0, f"{account['name']}", txt_name)
                    for amountIncome in accAmountIncome:
                        cols = cols + 1
                        sheet.write(rows, cols + 1, f"{symbol}{amountIncome['format_amount']}")

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Cost Of Revenue')
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']}{data['expense_direct_cost'][1]}")
            account_lines = self.get_account_lines('expense_direct_cost', pdf_data)
            if len(account_lines) != 0:
                for account in account_lines[0][0]:
                    accAmountIncome = self.get_account_line(account['id'], account_lines)
                    if len(accAmountIncome):
                        rows += 1
                        sheet.write(rows, 0, f"{account['name']}", txt_name)
                        for amountIncome in accAmountIncome:
                            sheet.write(rows, cols + 1, f"{symbol}{amountIncome['format_amount']}")
            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Other Income')
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']}{data['income_other'][1]}")
            account_lines = self.get_account_lines('income_other', pdf_data)
            if len(account_lines) != 0:
                for account in account_lines[0][0]:
                    accAmountIncome = self.get_account_line(account['id'], account_lines)
                    if len(accAmountIncome):
                        rows += 1
                        sheet.write(rows, 0, f"{account['name']}", txt_name)
                        for amountIncome in accAmountIncome:
                            sheet.write(rows, cols + 1, f"{symbol}{amountIncome['format_amount']}")
            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Total Income', side_heading_sub)
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']}{data['total_income']}")
            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Expenses', side_heading_sub)
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']}{data['total_expense']}")
            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Expenses')
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']}{data['expense'][1]}")
            account_lines = self.get_account_lines('expense', pdf_data)
            if len(account_lines) != 0:
                for account in account_lines[0][0]:
                    accAmountIncome = self.get_account_line(account['id'], account_lines)
                    if len(accAmountIncome):
                        rows += 1
                        sheet.write(rows, 0, f"{account['name']}", txt_name)
                        for amountIncome in accAmountIncome:
                            sheet.write(rows, cols + 1, f"{symbol}{amountIncome['format_amount']}")
            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Depreciation')
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']}{data['expense_depreciation'][1]}")
            account_lines = self.get_account_lines('expense_depreciation', pdf_data)
            if len(account_lines) != 0:
                for account in account_lines[0][0]:
                    accAmountIncome = self.get_account_line(account['id'], account_lines)
                    if len(accAmountIncome):
                        rows += 1
                        sheet.write(rows, 0, f"{account['name']}", txt_name)
                        for amountIncome in accAmountIncome:
                            sheet.write(rows, cols + 1, f"{symbol}{amountIncome['format_amount']}")
            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Total Expenses', side_heading_sub)
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']}{data['total_expense']}")
        elif report_name == "Balance Sheet":
            cols = 0
            rows = 10
            for periods in data['periods']:
                cols = cols + 1
                sheet.write(rows, cols + 1, periods, sub_heading)
                sheet.write(11, cols + 1, "Balance", sub_heading)
            sheet.write(12, 0, 'ASSETS', sub_heading)
            sheet.write(13, 0, 'Current Assets', side_heading_sub)
            sheet.write(14, 0, 'Bank and Cash Accounts')
            cols = 0
            rows = 14
            for data in pdf_data[0]:
                symbol = data['currency_symbol']
                cols = cols + 1
                sheet.write(14, cols + 1, f"{data['currency_symbol']} {data['asset_cash'][1]}")
            account_lines = self.get_account_lines('asset_cash', pdf_data)
            if len(account_lines) != 0:
                for account in account_lines[0][0]:
                    accAmountIncome = self.get_account_line(account['id'], account_lines)
                    if len(accAmountIncome):
                        rows += 1
                        sheet.write(rows, 0, f"{account['name']}", txt_name)
                        for amountIncome in accAmountIncome:
                            sheet.write(rows, cols + 1, f"{symbol}{amountIncome['format_amount']}")
            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Receivables')
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']} {data['asset_receivable'][1]}")
            account_lines = self.get_account_lines('asset_receivable', pdf_data)
            if len(account_lines) != 0:
                for account in account_lines[0][0]:
                    accAmountIncome = self.get_account_line(account['id'], account_lines)
                    if len(accAmountIncome):
                        rows += 1
                        sheet.write(rows, 0, f"{account['name']}", txt_name)
                        for amountIncome in accAmountIncome:
                            sheet.write(rows, cols + 1, f"{symbol}{amountIncome['format_amount']}")

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Current Assets')
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']} {data['asset_current'][1]}")
            account_lines = self.get_account_lines('asset_current', pdf_data)
            if len(account_lines) != 0:
                for account in account_lines[0][0]:
                    accAmountIncome = self.get_account_line(account['id'], account_lines)
                    if len(accAmountIncome):
                        rows += 1
                        sheet.write(rows, 0, f"{account['name']}", txt_name)
                        for amountIncome in accAmountIncome:
                            sheet.write(rows, cols + 1, f"{symbol}{amountIncome['format_amount']}")

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Prepayments')
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']} {data['asset_prepayments'][1]}")
            account_lines = self.get_account_lines('asset_prepayments', pdf_data)
            if len(account_lines) != 0:
                for account in account_lines[0][0]:
                    accAmountIncome = self.get_account_line(account['id'], account_lines)
                    if len(accAmountIncome):
                        rows += 1
                        sheet.write(rows, 0, f"{account['name']}", txt_name)
                        for amountIncome in accAmountIncome:
                            sheet.write(rows, cols + 1, f"{symbol}{amountIncome['format_amount']}")

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Total Current Assets', side_heading_sub)
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']}{data['total_current_asset']}")

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Plus Fixed Assets')
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']} {data['asset_fixed'][1]}")
            account_lines = self.get_account_lines('asset_fixed', pdf_data)
            if len(account_lines) != 0:
                for account in account_lines[0][0]:
                    accAmountIncome = self.get_account_line(account['id'], account_lines)
                    if len(accAmountIncome):
                        rows += 1
                        sheet.write(rows, 0, f"{account['name']}", txt_name)
                        for amountIncome in accAmountIncome:
                            sheet.write(rows, cols + 1, f"{symbol}{amountIncome['format_amount']}")

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Plus Non-current Assets')
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']} {data['asset_non_current'][1]}")
            account_lines = self.get_account_lines('asset_non_current', pdf_data)
            if len(account_lines) != 0:
                for account in account_lines[0][0]:
                    accAmountIncome = self.get_account_line(account['id'], account_lines)
                    if len(accAmountIncome):
                        rows += 1
                        sheet.write(rows, 0, f"{account['name']}", txt_name)
                        for amountIncome in accAmountIncome:
                            sheet.write(rows, cols + 1, f"{symbol}{amountIncome['format_amount']}")

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Total Assets', side_heading_sub)
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']}{data['total_assets']}")

            rows += 1
            cols = 0
            sheet.write(rows, cols, 'LIABILITIES', sub_heading)

            rows += 1
            cols = 0
            sheet.write(rows, cols, 'Current Liabilities', side_heading_sub)

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Current Liabilities')
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']} {data['liability_current'][1]}")
            account_lines = self.get_account_lines('liability_current', pdf_data)
            if len(account_lines) != 0:
                for account in account_lines[0][0]:
                    accAmountIncome = self.get_account_line(account['id'], account_lines)
                    if len(accAmountIncome):
                        rows += 1
                        sheet.write(rows, 0, f"{account['name']}", txt_name)
                        for amountIncome in accAmountIncome:
                            sheet.write(rows, cols + 1, f"{symbol}{amountIncome['format_amount']}")

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Payable')
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']} {data['liability_payable'][1]}")
            account_lines = self.get_account_lines('liability_payable', pdf_data)
            if len(account_lines) != 0:
                for account in account_lines[0][0]:
                    accAmountIncome = self.get_account_line(account['id'], account_lines)
                    if len(accAmountIncome):
                        rows += 1
                        sheet.write(rows, 0, f"{account['name']}", txt_name)
                        for amountIncome in accAmountIncome:
                            sheet.write(rows, cols + 1, f"{symbol}{amountIncome['format_amount']}")

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Total Current Liabilities', side_heading_sub)
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']}{data['total_current_liability']}")

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Plus Non-current Liabilities')
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']} {data['liability_non_current'][1]}")
            account_lines = self.get_account_lines('liability_non_current', pdf_data)
            if len(account_lines) != 0:
                for account in account_lines[0][0]:
                    accAmountIncome = self.get_account_line(account['id'], account_lines)
                    if len(accAmountIncome):
                        rows += 1
                        sheet.write(rows, 0, f"{account['name']}", txt_name)
                        for amountIncome in accAmountIncome:
                            sheet.write(rows, cols + 1, f"{symbol}{amountIncome['format_amount']}")

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Total LIABILITIES', side_heading_sub)
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']}{data['total_liability']}")

            rows += 1
            cols = 0
            sheet.write(rows, cols, 'EQUITY', sub_heading)

            rows += 1
            cols = 0
            sheet.write(rows, cols, 'Unallocated Earnings', side_heading_sub)

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Current Earnings', side_heading_sub)
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']}{data['total_earnings']}")

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Current Allocated Earnings')
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']} {data['equity_unaffected'][1]}")
            account_lines = self.get_account_lines('equity_unaffected', pdf_data)
            if len(account_lines) != 0:
                for account in account_lines[0][0]:
                    accAmountIncome = self.get_account_line(account['id'], account_lines)
                    if len(accAmountIncome):
                        rows += 1
                        sheet.write(rows, 0, f"{account['name']}", txt_name)
                        for amountIncome in accAmountIncome:
                            sheet.write(rows, cols + 1, f"{symbol}{amountIncome['format_amount']}")

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Total Unallocated Earnings', side_heading_sub)
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']}{data['total_unallocated_earning']}")

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Retained Earnings')
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']} {data['equity'][1]}")
            account_lines = self.get_account_lines('equity', pdf_data)
            if len(account_lines) != 0:
                for account in account_lines[0][0]:
                    accAmountIncome = self.get_account_line(account['id'], account_lines)
                    if len(accAmountIncome):
                        rows += 1
                        sheet.write(rows, 0, f"{account['name']}", txt_name)
                        for amountIncome in accAmountIncome:
                            sheet.write(rows, cols + 1, f"{symbol}{amountIncome['format_amount']}")

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'Total EQUITY', side_heading_sub)
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']}{data['total_equity']}")

            rows += 1
            cols = 0
            sheet.write(rows, 0, 'LIABILITIES + EQUITY', side_heading_sub)
            for data in pdf_data[0]:
                cols = cols + 1
                sheet.write(rows, cols + 1, f"{data['currency_symbol']}{data['total_balance']}")

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
