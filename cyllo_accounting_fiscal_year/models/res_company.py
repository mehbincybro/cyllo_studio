# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import models
from odoo.tools import date_utils


class ResCompany(models.Model):
    """Inheriting company model for compute fiscal year dates"""
    _inherit = "res.company"

    def compute_fiscalyear_dates(self, current_date):
        """This method returns the calendar year.
        :param current_date: A datetime.date/datetime.datetime object.
        :return: A dictionary containing:
            * date_from
            * date_to
        """
        self.ensure_one()
        fiscalyear = self.env["account.fiscal.year"].search(
            [("company_id", "=", self.id), ("start_date", "<=", current_date), ("end_date", ">=", current_date)],
            limit=1)
        if fiscalyear:
            return {
                "date_from": fiscalyear.start_date,
                "date_to": fiscalyear.end_date,
                "record": fiscalyear,
            }
        date_from, date_to = date_utils.get_fiscal_year(current_date, day=self.fiscalyear_last_day,
                                                        month=int(self.fiscalyear_last_month))
        fiscal_year_from = self.env["account.fiscal.year"].search(
            [("company_id", "=", self.id), ("start_date", "<=", date_from), ("end_date", ">=", date_from)], limit=1)
        if fiscal_year_from:
            date_from = fiscal_year_from.end_date + timedelta(days=1)
        fiscal_year_to = self.env["account.fiscal.year"].search(
            [("company_id", "=", self.id), ("start_date", "<=", date_to), ("end_date", ">=", date_to)], limit=1)
        if fiscal_year_to:
            date_to = fiscal_year_to.end_date - timedelta(days=1)
        return {
            "date_from": date_from,
            "date_to": date_to,
        }
