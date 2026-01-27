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
import warnings

import pandas as pd
import xlsxwriter
from odoo import api, models
from prophet import Prophet

warnings.filterwarnings('ignore')


class SaleOrderInheritClass(models.Model):
    """ This class inherits from 'sale.order' model and extends its functionality."""

    _inherit = 'sale.order'

    @api.model
    def forecast_configure(self, *args):
        """  Configure and generate sales forecast using Prophet based on provided parameters."""
        period_filter = args[0].get('period') if args and args[0].get(
            'period') else 30
        frequency = args[0].get('frequency') if args and args[0].get(
            'frequency') else 'D'
        start_date = datetime.date.today() - datetime.timedelta(days=60)
        end_date = datetime.date.today()
        if args[0].get('start_date') and args[0].get('end_date'):
            search_params = [
                ('date_order', '>=', args[0].get('start_date')),
                ('date_order', '<=', args[0].get('end_date'))]
        elif args[0].get('start_date'):
            search_params = [('date_order', '>=', args[0].get('start_date'))]
        else:
            search_params = [('date_order', '>=', start_date),
                             ('date_order', '<=', end_date)]
        search_params.append(('state', '=', 'sale'))
        sales_data = {}
        sale_orders = self.env['sale.order'].search(
            search_params,
            order='date_order asc')
        for order in sale_orders:
            if order.date_order.date() in sales_data:
                sales_data[str(order.date_order.date())] += order.amount_total
            else:
                sales_data[
                    str(order.date_order.date())] = order.amount_total

        if frequency == 'D':
            df = pd.DataFrame(list(sales_data.items()), columns=['ds', 'y'])
            sales_data_dict = df.set_index('ds')['y'].to_dict()
        else:
            df = pd.DataFrame(list(sales_data.items()), columns=['ds', 'y'])
            df['ds'] = pd.to_datetime(df['ds'])
            grouped = df.resample(frequency, on='ds').agg(
                {'y': 'sum'}).reset_index()
            df = pd.DataFrame({'ds': grouped['ds'], 'y': grouped['y']})
            sales_data_dict = dict(
                zip(df['ds'].dt.strftime('%Y-%m-%d'), df['y']))
        if len(sales_data) > 5:
            return self.prophet_forecast(df, period_filter, frequency,
                                         sales_data_dict, start_date, end_date)
        else:
            return False

    def prophet_forecast(self, df, period_filter, frequency, sales_data_dict,
                         start_date, end_date):
        """Generate a forecast using the Prophet library based on historical sales data."""
        try:
            if len(df) >= 1:
                m = Prophet()
                m.fit(df)
                future_period = m.make_future_dataframe(
                    periods=int(period_filter), freq=frequency)
                future_period = future_period.iloc[len(df):]
                forecast = m.predict(future_period)
                forecast_dict = {}
                for key, value in zip(forecast['ds'], forecast['yhat']):
                    rounded_value = round(value, 0)
                    forecast_dict[str(key.date())] = rounded_value
                chart_data = {}
                chart_data.update(sales_data_dict)
                chart_data.update(forecast_dict)
                sales_data_dict = [{'date': date, 'value': value} for
                                   date, value in sales_data_dict.items()]
                forecast_dict = [{'date': date, 'value': value} for date, value
                                 in forecast_dict.items()]
                return chart_data, len(
                    sales_data_dict), start_date, end_date, sales_data_dict, forecast_dict
        except ValueError as e:
            return False, e

    @api.model
    def product_demand_forecast(self, date, prod):

        """  Generate a forecast for product demand based on historical sales data."""
        global prop_input, prop_output, demand_act_data
        actual_start_date = date.get('actStartDate') if date.get(
            'actStartDate') else (datetime.date.today() -
                                  datetime.timedelta(days=30))
        actual_end_date = date.get('actEndDate') if date.get(
            'actEndDate') else datetime.date.today()
        periods = date.get('period') if date.get('period') else 10
        frequency = date.get('frequency') if date.get('frequency') else 'D'
        search_params = [('order_id.state', '=', 'sale'),
                         ('order_id.date_order', '>=', actual_start_date),
                         ('order_id.date_order', '<=', actual_end_date)]
        sale_order_lines = self.env['sale.order.line'].search(search_params)
        prod_list = sorted([{rec.id: [rec.id, rec.display_name]} for rec in
                            sale_order_lines.mapped('product_id')],
                           key=lambda x: list(x.keys())[0])
        if prod_list:
            if not prod:
                prod = list(prod_list[0].values())[0]
        else:
            return False
        data = [{'name': order_line.product_id.display_name,
                 'date': order_line.order_id.date_order.date(),
                 'qty': order_line.product_uom_qty,
                 'unit_price': order_line.price_unit,
                 'sub_total': order_line.price_subtotal
                 } for order_line in sale_order_lines.filtered(
            lambda rec: rec.product_id.id == prod[0])]

        df = pd.DataFrame(data)
        df.sort_values(by='date', ascending=True)
        daily = df.groupby('date').agg(
            {'qty': 'sum', 'sub_total': 'sum'}).reset_index()
        daily['avg_price'] = (daily['sub_total'] / daily['qty']).where(
            daily['qty'] != 0, 0).round(2)
        daily['date'] = daily['date'].astype(str)
        daily[['sub_total', 'avg_price']] = daily[
            ['sub_total', 'avg_price']].round(2)
        # data for arima model
        sales_data = df.groupby('date').agg(
            {'qty': 'sum', 'sub_total': 'sum'}).reset_index()
        sales_data = sales_data.rename(
            columns={'qty': 'total_qty', 'unit_price': 'avg_unit_price'})
        sales_data['date'] = pd.to_datetime(sales_data['date'])
        actual_data = sales_data
        actual_data = actual_data.drop(columns=['sub_total'])
        actual_data = actual_data.rename(
            columns={'date': 'ds', 'total_qty': 'y'})
        daily['date'] = pd.to_datetime(daily['date'])
        if frequency == 'D':
            daily['date'] = pd.to_datetime(daily['date']).dt.strftime(
                '%Y/%m/%d')
            # data for prophet model
            prop_input = actual_data
        else:  # Handles M and Y cases here
            daily = daily.resample(frequency, on='date').agg(
                {'qty': 'sum', 'sub_total': 'sum'})
            daily['avg_price'] = (daily['sub_total'] / daily['qty']).where(
                daily['qty'] != 0, 0).round(2)
            date_format = "%Y %b" if frequency == "M" else "%Y"
            daily = daily.reset_index()
            daily['date'] = daily['date'].dt.strftime(date_format)
            prop_input = actual_data.groupby(
                pd.Grouper(key='ds', freq=frequency)).sum().reset_index()
        demand_act_data = daily.to_dict(orient='records')
        if len(prop_input) >= 10:
            try:
                prod_price = df['unit_price'].mean()
                model = Prophet()
                model.fit(prop_input)
                future_pred = model.make_future_dataframe(
                    periods=int(periods),
                    freq=frequency
                )
                future_pred = future_pred.iloc[len(prop_input):]
                forecast = model.predict(future_pred)
                forecast_dict_list = []
                for key, value in zip(forecast['ds'], forecast['yhat']):
                    rounded_value = round(value, 0)
                    forecast_dict = {
                        'date': str(key.date()),
                        'qty': rounded_value,
                        'subtotal': round(rounded_value * prod_price, 2),
                        'avg_price': round(prod_price, 2),
                    }
                    forecast_dict_list.append(forecast_dict)
                no_data = True
            except:
                return False
            forecast_dict_list = pd.DataFrame(forecast_dict_list)
            forecast_dict_list['date'] = pd.to_datetime(
                forecast_dict_list['date'])
            if frequency == 'D':
                forecast_dict_list['date'] = pd.to_datetime(
                    forecast_dict_list['date']).dt.strftime('%Y/%m/%d')
            else:
                date_format = "%Y %b" if frequency == "M" else "%Y"
                forecast_dict_list['date'] = forecast_dict_list[
                    'date'].dt.strftime(date_format)
            demand_fore_data = forecast_dict_list.to_dict(orient='records')
            chart_data = demand_act_data + demand_fore_data
        else:
            no_data = False
            demand_fore_data = []
            chart_data = []
        vals = {
            'product_list': prod_list,
            'current_product': prod,
            'table_act_data': demand_act_data,
            'table_fore_data': demand_fore_data,
            'start_date': actual_start_date,
            'end_date': actual_end_date,
            'no_data': no_data,
            'chart_data': chart_data
        }
        return vals

    def get_xlsx_report(self, data, response):
        """ Generate an Excel report based on demand prediction data."""

        data = json.loads(data)
        if data['frequency'] == 'D':
            frequency = 'Days'
        elif data['frequency'] == 'M':
            frequency = 'Months'
        else:
            frequency = 'Years'
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()

        main_head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '15px'})
        sub_head = workbook.add_format(
            {'align': 'center', 'bold': True, 'font_size': '13px'})
        sub_head1 = workbook.add_format(
            {'align': 'left', 'bold': True, 'font_size': '13px'})
        header = workbook.add_format({'bold': True, 'align': 'center'})
        table_data = workbook.add_format(
            {'align': 'center', 'font_size': '12px'})
        sheet.merge_range('B2:J3', 'DEMAND PREDICTION REPORT', main_head)
        sheet.merge_range('B5:J6',
                          f"Actual Sales is from {data['start_date']} to {data['end_date']} & Predicted Demand"
                          f" for {data['period']} {frequency}", sub_head)
        sheet.merge_range('B8:F9', f"Product : {data['product']}", sub_head1)
        sheet.merge_range('B11:E12', 'ACTUAL SALES', sub_head)
        sheet.merge_range('G11:J12', 'PREDICTED SALES', sub_head)
        row = 13
        column = 1
        sheet.set_column(1, 4, 20)
        sheet.set_column(6, 9, 20)
        sheet.set_row(13, height=30)
        sheet.write(row, column, 'Periods', header)
        column += 1
        sheet.write(row, column, 'Quantity Sold', header)
        column += 1
        sheet.write(row, column, 'Average Sales Price', header)
        column += 1
        sheet.write(row, column, 'Revenue', header)
        column += 2
        sheet.write(row, column, 'Periods', header)
        column += 1
        sheet.write(row, column, 'Quantity Sold', header)
        column += 1
        sheet.write(row, column, 'Average Sales Price', header)
        column += 1
        sheet.write(row, column, 'Revenue', header)
        row = 14
        new_row1 = row + 1
        for each in data['actual']:
            sheet.write('B%s' % new_row1, each['date'], table_data)
            sheet.write('C%s' % new_row1, each['qty'], table_data)
            sheet.write('D%s' % new_row1, each['sub_total'], table_data)
            sheet.write('E%s' % new_row1, each['avg_price'], table_data)
            new_row1 += 1
        row_num = 14
        new_row2 = row_num + 1
        for eachitem in data['predict']:
            sheet.write('G%s' % new_row2, eachitem['date'], table_data)
            sheet.write('H%s' % new_row2, eachitem['qty'], table_data)
            sheet.write('I%s' % new_row2, eachitem['subtotal'], table_data)
            sheet.write('J%s' % new_row2, eachitem['avg_price'], table_data)
            new_row2 += 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
