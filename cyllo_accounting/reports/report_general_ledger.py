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

LIMIT = 100


class GeneralLedgerReport(models.AbstractModel):
    """
    Abstract model for generating the General Ledger Report.

    This model serves as a base for generating the General Ledger Report in the accounting system.

    """
    _name = 'report.cyllo_accounting.general_ledger'
    _description = 'General Ledger Report'

    @api.model
    def get_report(self, **kwargs):
        """
        Generate a financial report.

        Args:
            **kwargs: Additional keyword arguments for customizing the report, including:
                - get_filters (bool): Whether to retrieve report filters.
                - account_id (int): The ID of the specific account to generate the report for.
                - limit (int): Maximum number of entries per account in the report.
                - offset (int): Offset for pagination of entries per account in the report.

        Returns:
            tuple: A tuple containing:
                - account_data (list): A list of dictionaries containing detailed transaction data for each account.
                - account_sum_data (list): A list of dictionaries containing summarized transaction data for each account.
                - account_data_page (dict): A dictionary containing pagination information for each account's data.
                - filters (dict): A dictionary containing filters for the report, if requested.
                - currency_symbol (str): Symbol of the currency used.
        """
        get_filters = kwargs.get('get_filters', False)
        account_id = kwargs.get('account_id', False)

        accounts = self.env['account.account'].browse(int(account_id)) if account_id else self.env[
            'account.account'].search([('move_line_ids', '!=', False)])
        account_data = {}
        account_sum_data = {}
        account_data_page = {}
        for account in accounts:
            data = self._get_move_line(False, account.id, **kwargs)
            limit = kwargs.get('limit', LIMIT)
            offset = kwargs.get('offset', 0)
            if data:
                account_data_page[account.display_name] = {
                    "limit": limit,
                    "offset": offset,
                    "total": len(data),
                    "account_id": account.id,
                }
                account_data[account.display_name] = data[offset: limit] if limit else data
                sum_data = self._get_move_line(True, account.id, **kwargs)
                account_sum_data[account.display_name] = sum_data if len(sum_data) else [
                    {'account_id': account.id, 'total_credit': 0.0, 'total_debit': 0.0}]
        filters = self._get_report_filters if get_filters else {}
        currency_symbol = self.env.company.currency_id.symbol
        return [account_data], [account_sum_data], account_data_page, filters, currency_symbol

    @property
    def _get_report_filters(self):
        """
        Retrieve filters for generating a financial report.

        Returns:
            dict: A dictionary containing filters for the report, including:
                - 'journals': A list of dictionaries representing account journals, each containing 'name'.
                - 'analytics': A list of dictionaries representing analytic accounts, each containing 'name'.
        """
        return {
            'journals': self.env['account.journal'].search_read([], ['name', 'display_name']),
            'analytics': self.env['account.analytic.account'].search_read([], ['name', 'display_name'])
        }

    def _get_move_line(self, get_sum, account_id, **kwargs):
        """
        Retrieve move line data for a specific account.

        Args:
            get_sum (bool): Whether to retrieve summarized data.
            account_id (int): The ID of the account to retrieve move lines for.
            **kwargs: Additional keyword arguments for filtering move lines, including:
                - target_move (list): List of target move states to consider.
                - analytic_ids (list): List of analytic account IDs for additional filtering.
                - journal_ids (list): List of journal IDs for additional filtering.
                - company_ids (list): List of company IDs for additional filtering.
                - start_date (str): Start date of the period to retrieve move lines for in 'YYYY-MM-DD' format.
                - end_date (str): End date of the period to retrieve move lines for in 'YYYY-MM-DD' format.

        Returns:
            list: A list of dictionaries containing move line data, with keys:
                - 'account_id': ID of the account.
                - 'total_credit': Total credit amount.
                - 'total_debit': Total debit amount.
        """
        if get_sum:
            return self._get_sum_data(account_id, **kwargs)
        else:
            return self._get_data(account_id, **kwargs)

    def _get_sum_data(self, account_id, **kwargs):
        """
        Retrieve summarized move line data for a specific account.

        Args:
            account_id (int): The ID of the account to retrieve summarized move lines for.
            **kwargs: Additional keyword arguments for filtering move lines, including:
                - target_move (list): List of target move states to consider.
                - analytic_ids (list): List of analytic account IDs for additional filtering.
                - journal_ids (list): List of journal IDs for additional filtering.
                - company_ids (list): List of company IDs for additional filtering.
                - start_date (str): Start date of the period to retrieve move lines for in 'YYYY-MM-DD' format.
                - end_date (str): End date of the period to retrieve move lines for in 'YYYY-MM-DD' format.

        Returns:
            list: A list of dictionaries containing summarized move line data, with keys:
                - 'account_id': ID of the account.
                - 'total_credit': Total credit amount.
                - 'total_debit': Total debit amount.
        """
        target_move = kwargs.get('target_move', [])
        analytic_ids = kwargs.get('analytic_ids', [])
        journal_ids = kwargs.get('journal_ids', [])
        company_ids = kwargs.get('company_ids', [])
        start_date = kwargs.get('start_date', "")
        end_date = kwargs.get('end_date', "")

        query = """SELECT 
                        move_line.account_id,
                        SUM(move_line.credit) AS total_credit,
                        SUM(move_line.debit) AS total_debit
                    FROM 
                        account_move_line move_line 
                    WHERE 
                        move_line.account_id = %s 
                        AND move_line.parent_state IN %s
                        AND move_line.date >= %s 
                        AND move_line.date <= %s
                    """
        params = (account_id, tuple(target_move), start_date, end_date)
        if company_ids:
            query += f""" AND move_line.company_id IN {tuple(company_ids)}"""
        if journal_ids:
            if len(journal_ids) > 1:
                query += f""" AND move_line.journal_id IN {tuple(journal_ids)}"""
            else:
                query += f""" AND move_line.journal_id = {journal_ids[0]}"""
        if analytic_ids:
            if len(analytic_ids) > 1:
                query += " AND ("
                for idx, rec in enumerate(analytic_ids):
                    query += f""" (move_line.analytic_distribution->> '{rec}') IS NOT NULL {'OR' if idx < len(analytic_ids) - 1 else ''}"""
                query += " )"
            else:
                query += f""" AND (move_line.analytic_distribution->> '{analytic_ids[0]}') IS NOT NULL"""
        query += """ GROUP BY move_line.account_id;"""
        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()

    def _get_data(self, account_id, **kwargs):
        """
        Retrieve detailed move line data for a specific account.

        Args:
            account_id (int): The ID of the account to retrieve detailed move lines for.
            **kwargs: Additional keyword arguments for filtering move lines, including:
                - target_move (list): List of target move states to consider.
                - analytic_ids (list): List of analytic account IDs for additional filtering.
                - journal_ids (list): List of journal IDs for additional filtering.
                - company_ids (list): List of company IDs for additional filtering.
                - start_date (str): Start date of the period to retrieve move lines for in 'YYYY-MM-DD' format.
                - end_date (str): End date of the period to retrieve move lines for in 'YYYY-MM-DD' format.

        Returns:
            list: A list of dictionaries containing detailed move line data, with keys:
                - 'id': ID of the move line.
                - 'annotations': Annotations of the move line.
                - 'account_id': ID of the account.
                - 'credit': Credit amount.
                - 'date': Date of the move line.
                - 'debit': Debit amount.
                - 'journal_id': ID of the journal.
                - 'move_id': ID of the move.
                - 'move_name': Name of the move.
                - 'name': Name of the move line.
                - 'partner_name': Name of the partner associated with the move line.
                - 'partner_id': ID of the partner associated with the move line.
        """
        target_move = kwargs.get('target_move', [])
        analytic_ids = kwargs.get('analytic_ids', [])
        journal_ids = kwargs.get('journal_ids', [])
        company_ids = kwargs.get('company_ids', [])
        start_date = kwargs.get('start_date', "")
        end_date = kwargs.get('end_date', "")

        query = """SELECT move_line.id, move_line.annotations, move_line.account_id, move_line.credit,
                   move_line.date, move_line.debit, move_line.journal_id,
                   move_line.move_id, move_line.move_name, move_line.name,
                   partner.name partner_name, partner.id partner_id
                   FROM account_move_line move_line INNER JOIN res_partner partner
                   ON move_line.partner_id = partner.id
                   WHERE move_line.account_id = %s 
                   AND move_line.parent_state in %s
                   AND move_line.date >= %s 
                   AND move_line.date <= %s"""
        params = (account_id, tuple(target_move), start_date, end_date)
        if company_ids:
            if len(company_ids) > 1:
                query += f""" AND move_line.company_id IN {tuple(company_ids)}"""
            else:
                query += f""" AND move_line.company_id = {company_ids[0]}"""
        if journal_ids:
            if len(journal_ids) > 1:
                query += f""" AND move_line.journal_id IN {tuple(journal_ids)}"""
            else:
                query += f""" AND move_line.journal_id = {journal_ids[0]}"""
        if analytic_ids:
            if len(analytic_ids) > 1:
                query += " AND ("
                for idx, rec in enumerate(analytic_ids):
                    query += f""" (move_line.analytic_distribution->> '{rec}') IS NOT NULL {'OR' if idx < len(analytic_ids) - 1 else ''}"""
                query += " )"
            else:
                query += f""" AND (move_line.analytic_distribution->> '{analytic_ids[0]}') IS NOT NULL"""
        query += """ ORDER BY move_line.id DESC"""
        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()

    @api.model
    def get_account_data(self, **kwargs):
        """
        Retrieve account data for a specific account.

        Args:
            **kwargs: Additional keyword arguments for customizing the data retrieval, including:
                - limit (int): Maximum number of entries per account.
                - offset (int): Offset for pagination of entries per account.
                - account_id (int): The ID of the specific account to retrieve data for.

        Returns:
            tuple: A tuple containing:
                - account_data (dict): A dictionary containing detailed transaction data for the specified account, with keys:
                    - Account name: Detailed transaction data for the account, in a list of dictionaries format.
                - account_data_page (dict): A dictionary containing pagination information for the account's data, with keys:
                    - Account name: Pagination information for the account's data, including 'limit', 'offset', 'total', and 'account_id'.
        """
        account_data_page = {}
        account_data = {}
        limit = kwargs.get("limit", LIMIT)
        offset = kwargs.get("offset", 0)
        account_id = kwargs.get("account_id")
        if account_id:
            account_id = self.env['account.account'].browse(account_id)
            data = self._get_move_line(False, **kwargs)
            account_data_page[account_id.display_name] = {
                "limit": limit,
                "offset": offset,
                "total": len(data),
                "account_id": account_id.id,
            }
            account_data[account_id.display_name] = data[offset: limit + offset] if limit else data
        return account_data, account_data_page

    @api.model
    def get_xlsx_report(self, data, response, report_name):
        """
        Generate an XLSX report based on the provided data.

        Args:
            data (str): JSON data containing information required for generating the report.
            response: The HTTP response object used to send the generated XLSX file.
            report_name (str): Name of the report.

        Returns:
            None
        """
        data = json.loads(data)
        filters_kwargs = data.get("filterData", {})
        filters_kwargs['limit'] = 0
        filters_kwargs['get_filters'] = True
        account_data, account_sum_data, dummy, filters, currency_symbol = self.get_report(**filters_kwargs)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        start_date = filters_kwargs.get('start_date', "")
        end_date = filters_kwargs.get('end_date', "")
        sheet = workbook.add_worksheet()
        option = "With Draft Entries" if len(filters_kwargs.get('target_move', [])) == 2 else ""
        head = workbook.add_format(
            {'font_size': 15, 'align': 'center', 'bold': True})
        sub_heading = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '10px',
             'border': 1, 'bg_color': '#D3D3D3',
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
        header_text_name = workbook.add_format({'font_size': '10px', 'border': 1, 'bold': True})
        header_text_name.set_indent(2)
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 15)
        sheet.write('A1:b1', report_name, head)
        sheet.write('B3:b4', 'Date Range', filter_head)
        sheet.write('B4:b4', 'Journals', filter_head)
        sheet.write('B5:b4', 'Analytic Accounts', filter_head)
        sheet.write('B6:b4', 'Options', filter_head)
        sheet.merge_range('C3:G3', f"{start_date} to {end_date}", filter_body)
        journal_ids = filters_kwargs.get('journal_ids', False)
        if journal_ids:
            journals = filters.get('journals', [])
            display_names = list(
                map(lambda record: record['name'], filter(lambda rec: rec['id'] in journal_ids, journals)))
            pos = len(display_names) + 3
            display_names = ', '.join(display_names)
            sheet.merge_range(3, 2, 3, pos, display_names, filter_body)
        analytic_ids = filters_kwargs.get('analytic_ids', False)
        if analytic_ids:
            analytics = filters.get('analytics', [])
            display_names = list(
                map(lambda record: record['name'], filter(lambda rec: rec['id'] in analytic_ids, analytics)))
            pos = len(display_names) + 3
            display_names = ', '.join(display_names)
            sheet.merge_range(4, 2, 4, pos, display_names, filter_body)
        sheet.merge_range(5, 2, 5, 3, option, filter_body)
        analytic_ids = filters_kwargs.get('analytic_ids', False)
        col = 0
        sheet.write(8, col, ' ', sub_heading)
        sheet.write(8, col + 1, 'Date', sub_heading)
        sheet.merge_range('C9:E9', 'Communication', sub_heading)
        sheet.merge_range('F9:G9', 'Partner', sub_heading)
        sheet.merge_range('H9:I9', 'Debit', sub_heading)
        sheet.merge_range('J9:K9', 'Credit', sub_heading)
        sheet.merge_range('L9:M9', 'Balance', sub_heading)
        row = 8
        total_debit = total_credit = 0
        for rec in account_data[0]:
            account_obj = account_sum_data[0][rec][0]
            row += 1
            sheet.write(row, col, rec, header_text_name)
            sheet.write(row, col + 1, ' ', txt_name)
            sheet.merge_range(row, col + 2, row, col + 4, ' ', txt_name)
            sheet.merge_range(row, col + 4, row, col + 6, ' ', txt_name)
            sheet.merge_range(row, col + 7, row, col + 8, f"{currency_symbol} {account_obj['total_debit']}",
                              header_text_name)
            sheet.merge_range(row, col + 9, row, col + 10, f"{currency_symbol} {account_obj['total_credit']}",
                              header_text_name)
            sheet.merge_range(row, col + 11, row, col + 12,
                              f"{currency_symbol} {account_obj['total_debit'] - account_obj['total_credit']}",
                              header_text_name)
            for inner_rec in account_data[0][rec]:
                row += 1
                name = inner_rec['name'] if inner_rec.get('name', "") else ""
                sheet.set_row(row, 20 if len(name) < 40 else 25)
                sheet.write(row, col, inner_rec['move_name'], txt_name)
                sheet.write(row, col + 1, inner_rec['date'].strftime("%Y-%m-%d"), txt_name)
                sheet.set_column(col + 2, col + 4, 15 if len(name) < 40 else 20)
                sheet.merge_range(row, col + 2, row, col + 4, name, txt_name)
                sheet.merge_range(row, col + 5, row, col + 6, inner_rec['partner_name'], txt_name)
                sheet.merge_range(row, col + 7, row, col + 8, f"{currency_symbol} {inner_rec['debit']}", txt_name)
                sheet.merge_range(row, col + 9, row, col + 10, f"{currency_symbol} {inner_rec['credit']}", txt_name)
                sheet.merge_range(row, col + 11, row, col + 12, ' ', txt_name)

            total_credit += account_obj['total_credit']
            total_debit += account_obj['total_debit']
        sheet.merge_range(row, col, row, col + 6, 'Total', filter_head)
        sheet.merge_range(row, col + 7, row, col + 8, f"{currency_symbol} {total_debit}", filter_head)
        sheet.merge_range(row, col + 9, row, col + 10, f"{currency_symbol} {total_credit}", filter_head)
        sheet.merge_range(row, col + 11, row, col + 12, f"{currency_symbol} {total_debit - total_credit}", filter_head)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
