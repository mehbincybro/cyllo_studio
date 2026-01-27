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
from datetime import datetime

from odoo import api, models

FIELDS = ['name', 'move_name', 'date', 'amount_currency', 'account_id',
          'date_maturity', 'currency_id', 'debit', 'credit', 'move_id', 'annotations', 'partner_id']
PARTNER_LIMIT = 50
MOVE_LINE_LIMIT = 100


class AgePayableReceivableReport(models.AbstractModel):
    """Model for generating Aged Payable Receivable Report."""
    _name = 'aged.payable.receivable.report'
    _description = 'Aged Payable Receivable Report'

    @api.model
    def get_report(self, account_type=None, offset=0, limit=PARTNER_LIMIT, **filter_kwargs):
        """Generates the aged payable receivable report.
           :param str account_type: The type of the account.
           :param int offset: Offset for pagination.
           :param int limit: Limit for pagination.
           :param dict filter_kwargs: Filter parameters.
           :return: Dictionary containing report values.
           :rtype: dict
        """
        partner_totals = []
        is_report = filter_kwargs.get('is_report', False)

        partner_data = self.get_partners(account_type, **filter_kwargs)
        currency_id = self.env.company.currency_id.symbol

        partners_dict = partner_data if is_report else partner_data[offset:offset + limit]

        for partner in partners_dict:
            move_line_data = self.get_partner_move_lines(partner['id'], account_type, **filter_kwargs)
            partner_line_total = self.get_partner_ml_total(partner['id'], account_type, **filter_kwargs)

            partner_totals.append({
                **partner_line_total,
                'move_lines': move_line_data if is_report else move_line_data[0:MOVE_LINE_LIMIT],
                'move_lines_count': len(move_line_data),
                'currency_id': currency_id,
                'partner': partner['name'],
                'partner_id': partner['id'],
            })
        partner_ids = [partner['id'] for partner in partners_dict]
        grand_total = self.get_grand_total(partner_ids, account_type, **filter_kwargs)
        grand_total['currency'] = currency_id

        move_line_list = {
            'partner_totals': partner_totals,
            'grand_total': grand_total,
            'partners': partners_dict if is_report else [partner['id'] for partner in partner_data]
        }

        return move_line_list

    @api.model
    def get_partner_move_lines(self, partner_id=None, account_type=None, offset=0, limit=MOVE_LINE_LIMIT,
                               **filter_kwargs):
        """Retrieves move lines for a partner.
            :param int partner_id: The ID of the partner.
            :param str account_type: The type of the account.
            :param int offset: Offset for pagination.
            :param int limit: Limit for pagination.
            :param dict filter_kwargs: Filter parameters.
            :return: List of move lines.
            :rtype: list
        """
        date_str = filter_kwargs.get('date')
        company_ids = filter_kwargs.get('company_ids', [])

        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        is_pagination = False
        if not partner_id:
            is_pagination = True
            partner_id = filter_kwargs.get('partners', None)
        query = """
            SELECT
                line.id,
                line.name,
                line.move_name,
                line.date_maturity,
                line.date,
                line.amount_currency,
                account.name as account_name,
                account.code as account_code,
                currency.name as amount_currency_name,
                currency.symbol as amount_currency_symbol,
                line.debit,
                line.credit,
                line.move_id,
                line.annotations,
                line.partner_id,
                CASE
                    WHEN EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 <= 0 THEN 
                        CASE
                            WHEN line.debit <> 0 THEN line.debit
                            ELSE -1 * line.credit
                        END
                    ELSE 0.0
                END AS diff0,
                CASE
                    WHEN EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 > 0 AND EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 <= 30 THEN 
                        CASE
                            WHEN line.debit <> 0 THEN line.debit
                            ELSE -1 * line.credit
                        END
                    ELSE 0.0
                END AS diff1,
                CASE
                    WHEN EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 > 30 AND EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 <= 60 THEN 
                        CASE
                            WHEN line.debit <> 0 THEN line.debit
                            ELSE -1 * line.credit
                        END
                    ELSE 0.0
                END AS diff2,
                CASE
                    WHEN EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 > 60 AND EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 <= 90 THEN 
                        CASE
                            WHEN line.debit <> 0 THEN line.debit
                            ELSE -1 * line.credit
                        END
                    ELSE 0.0
                END AS diff3,
                CASE
                    WHEN EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 > 90 AND EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 <= 120 THEN 
                        CASE
                            WHEN line.debit <> 0 THEN line.debit
                            ELSE -1 * line.credit
                        END
                    ELSE 0.0
                END AS diff4,
                CASE
                    WHEN EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 > 120 THEN 
                        CASE
                            WHEN line.debit <> 0 THEN line.debit
                            ELSE -1 * line.credit
                        END
                    ELSE 0.0
                END AS diff5
            FROM
                account_move_line as line
            INNER JOIN account_account as account ON account.id = line.account_id and account.account_type = %(account_type)s
            INNER JOIN res_currency as currency ON currency.id = line.currency_id
                WHERE
                    line.parent_state = 'posted'
                    AND line.reconciled = FALSE
                    AND line.date <= %(date)s 
                    AND line.partner_id = %(partner_id)s
                    AND line.company_id IN %(company_ids)s
                    ORDER BY line.date
        """
        if is_pagination:
            query += """ OFFSET %(offset)s LIMIT %(limit)s;"""

        params = {'date': date, 'partner_id': partner_id, 'account_type': account_type,
                  'company_ids': tuple(company_ids), 'offset': offset, 'limit': limit}
        self.env.cr.execute(query, params)
        return self.env.cr.dictfetchall()

    def get_partners(self, account_type, **filter_kwargs):
        """Retrieves partners for the report.
            :param str account_type: The type of the account.
            :param dict filter_kwargs: Filter parameters.
            :return: List of partners.
            :rtype: list
        """
        company_ids = filter_kwargs.get('company_ids', [])
        date_str = filter_kwargs.get('date')
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        partners = filter_kwargs.get('partners', [])
        query = """
            SELECT DISTINCT partner.id, partner.name FROM res_partner as partner
            INNER JOIN account_move_line as line ON line.partner_id = partner.id
            INNER JOIN account_account as account ON account.id = line.account_id
            WHERE
                    line.parent_state = 'posted'
                    AND line.reconciled = FALSE
                    AND account.account_type = %(account_type)s
                    AND line.date <= %(date)s 
                    AND line.company_id IN %(company_ids)s
        """
        if partners:
            query += """ AND partner.id in %(partners)s"""
        params = {'date': date, 'account_type': account_type, 'partners': tuple(partners),
                  'company_ids': tuple(company_ids)}
        self.env.cr.execute(query, params)

        partner_data = self.env.cr.dictfetchall()
        return partner_data

    @api.model
    def get_partner_ml_total(self, partner_id=None, account_type=None, **filter_kwargs):
        """Retrieves the total for move lines of a partner.
           :param int partner_id: The ID of the partner.
           :param str account_type: The type of the account.
           :param dict filter_kwargs: Filter parameters.
           :return: Dictionary containing total values.
           :rtype: dict
       """
        company_ids = filter_kwargs.get('company_ids', [])
        date_str = filter_kwargs.get('date')
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        query = self._get_total_query
        query += """
                  SUM(CASE
                      WHEN line.debit <> 0 THEN line.debit
                      ELSE -1 * line.credit
                  END) AS sub_total
              FROM
                  account_move_line as line
              INNER JOIN account_account as account ON account.id = line.account_id and account.account_type = %(account_type)s
                  WHERE
                      line.parent_state = 'posted'
                      AND line.reconciled = FALSE
                      AND line.date <= %(date)s 
                      AND line.partner_id = %(partner_id)s
                      AND line.company_id IN %(company_ids)s
          """

        params = {'date': date, 'partner_id': partner_id, 'account_type': account_type,
                  'company_ids': tuple(company_ids)}
        self.env.cr.execute(query, params)

        partner_ml_total = self.env.cr.dictfetchone()
        return partner_ml_total

    def get_grand_total(self, partner_ids, account_type, **filter_kwargs):
        """Retrieves the grand total for all partners.
           :param list partner_ids: The IDs of the partners.
           :param str account_type: The type of the account.
           :param dict filter_kwargs: Filter parameters.
           :return: Dictionary containing grand total values.
           :rtype: dict
       """
        company_ids = filter_kwargs.get('company_ids', [])
        date_str = filter_kwargs.get('date')
        date = datetime.strptime(date_str, "%Y-%m-%d").date()

        if not partner_ids:
            return {
                    'diff0_sum': 0.0,
                    'diff1_sum': 0.0,
                    'diff2_sum': 0.0,
                    'diff3_sum': 0.0,
                    'diff4_sum': 0.0,
                    'diff5_sum': 0.0,
                    'total': 0.0,
                }
        query = self._get_total_query
        query += """
                      SUM(CASE
                          WHEN line.debit <> 0 THEN line.debit
                          ELSE -1 * line.credit
                      END) AS total
                      FROM
                          account_move_line as line
                      INNER JOIN account_account as account ON account.id = line.account_id and account.account_type = %(account_type)s
                          WHERE
                              line.parent_state = 'posted'
                              AND line.reconciled = FALSE
                              AND line.date <= %(date)s 
                              AND line.partner_id IN %(partner_id)s
                              AND line.company_id IN %(company_ids)s
                  """

        params = {'date': date, 'partner_id': tuple(partner_ids), 'account_type': account_type,
                  'company_ids': tuple(company_ids)}
        self.env.cr.execute(query, params)

        grand_total = self.env.cr.dictfetchone()
        return grand_total

    @property
    def _get_total_query(self):
        """Constructs and returns base query for both partner move line totals and the grand total.
        :return: Starting SQL query string.
        :rtype: str
        """
        return """
            SELECT
              SUM(CASE
                  WHEN EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 <= 0 THEN 
                      CASE
                          WHEN line.debit <> 0 THEN line.debit
                          ELSE -1 * line.credit
                      END
                  ELSE 0.0
              END) AS diff0_sum,
              SUM(CASE
                  WHEN EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 > 0 AND EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 <= 30 THEN 
                      CASE
                          WHEN line.debit <> 0 THEN line.debit
                          ELSE -1 * line.credit
                      END
                  ELSE 0.0
              END) AS diff1_sum,
              SUM(CASE
                  WHEN EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 > 30 AND EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 <= 60 THEN 
                      CASE
                          WHEN line.debit <> 0 THEN line.debit
                          ELSE -1 * line.credit
                      END
                  ELSE 0.0
              END) AS diff2_sum,
              SUM(CASE
                  WHEN EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 > 60 AND EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 <= 90 THEN 
                      CASE
                          WHEN line.debit <> 0 THEN line.debit
                          ELSE -1 * line.credit
                      END
                  ELSE 0.0
              END) AS diff3_sum,
              SUM(CASE
                  WHEN EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 > 90 AND EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 <= 120 THEN 
                      CASE
                          WHEN line.debit <> 0 THEN line.debit
                          ELSE -1 * line.credit
                      END
                  ELSE 0.0
              END) AS diff4_sum,
              SUM(CASE
                  WHEN EXTRACT(EPOCH FROM AGE(%(date)s, COALESCE(line.date_maturity, line.date))) / 86400 > 120 THEN 
                      CASE
                          WHEN line.debit <> 0 THEN line.debit
                          ELSE -1 * line.credit
                      END
                  ELSE 0.0
              END) AS diff5_sum,
        """
