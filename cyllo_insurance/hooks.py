# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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

def post_init_hook(env):
    for company in env['res.company'].search([]):
        _setup_insurance_accounting(env, company)

def _setup_insurance_accounting(env, company):
    # Create Income Account
    account = env['account.account'].search([
        ('company_id', '=', company.id),
        ('name', '=', 'Insurance Income')
    ], limit=1)
    
    if not account:
        account = env['account.account'].create({
            'name': 'Insurance Income',
            'code': '400100',
            'account_type': 'income',
            'company_id': company.id,
        })
        
    product = env.ref('cyllo_insurance.product_product_insurance_premium', raise_if_not_found=False)
    if product:
        product.with_company(company).property_account_income_id = account
        
    # Create Journal
    journal = env['account.journal'].search([
        ('company_id', '=', company.id),
        ('code', '=', 'INS')
    ], limit=1)
    
    if not journal:
        journal = env['account.journal'].create({
            'name': 'Insurance Sales',
            'code': 'INS',
            'type': 'sale',
            'default_account_id': account.id,
            'company_id': company.id,
        })
