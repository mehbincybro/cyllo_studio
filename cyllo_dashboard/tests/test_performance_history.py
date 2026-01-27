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
from odoo.tests.common import TransactionCase


class TestPerformanceHistoryTime(TransactionCase):
    """Test methods of the Performance History Time"""

    def test_get_periodical_data(self):
        PHistory = self.env['performance.history'].create({
            'used_memory_history': '5',
            'used_ram_history': '8',
            'hardware_temperature_history': '7',
            'cpu_usage_history': '6'})
        PHistoryTime = self.env['performance.history.time'].create(
            {'used_memory_history': '5', })
        PHistoryTime.get_periodical_data()
        LatestPHT = self.env['performance.history.time'].search([],
                                                                order='id desc',
                                                                limit=1)
        self.assertEqual(LatestPHT.used_memory_history,
                         PHistory.used_memory_history)
        self.assertEqual(LatestPHT.used_ram_history, PHistory.used_ram_history)
        self.assertEqual(LatestPHT.hardware_temperature_history,
                         PHistory.hardware_temperature_history)
        self.assertEqual(LatestPHT.cpu_usage_history,
                         PHistory.cpu_usage_history)
