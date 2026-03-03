import json
from odoo.modules.module import get_module_resource

PARAM_KEY = "cyllo_accounting_dashboard.dashboard_id"


def _post_init_hook(env):
    """
    Post-init hook to import dashboard configuration from JSON file
    """
    file_path = get_module_resource(
        'cyllo_accounting_dashboard',
        'static/src/json',
        'Accounting Dashboard dashboard (4).json'
    )
    if not file_path:
        return

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        return

    dashboard_model = env['dashboard.config'].sudo()
    dashboard = False

    try:
        result = dashboard_model.import_data(data)

        if result:
            # Case 1: Result is a tuple with IDs
            if isinstance(result, tuple) and len(result) > 0:
                first_element = result[0]
                if isinstance(first_element, (list, tuple)) and len(first_element) > 0:
                    # Safe access to first ID
                    first_id = first_element[0]
                    if first_id:
                        dashboard = dashboard_model.browse(first_id)

            # Case 2: Result is a recordset with id attribute
            elif hasattr(result, 'id') and result.id:
                dashboard = result

            # Case 3: Result is a list of IDs
            elif isinstance(result, (list, tuple)) and result and result[0]:
                dashboard = dashboard_model.browse(result[0])

    except Exception:
        # If import fails, try to find existing dashboard by name
        pass

    # If dashboard not found from import result, try to find by name
    if not dashboard and data and 'name' in data:
        dashboard = dashboard_model.search(
            [('name', '=', data.get('name'))],
            limit=1
        )

    # Still no dashboard? Create one from data
    if not dashboard and data:
        try:
            dashboard = dashboard_model.create(data)
        except Exception:
            return

    if not dashboard or not dashboard.exists():
        return

    # Store dashboard id in config parameters
    try:
        env['ir.config_parameter'].sudo().set_param(PARAM_KEY, str(dashboard.id))
    except Exception:
        return

    # Link menu and action
    try:
        menu = env.ref('cyllo_accounting_dashboard.menu_acc_dashboard_json')
        action = env.ref('cyllo_accounting_dashboard.action_acc_dashboard_json')

        # Add menu to dashboard
        if menu and menu.exists():
            dashboard.write({
                'ir_menu_ids': [(4, menu.id)]
            })

        # Update action context
        if action and action.exists():
            action_context = action.context or {}
            action_context.update({
                'rec_id': dashboard.id,
                'is_subAction': True
            })
            action.write({'context': action_context})

    except Exception:
        # Log error but don't fail the hook
        pass


def uninstall_hook(env):
    """
    Uninstall hook to clean up dashboard data
    """
    try:
        dashboard_id = env['ir.config_parameter'].sudo().get_param(PARAM_KEY)

        if not dashboard_id:
            return

        # Convert to int safely
        try:
            dashboard_id = int(dashboard_id)
        except (ValueError, TypeError):
            return

        dashboard = env['dashboard.config'].sudo().browse(dashboard_id)

        if dashboard.exists():
            # Delete sheets first (if they exist)
            if hasattr(dashboard, 'sheet_ids') and dashboard.sheet_ids:
                dashboard.sheet_ids.unlink()

            # Delete the dashboard
            dashboard.unlink()

        # Remove the config parameter
        env['ir.config_parameter'].sudo().set_param(PARAM_KEY, False)

    except Exception:
        # Log error but don't fail the uninstall
        pass