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
from odoo.tools.date_utils import get_month


class TaxReport(models.AbstractModel):
    """
        This model for generating the Tax Report.
    """
    _name = 'tax.report'
    _description = 'Tax Report'

    @api.model
    def get_report(self, comparison, comparison_type, **filter_kwargs):
        """
            Generates the tax report based on the provided filter parameters.

            Args:
                comparison (str): The type of comparison for the report.
                comparison_type (str): The comparison type for the report.
                **filter_kwargs: Additional keyword arguments for filtering.

            Returns:
                dict: A dictionary containing the tax report data.

            Raises:
                ValueError: If the date format is incorrect.
        """
        company = filter_kwargs.get('company', [])
        options = filter_kwargs.get('options', [])
        date_from = filter_kwargs.get('startDate', False)
        date_to = filter_kwargs.get('endDate', False)
        report_type = filter_kwargs.get('report_type', False)

        start_date = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
        company_query = ""
        if company:
            if len(company) > 1:
                company_query += f""" AND lines.company_id IN {tuple(company)}"""
            else:
                company_query += f""" AND lines.company_id = {company[0]}"""

        report_data = []
        for key in ['sale', 'purchase']:
            if report_type == 'generic':
                report_data.append(self._get_report_data_for_generic(key=key, comparison=comparison, comparison_type=comparison_type, start_date=start_date, end_date=end_date, options=options, company=company_query))
            elif report_type == 'account':
                report_data.append(self._get_report_data_for_account(key=key, comparison=comparison, comparison_type=comparison_type, start_date=start_date, end_date=end_date, options=options, company=company_query))
            elif report_type == 'tax':
                report_data.append(self._get_report_data_for_tax(key=key, comparison=comparison, comparison_type=comparison_type, start_date=start_date, end_date=end_date, options=options, company=company_query))
        return {'report_type': report_type, 'report_data': report_data}

    def _get_report_data_for_generic(self, key, comparison, comparison_type, **kwargs):
        """
            Generates the report data for the "generic" report type.
            Args:
                key (str): The tax type to filter the report (e.g., "sale" or "purchase").
                comparison (int): The number of comparison periods to include in the report.
                comparison_type (str): The type of comparison to perform (year, month, or quarter).
                **kwargs (dict): Additional filter parameters, such as start date, end date, and options.
            Returns:
                dict: A dictionary containing the report data for the "generic" report type.
        """
        company = kwargs.get('company')
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        options = kwargs.get('options')
        total_data = {}
        data = {'key': key, 'values': []}

        query_tax = f"""
        select distinct tax.id as tax_id, CONCAT(tax.name ->> 'en_US', '(', ROUND(tax.amount, 1), '%)') as name, tax.amount as amount,
        tax.annotations as annotations
        from account_move_line as lines 
        inner join account_move_line_account_tax_rel as line_tax 
        on  lines.id = line_tax.account_move_line_id
        inner join account_tax as tax on line_tax.account_tax_id = tax.id 
        where tax.type_tax_use = '{key}'
        """ + company
        self.env.cr.execute(query_tax)
        taxes = self.env.cr.dictfetchall()

        for tax in taxes:
            tax_data = {'tax_id': tax['tax_id'],
                        'display_name': tax['name'], 'annotations': tax['annotations'],
                        'values': []}
            for count in range(0, int(comparison)):
                date_from, date_to = self._get_comparison_dates(start_date, end_date, comparison_type, count)
                query = f"""
                select sum(lines.debit) as tax_debit_sum, sum(lines.credit) as tax_credit_sum  
                from account_move_line as lines 
                inner join account_move_line_account_tax_rel as line_tax 
                on  lines.id = line_tax.account_move_line_id
                inner join account_tax as tax on line_tax.account_tax_id = tax.id 
                where tax.id = %s and tax.type_tax_use = %s and lines.date >= %s and lines.date <= %s and  lines.parent_state in %s
                """ + company

                self.env.cr.execute(query, (tax['tax_id'], key, date_from, date_to, tuple(options)))
                res = self.env.cr.dictfetchall()
                tax_debit_sum = res[0]['tax_debit_sum'] if res[0]['tax_debit_sum'] is not None else 0
                tax_credit_sum = res[0]['tax_credit_sum'] if res[0]['tax_credit_sum'] is not None else 0
                net_amount = round(tax_debit_sum + tax_credit_sum, 2)
                tax_amount = round((tax_debit_sum + tax_credit_sum) * (tax['amount'] / 100), 2)
                tax_data['values'].append({
                    'net': net_amount,
                    'tax': tax_amount,
                })
                if count in total_data:
                    total_data[count]['net'] += net_amount
                    total_data[count]['tax'] += tax_amount
                    continue
                total_data[count] = {
                    'net': net_amount,
                    'tax': tax_amount,
                }
            data['values'].append(tax_data)
        data['totals'] = list(total_data.values())
        return data

    def _get_report_data_for_account(self, key, comparison, comparison_type, **kwargs):
        """
            Generates the report data for the "account" report type.

            Args:
                key (str): The tax type to filter the report (e.g., "sale" or "purchase").
                comparison (int): The number of comparison periods to include in the report.
                comparison_type (str): The type of comparison to perform (year, month, or quarter).
                **kwargs (dict): Additional filter parameters, such as start date, end date, and options.
            Returns:
                dict: A dictionary containing the report data for the "account" report type.
        """

        company = kwargs.get('company')
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        options = kwargs.get('options')
        data = []
        query_tax = f"""
        select distinct tax.id as tax_id, CONCAT(tax.name ->> 'en_US', '(', ROUND(tax.amount, 1), '%)') as name, tax.amount as amount,
        tax.annotations as annotations 
        from account_move_line as lines 
        inner join account_move_line_account_tax_rel as line_tax 
        on  lines.id = line_tax.account_move_line_id
        inner join account_tax as tax on line_tax.account_tax_id = tax.id where tax.type_tax_use = '{key}'
        """ + company
        self.env.cr.execute(query_tax)
        taxes = self.env.cr.dictfetchall()

        query_acc = f"""
        select distinct acc.id as acc_id, CONCAT(acc.code, ' ', acc.name->> 'en_US') as name, acc.code as code 
        from account_move_line as lines 
        inner join account_move_line_account_tax_rel as line_tax 
        on  lines.id = line_tax.account_move_line_id
        inner join account_tax as tax on line_tax.account_tax_id = tax.id 
        inner join account_account as acc on lines.account_id = acc.id where tax.type_tax_use = '{key}'
                """ + company
        self.env.cr.execute(query_acc)
        accounts = self.env.cr.dictfetchall()
        total_data = {}
        for account in accounts:
            acc_data = {
                'account': {'id': account['acc_id'], 'name': account['name']},
                'values': [],
            }

            for tax in taxes:
                tax_data = {
                    'tax_id': tax['tax_id'],
                    'display_name': tax['name'], 'annotations': tax['annotations'],
                    'values': []
                }
                for count in range(0, int(comparison)):
                    date_from, date_to = self._get_comparison_dates(start_date, end_date, comparison_type, count)
                    query = f"""
                                select sum(lines.debit) as tax_debit_sum, sum(lines.credit) as tax_credit_sum 
                                from account_move_line as lines 
                                inner join account_move_line_account_tax_rel as line_tax 
                                on  lines.id = line_tax.account_move_line_id
                                inner join account_tax as tax 
                                on line_tax.account_tax_id = tax.id 
                                where tax.id = %s and tax.type_tax_use = %s and lines.date >= %s 
                                and lines.date <= %s and  lines.parent_state in %s and lines.account_id = %s
                            """ + company
                    self.env.cr.execute(query, (tax['tax_id'], key, date_from, date_to, tuple(options), account['acc_id']))
                    res = self.env.cr.dictfetchall()

                    tax_debit_sum = res[0]['tax_debit_sum'] if res[0]['tax_debit_sum'] is not None else 0
                    tax_credit_sum = res[0]['tax_credit_sum'] if res[0]['tax_credit_sum'] is not None else 0
                    net_amount = round(tax_debit_sum + tax_credit_sum, 2)
                    tax_amount = round((tax_debit_sum + tax_credit_sum) * (tax['amount'] / 100), 2)
                    tax_data['values'].append({
                        'net': net_amount,
                        'tax': tax_amount,
                    })

                    if count in total_data:
                        total_data[count]['net'] += net_amount
                        total_data[count]['tax'] += tax_amount
                        continue
                    total_data[count] = {
                        'net': net_amount,
                        'tax': tax_amount,
                    }
                acc_data['values'].append(tax_data)
            data.append(acc_data)
        return {'key': key,  'data': data, 'totals': list(total_data.values())}

    def _get_report_data_for_tax(self, key, comparison, comparison_type, **kwargs):
        """
            Generates the report data for the "tax" report type.
            Args:
                key (str): The tax type to filter the report (e.g., "sale" or "purchase").
                comparison (int): The number of comparison periods to include in the report.
                comparison_type (str): The type of comparison to perform (year, month, or quarter).
                **kwargs (dict): Additional filter parameters, such as start date, end date, and options.
            Returns:
                dict: A dictionary containing the report data for the "tax" report type.
            """
        company = kwargs.get('company')
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        options = kwargs.get('options')
        data = []
        query_tax = f"""
        select distinct tax.id as tax_id, CONCAT(tax.name ->> 'en_US', '(', ROUND(tax.amount, 1), '%)') as name, tax.amount as amount,
        tax.annotations as annotations
        from account_move_line as lines 
        inner join account_move_line_account_tax_rel as line_tax on  lines.id = line_tax.account_move_line_id
        inner join account_tax as tax on line_tax.account_tax_id = tax.id where tax.type_tax_use = '{key}'
                        """ + company
        self.env.cr.execute(query_tax)
        taxes = self.env.cr.dictfetchall()
        total_data = {}
        for tax in taxes:
            query_acc = f"""
                select distinct acc.id as acc_id, CONCAT(acc.code, ' ', acc.name->> 'en_US') as name 
                from account_move_line as lines 
                inner join account_move_line_account_tax_rel as line_tax 
                on  lines.id = line_tax.account_move_line_id
                inner join account_tax as tax on line_tax.account_tax_id = tax.id 
                inner join account_account as acc on lines.account_id = acc.id where tax.id = {tax['tax_id']}
                """ + company
            self.env.cr.execute(query_acc)
            accounts = self.env.cr.dictfetchall()
            tax_data = {'tax_id': tax['tax_id'],
                        'display_name': tax['name'], 'annotations': tax['annotations'],
                        'values': []}

            for account in accounts:
                acc_data = {
                    'account': {
                        'account_id': account['acc_id'],
                        'name': account['name']
                    },
                    'values': []
                }
                for count in range(0, int(comparison)):
                    date_from, date_to = self._get_comparison_dates(start_date, end_date, comparison_type, count)
                    query = f"""
                                select sum(lines.debit) as tax_debit_sum, sum(lines.credit) as tax_credit_sum  
                                from account_move_line as lines 
                                inner join account_move_line_account_tax_rel as line_tax 
                                on  lines.id = line_tax.account_move_line_id
                                inner join account_tax as tax on line_tax.account_tax_id = tax.id 
                                where tax.id = %s and tax.type_tax_use = %s and lines.date >= %s 
                                and lines.date <= %s and  lines.parent_state in %s and lines.account_id = %s
                            """ + company
                    self.env.cr.execute(query, (tax['tax_id'], key, date_from, date_to, tuple(options), account['acc_id']))
                    res = self.env.cr.dictfetchall()
                    tax_debit_sum = res[0]['tax_debit_sum'] if res[0]['tax_debit_sum'] is not None else 0
                    tax_credit_sum = res[0]['tax_credit_sum'] if res[0]['tax_credit_sum'] is not None else 0
                    net_amount = round(tax_debit_sum + tax_credit_sum, 2)
                    tax_amount = round(
                        (tax_debit_sum + tax_credit_sum) * (tax['amount'] / 100), 2)
                    acc_data['values'].append({
                        'net': net_amount,
                        'tax': tax_amount,
                    })
                    if count in total_data:
                        total_data[count]['net'] += net_amount
                        total_data[count]['tax'] += tax_amount
                        continue
                    total_data[count] = {
                        'net': net_amount,
                        'tax': tax_amount,
                    }
                tax_data['values'].append(acc_data)
            data.append(tax_data)
        return {'key': key,  'data': data, 'totals': list(total_data.values())}

    @staticmethod
    def _get_comparison_dates(start_date, end_date, comparison_type, count):
        """
            Calculates the start and end dates for the comparison periods based on the specified comparison type.

            Args:
                start_date (datetime.date): The start date of the period.
                end_date (datetime.date): The end date of the period.
                comparison_type (str): The type of comparison ('year', 'month', or 'quarter').
                count (int): The number of comparison periods.

            Returns:
                tuple: A tuple containing the start and end dates for the comparison period.
        """
        if comparison_type == 'year':
            date_from = start_date - relativedelta(years=count)
            date_to = end_date - relativedelta(years=count)
        elif comparison_type == 'month':
            start_date_r = start_date - relativedelta(months=count)
            end_date_r = end_date - relativedelta(months=count)
            date_from, dummy = get_month(start_date_r)
            dummy, date_to = get_month(end_date_r)
        else:  # Should handle the quarter case
            start_date_r = start_date - relativedelta(
                months=count * 3)
            end_date_r = end_date - relativedelta(months=count * 3)
            date_from, dummy = get_month(start_date_r)
            dummy, date_to = get_month(end_date_r)
        return date_from, date_to
