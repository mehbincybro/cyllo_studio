# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    """ Inherited Account.move.line for the Analytic Distribution Checking"""
    _inherit = 'account.move.line'

    @api.constrains('analytic_distribution')
    def _check_analytic_distribution(self):
        """Constraints for checking Analytic Distribution"""
        for record in self.filtered(lambda x: x.analytic_distribution):
            analytic_distribution = [int(line) for line in record.analytic_distribution.keys()]
            for line in record.analytic_distribution.keys():
                if line:
                    line_analytic = self.env['account.analytic.account'].browse(int(line))
                    if (line_analytic.analytic_account_id and line_analytic.analytic_account_id.id in
                            analytic_distribution):
                        raise ValidationError(
                            _(f'The {line_analytic.name} Account`s Parent {line_analytic.analytic_account_id.name} '
                              f'already included in the Analytic Distribution.You can`t choose parent account with '
                              f'child account in a same move line.'))
                    elif line_analytic.analytic_account_ids:
                        for analytic_line in line_analytic.analytic_account_ids:
                            if analytic_line.id in analytic_distribution:
                                raise ValidationError(
                                    _(f'The {line_analytic.name} Account`s Child {analytic_line.name} already '
                                      f'included in the Analytic Distribution.You can`t choose Child account with '
                                      f'Parent account in a same move line.'))
