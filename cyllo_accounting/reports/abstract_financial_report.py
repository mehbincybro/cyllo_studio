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
import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools import get_fiscal_year, get_month

ACCOUNTING_TYPES = ['income', 'income_other', 'expense', 'expense_depreciation',
                    'expense_direct_cost', 'asset_receivable', 'asset_cash',
                    'asset_current', 'asset_non_current', 'asset_prepayments',
                    'asset_fixed', 'liability_payable', 'liability_credit_card',
                    'liability_current', 'liability_non_current', 'equity',
                    'equity_unaffected']


class AbstractFinancialReport(models.AbstractModel):
    """
    Abstract model for handling financial reports such as balance sheets and profit and loss statements.
    This abstract model provides common functionality required for generating and managing financial reports.
    """

    _name = 'abstract.financial.report'
    _description = 'Financial Report'

    @api.model
    def get_report(self, comparison, comparison_type, **filter_kwargs):
        """
        Generate a report based on specified parameters.

        Args:
            comparison (int): Number of comparison periods.
            comparison_type (str): Type of comparison ('year', 'month', or 'quarter').
            **filter_kwargs: Additional keyword arguments for filtering data, including:
                - start_date (str): Start date of the reporting period in 'YYYY-MM-DD' format.
                - end_date (str): End date of the reporting period in 'YYYY-MM-DD' format.
                - get_filters (bool): Whether to retrieve report filters.

        Returns:
            tuple: A tuple containing:
                - accounting_report_data (list): A list of dictionaries containing report data for each
                comparison period.
                - filters (dict or None): A dictionary containing filters for the report,
                if requested; otherwise, None.
        """
        start_date = filter_kwargs.get('start_date', "")
        end_date = filter_kwargs.get('end_date', "")
        get_filters = filter_kwargs.get('get_filters', False)
        accounting_report_data = []
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
        for count in range(0, int(comparison)):
            if comparison_type == 'year':
                date_from = start_date - relativedelta(years=count)
                date_to = end_date - relativedelta(years=count)
            elif comparison_type == 'month':
                start_date_r = start_date - relativedelta(months=count)
                end_date_r = end_date - relativedelta(months=count)
                date_from, dummy = get_month(start_date_r)
                dummy, date_to = get_month(end_date_r)
            else:  # Should handle the quarter case
                start_date_r = start_date - relativedelta(months=count * 3)
                end_date_r = end_date - relativedelta(months=count * 3)
                date_from, dummy = get_month(start_date_r)
                dummy, date_to = get_month(end_date_r)
            filter_kwargs['start_date'] = date_from
            filter_kwargs['end_date'] = date_to
            account_entries = {account_type: self._get_account_entries(account_type, **filter_kwargs) for
                               account_type in ACCOUNTING_TYPES}
            accounting_report_data.append(self._get_report_data(account_entries))

        filters = self._get_report_filters if get_filters else {}
        return accounting_report_data, filters

    @property
    def _get_report_filters(self):
        """
          Get filters for generating a report.

          Returns:
              dict: A dictionary containing filters for the report, including:
                  - 'journals': A list of dictionaries representing account journals, each containing 'name'.
                  - 'accounts': A list of dictionaries representing accounts, each containing 'name'.
                  - 'analytics': A list of dictionaries representing analytic accounts, each containing 'name'.
        """
        return {
            'journals': self.env['account.journal'].search_read([], ['name', 'display_name']),
            'accounts': self.env['account.account'].search_read([], ['name', 'display_name']),
            'analytics': self.env['account.analytic.account'].search_read([], ['name', 'display_name'])
        }

    def _get_report_data(self, account_entries):
        """
        Calculate and aggregate data for generating a financial report.

        Args:
            account_entries (dict): A dictionary containing entries for various account types.

        Returns:
            dict: A dictionary containing aggregated data for the report, including:
                - 'total': Total balance.
                - 'total_value': Total balance as a float.
                - 'total_expense': Total expenses.
                - 'total_income': Total income.
                - 'total_current_asset': Total current assets.
                - 'total_assets': Total assets.
                - 'total_current_liability': Total current liabilities.
                - 'total_liability': Total liabilities.
                - 'total_earnings': Total earnings.
                - 'total_unallocated_earning': Total unallocated earnings.
                - 'total_equity': Total equity.
                - 'total_balance': Total balance (sum of liabilities and equity).
                - 'currency_symbol': Symbol of the currency used.
                - 'gross_profit': Gross profit.
                - Additional keys for individual account entries.
        """
        total_income = 0
        total_expense = 0
        total_current_asset = 0
        total_assets = 0
        total_current_liability = 0
        total_liability = 0
        total_unallocated_earning = 0
        total_equity = 0

        for account_type, entries in account_entries.items():
            for entry in entries[0]:
                amount = float(entry['amount'])
                if account_type in ['income', 'income_other']:
                    total_income += amount
                elif account_type == 'expense_direct_cost':
                    total_income -= amount
                elif account_type in ['expense', 'expense_depreciation']:
                    total_expense += amount
                elif account_type in ['asset_receivable', 'asset_current', 'asset_cash', 'asset_prepayments']:
                    total_current_asset += amount
                elif account_type in ['asset_fixed', 'asset_non_current']:
                    total_assets += amount
                elif account_type in ['liability_current', 'liability_payable']:
                    total_current_liability += amount
                elif account_type == 'liability_non_current':
                    total_liability += amount
                elif account_type == 'equity_unaffected':
                    total_unallocated_earning += amount
                elif account_type == 'equity':
                    total_equity += amount

        total_unallocated_earning += total_income - total_expense
        total_assets += total_current_asset
        total_liability += total_current_liability
        total_equity += total_unallocated_earning
        total = total_liability + total_equity
        expense_direct_cost = account_entries.get("expense_direct_cost")
        income = account_entries.get("income")
        gross_profit = income[2] + expense_direct_cost[2]
        super_total = round(total_income - total_expense, 2)
        return {
            'total': f"{super_total:,.2f}",
            'total_value': super_total,
            'total_expense': f"{total_expense:,.2f}",
            'total_income': f"{total_income:,.2f}",
            'total_current_asset': f"{total_current_asset:,.2f}",
            'total_assets': f"{total_assets:,.2f}",
            'total_current_liability': f"{total_current_liability:,.2f}",
            'total_liability': f"{total_liability:,.2f}",
            'total_earnings': f"{total_income - total_expense:,.2f}",
            'total_unallocated_earning': f"{total_unallocated_earning:,.2f}",
            'total_equity': f"{total_equity:,.2f}",
            'total_balance': f"{total:,.2f}",
            'currency_symbol': self.env.company.currency_id.symbol,
            'gross_profit': f"{gross_profit:,.2f}",
            **account_entries
        }

    def _get_move_line(self, account_id, **filter_kwargs):
        """
        Retrieve move line data for a specific account within a given date range and filters.

        Args:
            account_id (int): The ID of the account to retrieve move lines for.
            **filter_kwargs: Additional keyword arguments for filtering move lines, including:
                - target_move (list): List of target move states to consider.
                - analytic_ids (list): List of analytic account IDs for additional filtering.
                - journal_ids (list): List of journal IDs for additional filtering.
                - account_ids (list): List of account IDs for additional filtering.
                - start_date (str): Start date of the period to retrieve move lines for in 'YYYY-MM-DD' format.
                - end_date (str): End date of the period to retrieve move lines for in 'YYYY-MM-DD' format.

        Returns:
            list: A list of dictionaries containing move line data, with the following keys:
                - 'total_debit': Total debit amount.
                - 'total_credit': Total credit amount.
                - 'balance': Balance (debit - credit).
        """
        target_move = filter_kwargs.get('target_move', [])
        analytic_ids = filter_kwargs.get('analytic_ids', [])
        journal_ids = filter_kwargs.get('journal_ids', [])
        account_ids = filter_kwargs.get('account_ids', [])
        start_date = filter_kwargs.get('start_date', "")
        end_date = filter_kwargs.get('end_date', "")
        query = f"""SELECT
                        COALESCE(SUM(debit), 0) AS total_debit,
                        COALESCE(SUM(credit), 0) AS total_credit,
                        COALESCE(SUM(debit), 0) - COALESCE(SUM(credit), 0) AS balance
                    FROM
                        account_move_line
                    WHERE 
                    account_id = {account_id} AND
                    date >= %s AND date <= %s
                    AND parent_state IN %s"""
        params = (start_date, end_date, tuple(target_move))
        if account_ids:
            if len(account_ids) > 1:
                query += f""" AND account_id IN {tuple(account_ids)}"""
            else:
                query += f""" AND account_id = {account_ids[0]}"""
        if journal_ids:
            if len(journal_ids) > 1:
                query += f""" AND journal_id IN {tuple(journal_ids)}"""
            else:
                query += f""" AND journal_id = {journal_ids[0]}"""
        if analytic_ids:
            if len(analytic_ids) > 1:
                query += " AND ("
                for idx, rec in enumerate(analytic_ids):
                    query += f""" (analytic_distribution->> '{rec}') IS NOT NULL 
                    {'OR' if idx < len(analytic_ids) - 1 else ''}"""
                query += " )"
            else:
                query += f""" AND (analytic_distribution->> '{analytic_ids[0]}') IS NOT NULL"""
        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()

    def _get_account_entries(self, account_type, **filter_kwargs):
        """
        Retrieve entries for accounts of a specific type within a given date range and filters.

        Args:
            account_type (str): The type of accounts to retrieve entries for.
            **filter_kwargs: Additional keyword arguments for filtering entries, including:
                - target_move (list): List of target move states to consider.
                - analytic_ids (list): List of analytic account IDs for additional filtering.
                - journal_ids (list): List of journal IDs for additional filtering.
                - account_ids (list): List of account IDs for additional filtering.
                - start_date (str): Start date of the period to retrieve entries for in 'YYYY-MM-DD' format.
                - end_date (str): End date of the period to retrieve entries for in 'YYYY-MM-DD' format.

        Returns:
            tuple: A tuple containing:
                - entries (list): A list of dictionaries containing entries for the accounts of the specified type, with keys:
                    - 'name': Name of the account entry.
                    - 'format_amount': Formatted amount of the entry.
                    - 'id': ID of the account entry.
                    - 'amount': Amount of the entry.
                    - 'annotations': Annotations of the account entry.
                - total_formatted (str): Total amount of entries for the accounts of the specified type, formatted.
                - total (float): Total amount of entries for the accounts of the specified type.
        """
        account_ids = self.env['account.account'].search([('account_type', '=', account_type)])
        total = 0
        entries = []
        for account_id in account_ids:
            move_line = self._get_move_line(account_id.id, **filter_kwargs)
            name = f"{account_id.root_id.id} - {account_id.name}"
            amount = 0
            if move_line:
                amount = move_line[0]['balance']
                amount = -amount if account_type in ['income', 'income_other',
                                                     'liability_payable', 'liability_current',
                                                     'liability_non_current', 'equity',
                                                     'equity_unaffected'] else amount
            entries.append({
                'name': name,
                'format_amount': "{:,.2f}".format(amount),
                'id': account_id.id,
                'amount': amount,
                'annotations': account_id.annotations
            })
            total += amount
        return entries, "{:,.2f}".format(total), total

    @api.model
    def get_financial_year(self):
        """
        Retrieve the start and end dates of the current financial year.

        Returns:
            dict: A dictionary containing the start and end dates of the financial year, with keys:
                - 'start_date': Start date of the financial year in 'YYYY-MM-DD' format.
                - 'end_date': End date of the financial year in 'YYYY-MM-DD' format.
        """
        today = fields.date.today()
        acc_fiscal_year = self.env['account.fiscal.year'].search(
            [('state', '=', 'open'), ('start_date', '<=', today), ('end_date', '>=', today)])
        if acc_fiscal_year:
            start_date = acc_fiscal_year.start_date
            end_date = acc_fiscal_year.end_date
        else:
            start_date, end_date = get_fiscal_year(today)
        return {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }
    
    @api.model
    def get_search_view(self):
        return self.sudo().env.ref("cyllo_accounting.view_account_move_line_search").id
