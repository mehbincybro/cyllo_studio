# -*- coding: utf-8 -*-
import datetime
from datetime import date

from odoo import models


class HrLeave(models.Model):
    """To get the leave of the employee during the training period,
    based on that it changes the end date of the training"""
    _inherit = 'hr.leave'

    def action_validate(self):
        """The function is used to update the end date of the
        training period of the employee if the time off is approved """
        res = super(HrLeave, self).action_validate()
        contract_id = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id),
                                                      ('state', '=', 'training')], limit=1)
        # check valid contract and probation details.
        if contract_id and contract_id.employee_training_period_id:
            training_period_details = contract_id.employee_training_period_id
            time_off_type = self.env.ref('hr_holidays.holiday_status_unpaid')
            number_of_days = 0
            time_off_details = []

            # calculating half day leave :
            if self.request_unit_half:
                for half_day in contract_id.half_time_off_ids:
                    time_off_details.append(half_day.id)
                time_off_details.append(self.id)
                contract_id.write({'half_time_off_ids': time_off_details})
                if len(contract_id.half_time_off_ids) == 2:
                    number_of_days = 1
                    contract_id.half_time_off_ids = False

            # calculating full day leaves and updating period :
            if (self.holiday_status_id.id == time_off_type.id and contract_id.state == "training" and
                    training_period_details and not self.request_unit_half and not self.request_unit_hours):
                date_from = date(self.request_date_from.year, self.request_date_from.month, self.request_date_from.day)
                date_to = date(self.request_date_to.year, self.request_date_to.month, self.request_date_to.day)
                if date_from >= training_period_details.start_date and date_to <= training_period_details.end_date:
                    updated_end_date = training_period_details.end_date + datetime.timedelta(
                        days=self.number_of_days_display)
                    time_off_details = []
                    for time in training_period_details.time_off_ids:
                        time_off_details.append(time.id)
                    time_off_details.append(self.id)
                    training_period_details.write({
                        'end_date': updated_end_date,
                        'state': "extended",
                        'time_off_ids': time_off_details
                    })
                    contract_id.write({'date_end': updated_end_date})

            # updating period based on half day leave:
            elif (self.holiday_status_id.id == time_off_type.id and contract_id.state == "training"
                  and training_period_details and self.request_unit_half):
                date_from = date(self.request_date_from.year, self.request_date_from.month, self.request_date_from.day)
                if training_period_details.end_date >= date_from >= training_period_details.start_date:
                    updated_end_date = training_period_details.end_date + datetime.timedelta(days=number_of_days)
                    for leave in training_period_details.time_off_ids:
                        time_off_details.append(leave.id)
                    time_off_details.append(self.id)
                    training_period_details.write({
                        'end_date': updated_end_date,
                        'state': "extended",
                        'time_off_ids': time_off_details
                    })
                    contract_id.write({'training_date_to': updated_end_date})
        return res
