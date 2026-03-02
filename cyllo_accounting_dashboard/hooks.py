import json
from odoo.modules.module import get_module_resource

PARAM_KEY = "cyllo_accounting_dashboard.dashboard_id"


def _post_init_hook(env):
    file_path = get_module_resource(
        'cyllo_accounting_dashboard',
        'static/src/json',
        'Accounting Dashboard dashboard (4).json'
    )
    if not file_path:
        return
    with open(file_path, 'r') as f:
        data = json.load(f)

    dashboard = env['dashboard.config'].sudo().import_data(data)

    env['ir.config_parameter'].sudo().set_param(PARAM_KEY, dashboard.id)

    # Link menu + action
    menu = env.ref('cyllo_accounting_dashboard.menu_acc_dashboard_json')
    action = env.ref('cyllo_accounting_dashboard.action_acc_dashboard_json')

    dashboard.write({
        'ir_menu_ids': [(4, menu.id)]
    })

    action.write({
        'context': {
            'rec_id': dashboard.id,
            'is_subAction': True
        }
    })
def uninstall_hook(env):
    dashboard_id = env['ir.config_parameter'].sudo().get_param(PARAM_KEY)

    if not dashboard_id:
        return

    dashboard = env['dashboard.config'].sudo().browse(int(dashboard_id))

    if dashboard.exists():

        sheets = dashboard.sheet_ids

        dashboard.unlink()

        if sheets:
            sheets.unlink()

    env['ir.config_parameter'].sudo().set_param(PARAM_KEY, False)