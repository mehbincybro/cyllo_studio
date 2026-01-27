# -*- coding: utf-8 -*-
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
    _description = 'Performance history time'

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
