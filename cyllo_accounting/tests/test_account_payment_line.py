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
from odoo.addons.cyllo_accounting.tests.common import TestCylloAccounting


class TestAccountPaymentLine(TestCylloAccounting):

    def test_compute_paid_amount(self):
        payment_line = self.env['account.payment.line'].create({
            'payment_id': self.payment.id,
            'move_id': self.account_move.id,
            'partner_id': self.partner.id,
        })
        payment_line._compute_paid_amount()
        self.assertEqual(payment_line.paid_amount, 0.0)
