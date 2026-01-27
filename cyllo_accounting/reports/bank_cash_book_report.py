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

LIMIT = 100


class BankBookReport(models.AbstractModel):
    """
        This model for generating the Account Bank Book Report.
    """
    _name = 'bank.cash.book.report'
    _description = 'Account Bank/Cash Book Report'

    @api.model
    def get_partner(self, journal_type):
        """
        Get partner IDs associated with the specified journal type.

        Args:
            journal_type (str): Type of journal.

        Returns:
            list: List of partner IDs associated with the specified journal type.
        """
        journal = self.env['account.journal'].search([('type', '=', journal_type)])
        account_move_line_ids = self.env['account.move.line'].search(
            [('parent_state', '=', 'posted'), ('journal_id', 'in', journal.ids)])
        partner_ids = account_move_line_ids.mapped('partner_id')
        return partner_ids.ids

    @api.model
    def get_account_data(self, journal_type, **kwargs):
        """
        Get account data based on the specified journal type and optional filter criteria.

        Args:
            journal_type (str): Type of journal.
            **kwargs: Optional keyword arguments for additional filtering and configuration.
                - account_id (int, optional): ID of the account to filter by.
                - limit (int, optional): Maximum number of records to retrieve.
                - offset (int, optional): Offset for pagination.
                - account_name (str, optional): Name of the account to filter by.

        Returns:
            list: Account data based on the specified criteria.
        """
        account_id = kwargs.get('account_id', False)
        limit = kwargs.get('limit', LIMIT)
        offset = kwargs.get('offset', 0)
        account_name = kwargs.get('account_name', False)
        journals = self.env['account.journal'].search(
            [('type', '=', journal_type)])
        domain = self.get_domain(journals, **kwargs)
        return self._get_account_entries(account_id, domain, account_name, limit, offset)

    def _get_account_entries(self, account_type_id, domain, account_name, limit=LIMIT, offset=0):
        """
        Get account entries based on the specified account type ID and domain.

        Args:
            account_type_id (int): ID of the account type.
            domain (list): List of domain conditions for filtering account entries.
            account_name (str): Name of the account.
            limit (int, optional): Maximum number of records to retrieve. Defaults to LIMIT.
            offset (int, optional): Offset for pagination. Defaults to 0.

        Returns:
            tuple: A tuple containing:
                - list: Account entries based on the specified criteria.
                - float: Total debit amount for the account entries.
                - float: Total credit amount for the account entries.
                - float: Total balance (debit - credit) for the account entries.
                - dict: Information about the account entries including limit, offset, account ID, and total count.
        """
        new_domain = domain + [('account_id', '=', account_type_id)]
        account_entries_total = self.env['account.move.line'].search(new_domain)
        account_entries = self.env['account.move.line'].search_read(new_domain,
                                                                    ['date', 'journal_id', 'partner_id', 'move_name',
                                                                     'debit', 'annotations', 'account_id',
                                                                     'move_id', 'credit', 'name', 'ref'],
                                                                    # )
                                                                    limit=limit, offset=offset)
        [entry.update({'balance': entry.get('debit') - entry.get('credit')}) for entry in account_entries]
        acc_total_debit = sum(entry.debit for entry in account_entries_total)
        acc_total_credit = sum(entry.credit for entry in account_entries_total)
        acc_total_balance = acc_total_debit - acc_total_credit
        return account_entries, acc_total_debit, acc_total_credit, acc_total_balance, {
            account_name: {"limit": limit, "offset": offset, "account_id": account_type_id,
                           "total": len(
                               account_entries_total)}}

    def get_domain(self, journals, **filter_kwargs):
        """
            Construct a domain based on the provided journals and optional filter criteria.

            Args:
                journals (recordset): Recordset of account journals.
                **filter_kwargs: Optional keyword arguments for additional filtering and configuration.

            Returns:
                list: A list representing the domain for search queries.
        """
        startDate = filter_kwargs.get('startDate', None)
        endDate = filter_kwargs.get('endDate', None)
        partners = filter_kwargs.get('partners', [])
        accounts = filter_kwargs.get('accounts', [])
        parent_state = filter_kwargs.get('parent_state')
        domain = [('journal_id', 'in', journals.ids)]
        if parent_state:
            domain.append(('parent_state', 'in', parent_state))
        if accounts:
            domain.append(('account_id', 'in', accounts))
        if partners:
            domain.append(('partner_id', 'in', partners))
        if startDate and endDate:
            domain.extend([('date', '>=', startDate),
                           ('date', '<=', endDate)])
        elif startDate:
            domain.extend([('date', '>=', startDate)])
        elif endDate:
            domain.extend([('date', '<=', endDate)])
        return domain

    @api.model
    def get_report(self, journal_type, **filter_kwargs):
        """
            Get a report based on the specified journal type and optional filter criteria.

            Args:
                journal_type (str): Type of journal.
                **filter_kwargs: Optional keyword arguments for additional filtering and configuration.

            Returns:
                dict: A dictionary containing various data for the report including account details,
                      total debit, total credit, total balance, account entries, and currency ID.
        """
        data = {}
        journals = self.env['account.journal'].search(
            [('type', '=', journal_type)])
        domain = self.get_domain(journals, **filter_kwargs)
        account_move_lines = self.env['account.move.line'].search(domain, order="date desc")
        all_account_move_lines = self.env['account.move.line'].search(
            [('parent_state', '=', 'posted'),
             ('journal_id', 'in', journals.ids)], order="date desc")
        data['accounts'] = account_move_lines.mapped('account_id').read(
            ['display_name', 'name'])
        data['all_account'] = all_account_move_lines.mapped('account_id').read(
            ['display_name', 'name'])
        currency_id = self.env.company.currency_id.symbol
        data['total_debit'] = round(sum(entry.debit for entry in account_move_lines), 2)
        data['total_credit'] = round(sum(entry.credit for entry in account_move_lines), 2)
        data['total_balance'] = data['total_debit'] - data['total_credit']
        limit = filter_kwargs.get('limit', LIMIT) if not filter_kwargs.get('is_report', False) else 0
        offset = filter_kwargs.get('offset', 0)
        data['account_entries'] = {
            account_type.get('display_name'): self._get_account_entries(account_type.get('id'), domain,
                                                                        account_type.get('display_name'), limit, offset)
            for account_type in data['accounts']}
        data['currency_id'] = currency_id
        return data
