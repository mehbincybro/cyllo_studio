# -*- coding: utf-8 -*-
def add_payment_method(env):
    journals = env['account.journal'].search([('type', '=', 'bank')])
    if journals:
        for journal in journals:
            journal._compute_outbound_payment_method_line_ids()
            journal._compute_available_payment_method_ids()
