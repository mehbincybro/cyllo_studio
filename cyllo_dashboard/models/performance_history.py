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
from odoo import fields, models


class PerformanceHistory(models.Model):
    """
        Model for storing performance history data.
    """
    _name = 'performance.history'
    _description = 'Performance history'

    used_memory_history = fields.Float(string="Memory")
    used_ram_history = fields.Float(string="Ram")
    hardware_temperature_history = fields.Float(string="Hardware Temperature")
    cpu_usage_history = fields.Float(string="CPU usage")


class PerformanceHistoryTime(models.Model):
    """
        Model for storing performance history data with time information.
    """
    _name = 'performance.history.time'
    _description = 'Performance History Time'

    used_memory_history = fields.Float(string="Memory")
    used_ram_history = fields.Float(string="Ram")
    hardware_temperature_history = fields.Float(string="Hardware Temperature")
    cpu_usage_history = fields.Float(string="CPU usage")

    def get_periodical_data(self):
        """
            This method retrieves historical performance data records from the
            'performance.history' model and creates corresponding records in the
            'performance.history.time' model.
        """
        for value in self.env['performance.history'].search([]):
            self.env['performance.history.time'].create({
                'used_memory_history': value.used_memory_history,
                'used_ram_history': value.used_ram_history,
                'hardware_temperature_history': value.hardware_temperature_history,
                'cpu_usage_history': value.cpu_usage_history
            })
