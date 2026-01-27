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
from odoo import api, models

PARTNER_LIMIT = 50
MOVE_LINE_LIMIT = 100


class PartnerLedgerReport(models.AbstractModel):
    """
        This model for generating the Partner Ledger Report.
    """
    _name = 'partner.ledger.report'
    _description = 'Partner Ledger Report'

    @api.model
    def get_partner(self):
        """Returning partners who have the record"""
        move_line_ids = self.env['account.move.line'].search(
            [('account_type', 'in',
              ['liability_payable', 'asset_receivable']),
             ('parent_state', '=', 'posted')])
        partner_ids = move_line_ids.mapped('partner_id')
        return partner_ids.ids

    @api.model
    def get_report(self, offset=0, limit=PARTNER_LIMIT, **kwargs):
        """
        Retrieve partner-related data for generating a report.
        :return: A dictionary containing the partner data for the report.
        :rtype: Dict
        """
        partner_id = kwargs.get('partner_id') or []
        is_report = kwargs.get('is_report', False)
        company_ids = kwargs.get('company_id', [])
        pager = kwargs.get('pager', False)
        domain = self.get_domain(**kwargs)
        partner_dict = {}
        partner_totals = {}
        if not partner_id:
            partner_query = """SELECT DISTINCT partner.id
                               FROM res_partner AS partner
                                        INNER JOIN account_move_line AS move_line
                                                   ON partner.id = move_line.partner_id
                                        INNER JOIN account_account AS account
                                                   ON move_line.account_id = account.id
                               WHERE move_line.parent_state in %s
                                 AND move_line.date >= %s
                                 AND move_line.date <= %s
                                 AND account.account_type in %s;"""
            params = (domain['parent_state_domain'], domain['startDate'] or None,
                      domain['endDate'] or None, domain['account_type'])
            self.env.cr.execute(partner_query, params)
            partner_res = self.env.cr.fetchall()
            all_partner_ids = [item[0] for item in partner_res]
            partner_id = all_partner_ids if is_report else all_partner_ids[offset:offset + limit]

        else:
            all_partner_ids = partner_id
        totalDebitSum = 0
        totalCreditSum = 0
        currency_id = self.env.company.currency_id.symbol
        for partners in partner_id:
            query = """SELECT move_line.id,
                              move_line.date,
                              move_line.move_name,
                              account.account_type,
                              move_line.debit,
                              move_line.credit,
                              move_line.date_maturity,
                              move_line.account_id,
                              move_line.journal_id,
                              partner.id      partner_id,
                              move_line.move_id,
                              move_line.matching_number,
                              move_line.amount_currency,
                              move_line.currency_id,
                              move_line.annotations,
                              move_line.name,
                              journal.code as jrnl,
                              account.code as code,
                              partner.name    partner_name
                       FROM account_move_line move_line
                                INNER JOIN
                            res_partner partner ON move_line.partner_id = partner.id
                                INNER JOIN
                            account_account account ON move_line.account_id = account.id
                                INNER JOIN
                            account_journal journal ON move_line.journal_id = journal.id
                       WHERE move_line.partner_id = %s
                         AND parent_state IN %s
                         AND move_line.date >= %s
                         AND move_line.date <= %s
                         AND account.account_type IN %s"""
            if company_ids:
                if len(company_ids) > 1:
                    query += f""" AND move_line.company_id IN {tuple(company_ids)}"""
                else:
                    query += f""" AND move_line.company_id = {company_ids[0]}"""
            if not is_report:
                query += f""" LIMIT {limit}  OFFSET  {offset}"""

            params = (
                partners, domain['parent_state_domain'], domain['startDate'], domain['endDate'],
                domain['account_type'])
            self.env.cr.execute(query, params)
            res = self.env.cr.dictfetchall()
            if pager:
                return res
            partner = self.env['res.partner'].browse(partners).id
            move_lines = """SELECT move_line.name,
                                   move_line.id,
                                   move_line.account_id,
                                   move_line.credit,
                                   move_line.debit
                            FROM account_move_line move_line
                                     INNER JOIN
                                 res_partner AS partner ON partner.id = move_line.partner_id
                                     INNER JOIN
                                 account_account AS account ON move_line.account_id = account.id
                            WHERE move_line.parent_state in %s
                              AND move_line.date >= %s
                              AND move_line.date <= %s
                              AND account.account_type in %s
                              AND partner.id = %s \
                         """
            params = (domain['parent_state_domain'], domain['startDate'], domain['endDate'],
                      domain['account_type'], partners)
            self.env.cr.execute(move_lines, params)
            filtered_move_line_ids = self.env.cr.dictfetchall()
            partner_dict[partner] = res
            partner_totals[partner] = {
                'total_debit': round(sum(item['debit'] for item in filtered_move_line_ids), 2),
                'total_credit': round(sum(item['credit'] for item in filtered_move_line_ids), 2),
                'currency_id': currency_id,
                'partner_id': partners,
                'partner_name': self.env['res.partner'].browse(partners).name,
                'move_lines': res,
                'move_lines_count': len(filtered_move_line_ids),
            }
            partner_dict['partner_totals'] = partner_totals
            totalDebitSum += partner_totals[partner]['total_debit']
            totalCreditSum += partner_totals[partner]['total_credit']
            currency_id = partner_totals[partner]['currency_id']
        partner_dict['totalDebitSum'] = totalDebitSum
        partner_dict['totalCreditSum'] = totalCreditSum
        partner_dict['currency_id'] = currency_id
        return partner_dict, all_partner_ids

    @staticmethod
    def get_domain(**kwargs):
        """Date Domain"""
        startDate = kwargs.get('startDate', None)
        endDate = kwargs.get('endDate', None)
        parent_state = kwargs.get('parent_state') or None
        account = kwargs.get('account_type') or None
        account_type_domain = []
        parent_state_domain = ['posted'] if parent_state is None else ['posted',
                                                                       'draft'] if 'draft' in parent_state else [
            'posted']
        if account is None or ('Receivable' in account and 'Payable' in account):
            account_type_domain.extend(['liability_payable', 'asset_receivable'])
        elif 'Receivable' in account:
            account_type_domain.append('asset_receivable')
        elif 'Payable' in account:
            account_type_domain.append('liability_payable')
        domain = {
            'account_type': tuple(account_type_domain),
            'parent_state_domain': tuple(parent_state_domain),
            'startDate': startDate,
            'endDate': endDate
        }
        return domain
