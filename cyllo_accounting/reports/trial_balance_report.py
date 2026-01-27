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

from odoo import api, models
from odoo.tools import get_month


class TrialBalanceReport(models.AbstractModel):
    """
    This abstract model represents a Trial Balance Report.
    It provides methods to generate trial balance reports based on specified filters.
     """
    _name = 'trial.balance.report'
    _description = 'Trial Balance Report'

    @api.model
    def get_report(self, comparison, comparison_type, **filter_kwargs):
        """
        Generate a trial balance report based on the provided filters and parameters.

        Args:
            comparison (int): Number of periods to compare against.
            comparison_type (str): Type of comparison ('year', 'month', or 'quarter').
            **filter_kwargs (dict): Additional filter parameters including options, analytic_ids,
                                    journal_ids, get_filters, start_date, and end_date.

        Returns:
            tuple: A tuple containing:
                - list: Trial balance data for each account.
                - dict: Filters for the report.
                - list: Total data for each comparison period.
                - dict: Common total data for all accounts.
        """
        target_move = filter_kwargs.get('options', [])
        analytic_ids = filter_kwargs.get('analytic_ids', [])
        company_ids = filter_kwargs.get('company_ids', [])
        company_query = ""
        if company_ids:
            if len(company_ids) > 1:
                company_query += f""" lines.company_id IN {tuple(company_ids)}"""
            else:
                company_query += f""" lines.company_id = {company_ids[0]}"""

        query_acc = f"""
                select distinct acc.id as acc_id, CONCAT(acc.code, ' ', acc.name->> 'en_US') as name, acc.code as code, acc.annotations as annotations 
                from account_move_line as lines 
                inner join account_account as acc on lines.account_id = acc.id where 
                """ + company_query

        self.env.cr.execute(query_acc)
        account_ids = self.env.cr.dictfetchall()

        journal_ids = filter_kwargs.get('journal_ids', [])
        get_filters = filter_kwargs.get('get_filters', False)
        start_date = filter_kwargs.get('start_date', '')
        end_date = filter_kwargs.get('end_date', '')
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()

        where_query = f""" WHERE 1 = 1"""
        term = " AND "
        if journal_ids:
            if len(journal_ids) > 1:
                where_query += f""" AND lines.journal_id IN {tuple(journal_ids)}"""
            elif len(journal_ids) == 1:
                where_query += f""" AND lines.journal_id = {journal_ids[0]}"""

        if analytic_ids:
            if len(analytic_ids) > 1:
                where_query += " AND ("
                for idx, rec in enumerate(analytic_ids):
                    where_query += f""" (analytic_distribution->> '{rec}') IS NOT NULL 
                    {'OR' if idx < len(analytic_ids) - 1 else ''}"""
                where_query += " )"
            else:
                where_query += f""" AND (analytic_distribution->> '{analytic_ids[0]}') IS NOT NULL"""

        accounting_report_data = []
        total_data, total_common_data = {}, {}
        initial_credit_sum, initial_debit_sum, end_credit_sum, end_debit_sum = 0, 0, 0, 0
        for account in account_ids:
            acc_data = {'account': {'id': account['acc_id'], 'name': account['name'],
                                    'annotations': account['annotations']},
                        'initial_data': {}, 'end_data': {}, 'values': []}
            credit, debit = 0, 0
            initial_date = start_date
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

                initial_date = date_from

                query_move_lines = f"""
                select sum(lines.debit) as total_debit, sum(lines.credit) as total_credit
                from account_move_line as lines
                inner join account_account as acc on lines.account_id = acc.id """ + where_query + term + f"""
                lines.date >= %s and lines.date <= %s and  lines.parent_state in %s and lines.account_id = %s
                """

                self.env.cr.execute(query_move_lines,
                                    (date_from, date_to, tuple(target_move), account['acc_id']))
                res = self.env.cr.dictfetchall()
                total_debit = res[0]['total_debit'] if res[0]['total_debit'] is not None else 0
                total_credit = res[0]['total_credit'] if res[0]['total_credit'] is not None else 0

                credit += total_credit
                debit += total_debit
                acc_data['values'].append({'debit': total_debit, 'credit': total_credit})

                if count in total_data:
                    total_data[count]['debit'] += total_debit
                    total_data[count]['credit'] += total_credit
                    continue
                total_data[count] = {'debit': total_debit, 'credit': total_credit}

            initial_data_query = f"""
                            select sum(lines.debit) as total_debit, sum(lines.credit) as total_credit
                            from account_move_line as lines
                            inner join account_account as acc on lines.account_id = acc.id 
                            left join account_analytic_line as analatic on analatic.move_line_id = lines.id""" + where_query + term + f"""
                            lines.date < %s and  lines.parent_state in %s and lines.account_id = %s
                            """

            self.env.cr.execute(initial_data_query,
                                (initial_date, tuple(target_move), account['acc_id']))
            initial_data = self.env.cr.dictfetchall()

            initial_total_debit = initial_data[0]['total_debit'] if initial_data[0][
                                                                        'total_debit'] is not None else 0
            initial_total_credit = initial_data[0]['total_credit'] if initial_data[0][
                                                                          'total_credit'] is not None else 0

            acc_data['initial_data'] = {'debit': initial_total_debit,
                                        'credit': initial_total_credit}
            end_balance = debit - credit + initial_total_debit - initial_total_credit
            acc_data['end_data'] = {'debit': round(end_balance, 2) if end_balance > 0 else 0,
                                    'credit': abs(round(end_balance, 2)) if end_balance < 0 else 0}
            accounting_report_data.append(acc_data)
            initial_credit_sum += acc_data['initial_data']['credit']
            initial_debit_sum += acc_data['initial_data']['debit']
            end_debit_sum += acc_data['end_data']['debit']
            end_credit_sum += acc_data['end_data']['credit']
            total_common_data = {'initial_credit_sum': round(initial_credit_sum, 2),
                                 'initial_debit_sum': round(initial_debit_sum, 2),
                                 'end_debit_sum': round(end_debit_sum, 2),
                                 'end_credit_sum': round(end_credit_sum, 2)}
        filters = self._get_report_filters if get_filters else {}
        total_vals = list(total_data.values())
        for val in total_vals:
            val.update({
                'debit': round(val.get('debit', 0), 2),
                'credit': round(val.get('credit', 0), 2)
            })
        return accounting_report_data, filters, total_vals, total_common_data

    @property
    def _get_report_filters(self):
        """
        Get the filters for the trial balance report.
        Returns:
            dict: A dictionary containing filters such as journals and analytics.
        """
        return {
            'journals': self.env['account.journal'].search_read([], ['name', 'display_name']),
            'analytics': self.env['account.analytic.account'].search_read([],
                                                                          ['name', 'display_name'])
        }
