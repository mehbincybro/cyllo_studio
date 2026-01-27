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
import io
import json

import pandas as pd
import xlsxwriter
from odoo import api, fields, models
from odoo.tools import date_utils
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)


class ResPartner(models.Model):
    """ Extend the res.partner model to incorporate additional fields or behaviors as needed."""

    _inherit = 'res.partner'

    def _execute_query(self, date, index):
        """ Execute a SQL query to fetch the count of distinct sale
        orders and their total amount based on a given date range."""
        query = f"""SELECT 
                COUNT(DISTINCT sale_order.id) AS frequency_{index},
                COALESCE(SUM(sale_order.amount_total), 0) AS monetary_{index}
            FROM
                res_partner
            LEFT JOIN
                sale_order ON res_partner.id = sale_order.partner_id
                AND sale_order.date_order >= %s AND sale_order.date_order <= %s
            WHERE 
                res_partner.active = true
                AND EXISTS (
                    SELECT 1
                    FROM sale_order so
                    WHERE so.partner_id = res_partner.id
                    LIMIT 1
                )
            GROUP BY
                res_partner.id
            ORDER BY 
                res_partner.id;"""
        self.env.cr.execute(query, date)
        return self.env.cr.dictfetchall()

    def predict_churn(self, *dataframes, dates, date_range):
        """Predict churn based on input dataframes containing customer information"""
        data = pd.concat(dataframes, axis=1)
        if not data.empty:
            comp_freq = data.columns[len(data.columns) - 4]
            comp_mon = data.columns[len(data.columns) - 3]
            freq_columns = [f'frequency_{i}' for i in
                            range(1, int(len(data.columns) / 2 - 1))]
            mon_columns = [f'monetary_{i}' for i in
                           range(1, int(len(data.columns) / 2 - 1))]
            data['threshold_frequency'] = data[freq_columns].mean(
                axis=1) * 0.8
            data['threshold_monetary'] = data[mon_columns].mean(
                axis=1) * 0.8
            data['Churn'] = 'Yes'
            condition = (((data[comp_freq] > data['threshold_frequency']) |
                          (data[comp_mon] > data['threshold_monetary'])))
            data.loc[condition, 'Churn'] = 'No'
            freq_mon_data = data.drop(
                ['threshold_monetary', 'threshold_frequency', 'Churn'], axis=1)
            result = data[[comp_freq, comp_mon, 'threshold_frequency',
                           'threshold_monetary', 'Churn']]
            result = result.rename(
                columns={comp_freq: 'frequency', comp_mon: 'monetary'})
            try:
                X_train, X_test, y_train, y_test = train_test_split(
                    result.drop(['Churn'], axis=1),
                    result['Churn'],
                    test_size=0.33, random_state=42)

                scaler = StandardScaler()
                X_train = scaler.fit_transform(X_train)

                clf = RandomForestClassifier()
                clf.fit(X_train, y_train)
                test_data = pd.concat(dataframes[1:], axis=1)

                test_freq_columns = [f'frequency_{i}' for i in range(2, int(len(
                    test_data.columns) / 2 + 1))]
                test_mon_columns = [f'monetary_{i}' for i in range(2, int(len(
                    test_data.columns) / 2 + 1))]
                test_data['threshold_frequency'] = test_data[
                                                       test_freq_columns].mean(
                    axis=1) * 0.8
                test_data['threshold_monetary'] = test_data[
                                                      test_mon_columns].mean(
                    axis=1) * 0.8
                freq = test_data.columns[len(test_data.columns) - 4]
                mon = test_data.columns[len(test_data.columns) - 3]
                test_result = test_data[
                    [freq, mon, 'threshold_frequency', 'threshold_monetary']]
                test_result = test_result.rename(columns={
                    freq: 'frequency',
                    mon: 'monetary',
                })
                test_data_scaled = scaler.transform(test_result)

                y_pred = clf.predict(test_data_scaled)
                test_result['Churn'] = y_pred

                probabilities = clf.predict_proba(test_data_scaled)
                if probabilities.shape[1] > 1:
                    test_result['prob_yes'] = probabilities[:, 1]
                    test_result['prob_no'] = probabilities[:, 0]
                else:
                    test_result['prob_yes'] = probabilities[:, 0]
                    test_result['prob_no'] = 1 - probabilities[:, 0]
                test_result['prob_yes'] = (
                    round(test_result['prob_yes'] * 100, 2))
                test_result['prob_no'] = round(test_result['prob_no'] * 100, 2)

                total_churn_count = len(
                    test_result[test_result['Churn'] == 'Yes'])
                total_not_churn_count = len(
                    test_result[test_result['Churn'] == 'No'])
                total_records = len(test_result)

                churn_perc = (total_churn_count / total_records) * 100
                not_churn_perc = (total_not_churn_count / total_records) * 100
                customer_names_query = """
                    SELECT
                        rp.id AS CustomerID,
                        rp.name AS CustomerName,
                        MAX(so.date_order) AS LastSaleOrderDate
                    FROM res_partner AS rp
                    LEFT JOIN sale_order AS so ON so.partner_id = rp.id
                    WHERE rp.active = true
                    AND EXISTS (
                        SELECT 1
                        FROM sale_order so
                        WHERE so.partner_id = rp.id
                        LIMIT 1
                    )
                    GROUP BY rp.id, rp.name
                    ORDER BY rp.id
                """
                self.env.cr.execute(customer_names_query)
                customers = self.env.cr.dictfetchall()
                test_result['custId'] = [record['customerid'] for record in
                                         customers]
                test_result['custName'] = [record['customername'] for record in
                                           customers]
                test_result['last_purchase_date'] = [
                    record['lastsaleorderdate'].strftime('%d/%m/%Y %H:%M:%S')
                    for record in customers]
                freq_mon_churn_data = pd.concat([test_result, freq_mon_data],
                                                axis=1)
                cust_wise_details = freq_mon_churn_data.to_dict(
                    orient='records')
                chart_data = data.to_dict(orient='records')
                for customer in cust_wise_details:
                    domain = [('partner_id', '=', customer['custId']),
                              ('date_order', '>=', date_range[0][0]),
                              ('date_order', '<=', date_range[-1][1])
                              ]
                    total_sales = self.env['sale.order'].search_count(domain)
                    total_amt = sum(
                        self.env['sale.order'].search(domain).mapped(
                            'amount_total'))
                    customer['total_sales'] = round(total_sales, 2)
                    customer['total_amount'] = round(total_amt, 2)
                sorted_details = sorted(cust_wise_details,
                                        key=lambda x: x['total_sales'],
                                        reverse=True)
                for index, cust in enumerate(sorted_details, start=1):
                    cust['index'] = index
                vals = {
                    'predict': True,
                    'is_financial_year': self.env['ir.config_parameter'].sudo()
                    .get_param('cyllo_analytics.is_financial_year'),
                    'total_cust': self.env['res.partner'].search_count([]),
                    'active_cust': total_records,
                    'churn_perc': round(churn_perc, 2),
                    'not_churn_perc': round(not_churn_perc, 2),
                    'cust_wise_details': sorted_details,
                    'start_date': dates[0][0],
                    'end_date': dates[-1][1],
                    'date_range': dates,
                    'chart_data': chart_data,
                }
                return vals
            except ValueError as e:
                # Handle the case where the dataset is too small to split
                return {
                    'predict': False,
                    'is_financial_year': self.env['ir.config_parameter'].sudo()
                    .get_param('cyllo_analytics.is_financial_year'),
                    'start_date': dates[0][0],
                    'end_date': dates[-1][1],
                    'date_range': dates,
                }
        else:
            return {
                'predict': False,
                'is_financial_year': self.env['ir.config_parameter'].sudo()
                .get_param('cyllo_analytics.is_financial_year'),
                'start_date': dates[0][0],
                'end_date': dates[-1][1],
                'date_range': dates,
            }

    @api.model
    def get_date_range(self, period, period_type, dur):
        """Get date ranges based on the specified period and period type, and predict churn for each date range."""
        date_range = []
        if period_type == 'current_date':
            today = fields.Date.today()
            if period == 'Quarter':
                date_range = [date_utils.get_quarter(today)]
                for i in range(int(dur)):
                    if today.month <= 3:
                        today = today.replace(month=10, year=today.year - 1,
                                              day=1)
                    else:
                        today = today.replace(month=(today.month - 3), day=1)
                    date_range.append(date_utils.get_quarter(today))
                date_range = date_range[1:][::-1]
            elif period == 'Year':
                date_range = [(today.replace(year=today.year - i - 1,
                                             month=today.month,
                                             day=today.day),
                               date_utils.subtract(
                                   today.replace(year=today.year - i,
                                                 month=today.month,
                                                 day=today.day),
                                   days=1))
                              for i in range(int(dur))][::-1]
            elif period == 'Month':
                date_range = [(date_utils.subtract(today, months=i * 1),
                               date_utils.subtract(
                                   date_utils.subtract(date_utils.add(
                                       date_utils.subtract(today, months=i * 1),
                                       months=1), days=1)))
                              for i in range(1, int(dur) + 1)][::-1]
            elif period == 'Half Year':
                date_range = [(date_utils.subtract(today, months=i * 6),
                               date_utils.subtract(date_utils.add(
                                   date_utils.subtract(today, months=i * 6),
                                   months=6),
                                   days=1)) for i in
                              range(1, int(dur) + 1)][::-1]
            date_range_formatted = [(start_date.strftime("%d/%m/%Y"),
                                     end_date.strftime("%d/%m/%Y"))
                                    for start_date, end_date in date_range]
            data_list = [pd.DataFrame(self._execute_query(year, i)) for i, year
                         in enumerate(date_range, start=1)]
            return self.predict_churn(
                *data_list,
                dates=date_range_formatted,
                date_range=date_range)
        elif period_type == 'financial_year':
            month = self.env['ir.config_parameter'].sudo().get_param(
                'cyllo_analytics.fiscal_year_last_month')
            day = self.env['ir.config_parameter'].sudo().get_param(
                'cyllo_analytics.fiscal_year_last_day')
            today = datetime.datetime(fields.Date.today().year, int(month),
                                      int(day)).date()
            if period == 'Quarter':
                date_range = [(date_utils.add(
                    date_utils.subtract(today, months=i * 3), days=1),
                               date_utils.subtract(date_utils.subtract(
                                   date_utils.add(date_utils.add(
                                       date_utils.subtract(today, months=i * 3),
                                       days=1), months=3), days=1)))
                    for i in range(1, int(dur) + 1)][::-1]
            if period == 'Year':
                date_range = [(date_utils.add(
                    date_utils.subtract(today, months=i * 12), days=1),
                               date_utils.subtract(date_utils.subtract(
                                   date_utils.add(date_utils.add(
                                       date_utils.subtract(today,
                                                           months=i * 12),
                                       days=1)
                                       , months=12), days=1))) for i
                    in range(1, int(dur) + 1)][::-1]
            elif period == 'Half Year':
                date_range = [(date_utils.add(
                    date_utils.subtract(today, months=i * 6), days=1),
                               date_utils.subtract(date_utils.subtract(
                                   date_utils.add(date_utils.add(
                                       date_utils.subtract(today, months=i * 6),
                                       days=1), months=6), days=1)))
                    for i in range(1, int(dur) + 1)][::-1]
            elif period == 'Month':
                date_range = []
                today = fields.Date.today()
                for i in range(1, int(dur) + 2):
                    start_date = date_utils.start_of(today, 'month')
                    end_date = date_utils.end_of(today, 'month')
                    today = fields.Datetime.subtract(
                        date_utils.start_of(today, 'month'), days=1)
                    date_range.append((start_date, end_date))
                date_range = date_range[1:][::-1]
            date_range_formatted = [
                (start_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y"))
                for start_date, end_date in date_range]
            data_list = [pd.DataFrame(self._execute_query(year, i)) for i, year
                         in enumerate(date_range, start=1)]
            return self.predict_churn(
                *data_list,
                dates=date_range_formatted,
                date_range=date_range
            )

    def get_xlsx_report(self, data, response):
        """ Generate an Excel report based on churn prediction data and send it as a response."""
        data = json.loads(data)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        header = workbook.add_format({'bold': True, 'align': 'center'})
        head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '15px'})
        subhead = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '15px'})
        cell = workbook.add_format({'align': 'center'})
        row = 7
        column = 0
        if data['churnData']['predict']:
            sheet.merge_range('A2:H3', 'CHURN PREDICTION REPORT', head)
            sheet.merge_range('A4:H5',
                              f"Prediction based on last {data['numberOfPeriods']} {data['period']}s"
                              f" ({data['churnData']['date_range'][0][0]} to {data['churnData']['date_range'][-1][1]})",
                              subhead)
            sheet.write(row, column, 'Sl.no', header)
            column += 1
            sheet.write(row, column, 'Customer', header)
            column += 1
            sheet.write(row, column, 'Last Purchase Date', header)
            column += 1
            sheet.write(row, column, 'Total Sale Orders', header)
            column += 1
            sheet.write(row, column, 'Total Amount', header)
            column += 1
            sheet.write(row, column, 'Churn', header)
            column += 1
            sheet.write(row, column, 'Probability of Churn', header)
            column += 1
            sheet.write(row, column, 'Probability of Not Churn', header)
            column += 1
            sheet.set_column(1, 1, 30)
            sheet.set_column(2, 2, 20)
            sheet.set_column(3, 3, 20)
            sheet.set_column(4, 4, 20)
            sheet.set_column(5, 5, 20)
            sheet.set_column(6, 6, 20)
            sheet.set_column(7, 7, 25)
            row += 1
            number = 1
            for data in data['churnData']['cust_wise_details']:
                sheet.write(row, 0, number, cell)
                sheet.write(row, 1, data['custName'], cell)
                sheet.write(row, 2, data['last_purchase_date'], cell)
                sheet.write(row, 3, data['total_sales'], cell)
                sheet.write(row, 4, data['total_amount'], cell)
                sheet.write(row, 5, data['Churn'], cell)
                sheet.write(row, 6, f"{data['prob_yes']}%", cell)
                sheet.write(row, 7, f"{data['prob_no']}%", cell)
                number += 1
                row += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
