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
import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DashboardConfig(models.Model):
    """Dashboard Configuration Model"""
    _name = 'dashboard.config'
    _description = 'Dashboard Configuration'
    _inherit = ['image.mixin']

    def _get_placeholder_filename(self, field):
        image_fields = ["image_%s" % size for size in [1920, 1024, 512, 256, 128]] + ["image"]
        if field in image_fields:
            return "cyllo_analytics/static/src/img/demo_dashboard_bw.png"
        return super()._get_placeholder_filename(field)

    def _get_default_user_ids(self):
        """Returns the default admin user ids"""
        return self._get_default_users().ids

    def _get_default_groups(self):
        """Returns the default admin groups"""
        return self.env.ref('cyllo_analytics.group_cyllo_analytics_admin').ids

    def _get_default_banner(self):
        """Method to get the default banner ID."""
        return self.env.ref('cyllo_analytics.dashboard_banner_no_banner').id

    def _get_default_theme(self):
        """Returns the default theme"""
        return self.env.ref("cyllo_analytics.dashboard_theme_cyllo").id

    name = fields.Char(required=True, size=32)
    banner_id = fields.Many2one(
        "dashboard.banner",
        string="Banner",
        default=_get_default_banner,
    )
    group_ids = fields.Many2many(
        'res.groups',
        string='Groups',
        default=_get_default_groups
    )
    user_ids = fields.Many2many(
        'res.users',
        string='Users',
        default=_get_default_user_ids
    )
    limit = fields.Integer()
    theme_id = fields.Many2one(
        'dashboard.theme',
        default=_get_default_theme
    )
    sheet_ids = fields.Many2many(
        'dashboard.sheet',
        string='Sheets'
    )
    global_filter_ids = fields.One2many(
        'dashboard.global.filter',
        'dashboard_config_id'
    )
    users_ids = fields.Many2many(
        'res.users',
        'dashboard_config_user_rel',
        compute="_compute_users_ids",
        store=True
    )
    company_id = fields.Many2one('res.company', string="Company")

    skip_filter = fields.Boolean(
        "Skip filter",
        default=False
    )
    ir_menu_ids = fields.Many2many(
        'ir.ui.menu',
        string='Linked Menus'
    )

    def _get_default_users(self):
        """Returns the default admin users"""
        return self.env.ref('cyllo_analytics.group_cyllo_analytics_admin').users

    @api.depends("group_ids", "user_ids", "create_uid")
    def _compute_users_ids(self):
        """Computes the users and groups and assigns it back"""
        default_group_id = self.env.ref(
            'cyllo_analytics.group_cyllo_analytics_admin')
        admin_user = default_group_id.mapped('users')
        for record in self:
            user_ids = record.group_ids.mapped(
                'users') + record.user_ids + admin_user
            record.users_ids = [fields.Command.set(user_ids.ids)]
            admin_ids = self._get_default_users()
            record.user_ids |= admin_ids
            record.group_ids |= default_group_id

    @api.model
    def get_sheets(self, res_id):
        """Get all the sheets"""

        def get_a_sheet():
            """Method to get a sheet associated with the current user."""
            return self.search([('users_ids', 'in', self.env.user.ids)],
                               limit=1)

        if res_id:
            rec = self.search(
                [('id', '=', res_id), ('users_ids', 'in', self.env.user.ids)])
            if not rec:
                rec = get_a_sheet()
        else:
            rec = get_a_sheet()
        theme_id = rec.theme_id or self.env.ref(
            'cyllo_analytics.dashboard_theme_walden')
        return [rec.get_data(), rec.id, theme_id.read_theme(), rec.name,
                rec.banner_id.read(['name', 'image_1920'])]

    def get_data(self, field_list=None):
        """Method to get data for the specified fields from associated sheets."""
        if not field_list:
            field_list = []
        data = [rec.fetch_data(field_list, self.id) for rec in self.sheet_ids]
        return data

    @api.model
    def sql_execute(self, sql):
        """Execute SQL query"""
        try:
            if sql:
                params = []
                before, sep, after = sql.rpartition("FROM")
                after = sep + after
                tables = re.findall(r'(?i)(?:FROM|JOIN)\s+([`"]?[\w\.]+[`"]?)', after)
                models = self.env['ir.model'].search([('table_name', 'in', tables)]).mapped('model')
                for model in models:
                    model = self.env[model]
                    query_obj = model._where_calc([])
                    model._apply_ir_rules(query_obj, 'read')

                    # Convert domain to SQL clauses
                    from_clause, where_clause, where_params = query_obj.get_sql()
                    join = "LEFT JOIN" if 'LEFT JOIN' in from_clause.upper() else "RIGHT JOIN" if 'RIGHT JOIN' in from_clause.upper() else "JOIN" if 'JOIN' in from_clause.upper() else ""
                    join_clause = join + from_clause.split(f"{join}", 1)[1] if join else ""
                    params = where_params + params

                    if 'WHERE' in after.upper():
                        # Split query at WHERE
                        parts = re.split(r'\bWHERE\b', after, maxsplit=1, flags=re.IGNORECASE)

                        if len(parts) == 2:
                            before_where = parts[0]
                            after_where = parts[1]

                            # Reconstruct with ir.rule
                            after = f"{before_where} {join_clause} WHERE ({where_clause}) AND {after_where}"
                    else:
                        # No WHERE clause - add one
                        # Find position after FROM clause(s)
                        after = re.sub(
                            r'(FROM\b[\s\S]*?)(\bORDER BY\b|\bGROUP BY\b|\bLIMIT\b|$)',
                            rf'\1{join_clause} WHERE {where_clause} \2',
                            after,
                            count=1,
                            flags=re.IGNORECASE,
                        )
                new_query = before + after
                self.env.cr.execute(new_query, params)
                return self.env.cr.dictfetchall()
            else:
                return False
        except Exception as error:
            return False

    def save_position(self, vals):
        """Save the position of the graph in the dashboard"""
        for val in vals["children"]:
            sheet_option = self.env['dashboard.sheet.option'].search(
                [('dashboard_sheet_id', '=', val["id"]),
                 ('dashboard_config_id', "=", self.id)])
            if not sheet_option:
                sheet_option = self.env['dashboard.sheet.option'].create({
                    "dashboard_sheet_id": val["id"],
                    "dashboard_config_id": self.id})
            sheet_option.write({
                "attributes": {
                    "x": val["x"],
                    "y": val["y"],
                    "graph_height": val["h"] if 'h' in val.keys() else 1,
                    "graph_width": val["w"] if 'w' in val.keys() else 1,
                }
            })

    def get_dashboard_data(self):
        """Get the dashboard data for json export"""
        return {
            "sheets": self.get_data(
                ["name", "query", "dimension", "measure", "type",
                 "dimension_axis", "image_1920", "kpi_name",
                 "kpi_target", "is_enabled", "kpi_redirect",
                 "kpi_view", "kpi_description", "kpi_target_perc",
                 "kpi_icon", "table_ids", "filter_ids", "limit"]),
            "theme": self.theme_id.name,
            "name": self.name,
            "image_1920": self.image_1920,
            "limit": self.limit,
        }

    @api.model
    def import_data(self, data):
        """Import dashboard from a JSON file."""
        try:
            dashboard_config_id = self.create({
                "name": data["name"],
                "limit": data["limit"],
                "image_1920": data["image_1920"],
                "theme_id": self.env["dashboard.theme"].search(
                    [("name", "=", data["theme"])], limit=1).id,
            })
            dashboard_config_id.write({
                "sheet_ids": [fields.Command.create({
                    "name": sheet["name"],
                    "type": sheet["type"],
                    "image_1920": sheet["image_1920"],
                    "dimension_axis": sheet["dimension_axis"],
                    "limit": sheet["limit"] or 0,
                    "kpi_target": sheet.get("kpi_target", False),
                    "kpi_view": sheet.get("kpi_view", False),
                    "kpi_redirect": sheet.get("kpi_target", False),
                    "kpi_icon": sheet.get("kpi_icon", False),
                    "kpi_description": sheet.get("kpi_description", False),
                    "is_enabled": sheet["is_enabled"],
                    "axis_ids": [fields.Command.create({
                        "value": rec['value'],
                        "alias": rec['alias'],
                        "query": rec['query'],
                        "column": rec['column'],
                        "type": rec['type'],
                    }) for rec in sheet["axis_ids"]],
                    "dashboard_sheet_option_ids": [fields.Command.create({
                        "attributes": rec["attributes"],
                        "dashboard_config_id": dashboard_config_id.id
                    }) for rec in sheet["dashboard_sheet_option_ids"]],
                    "table_ids": [fields.Command.create({
                        "name": table['name'],
                        "model": table['model'],
                        "linked": table['linked'],
                        "field": table['field'],
                        "join": table['join'],
                        "model_id": self.env['ir.model'].search(
                            [('model', '=', table['model'])]).id,
                    }) for table in sheet["table_ids"]],
                    "filter_ids": [fields.Command.create({
                        "name": filter_data.get("name", False),
                        "domain": filter_data.get("domain", False),
                        "is_active": filter_data.get("is_active", False),
                    }) for filter_data in sheet["filter_ids"]],
                }) for sheet in data["sheets"]]
            })
            return True, ""
        except Exception as e:
            return False, e

    def remove_sheet(self, sheet_id):
        """Method to remove a sheet."""
        self.sheet_ids.filtered(
            lambda rec: rec.id == sheet_id).dashboard_sheet_option_ids.filtered(
            lambda item: item.dashboard_config_id == self.id).unlink()
        self.write({'sheet_ids': [(fields.Command.unlink(sheet_id))]})

    def execute_query_d(self, obj):
        """Method to execute a database query and send the result through the bus."""
        res_id = obj["id"]
        query = obj["query"]
        result = self.sql_execute(query)
        channel = "CY:ANALYTICS"
        message = {
            "result": result,
            "id": res_id,
            "channel": channel
        }
        self.env["bus.bus"]._sendone(channel, "notification", message)

    def process_query(self, sql):
        """Method to process a SQL query."""
        try:
            self.env.cr.execute(sql)
            return self.env.cr.dictfetchall()
        except Exception as error:
            return False

    @api.model
    def sql_execute_multi(self, queries_obj):
        """Method to execute multiple SQL queries asynchronously."""
        for query in queries_obj:
            self.execute_query_d(query)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        """ Method to create multiple records."""
        res = super(DashboardConfig, self).create(vals_list)
        if not res.skip_filter:
            filters = ['dashboard_global_filter_start_date',
                       'dashboard_global_filter_end_date',
                       'dashboard_global_filter_company',
                       'dashboard_global_filter_user']
            for filter_id in filters:
                filter_record = self.env.ref(f"{'cyllo_analytics'}.{filter_id}")
                if filter_record:
                    vals = {
                        'name': filter_record.name,
                        'type': filter_record.type,
                        'code': filter_record.code,
                        'relation': filter_record.relation,
                        'operator': filter_record.operator,
                        'dashboard_config_id': res.id
                    }
                res.update(
                    {'global_filter_ids': [(fields.Command.create(vals))]})
        return res

    def append_menu(self, menu_id):
        """ Method to append a menu to the dashboard configuration."""
        self.write({"ir_menu_ids": [fields.Command.link(menu_id)]})

    def write(self, data):
        """ Method to write data to the record."""
        menus = data.get('ir_menu_ids')
        to_remove_menus = filter(lambda rec: rec[0] == 3,
                                 menus) if menus else []
        self.remove_added_menus(to_remove_menus)
        res = super().write(data)

        # Add Group Access to Selected Users Automatically
        if "user_ids" in data:
            group = self.env.ref("cyllo_analytics.group_cyllo_analytics_user")
            for rec in self:
                for user in rec.users_ids:
                    if group not in user.groups_id:
                        user.write(
                            {"groups_id": [(4, group.id)]}
                        )  # Add group safely
        return res

    def remove_added_menus(self, to_remove_menu_ids):
        """Method to remove added menus."""
        for rec_id in to_remove_menu_ids:
            rec_id = rec_id if type(rec_id) is int else rec_id[1]
            menu_id = self.env["ir.ui.menu"].browse(rec_id)
            if menu_id.exists():
                menu_id.action.unlink()
                menu_id.unlink()

    def clean_up_menus(self):
        """Method to clean up menus associated with the record."""
        menu_ids = self.ir_menu_ids.ids
        if menu_ids:
            self.remove_added_menus(menu_ids)

    def unlink(self):
        """Method to unlink the record."""
        if self.id == self.env.ref('cyllo_analytics.dashboard_config_main').id:
            raise ValidationError("Can't remove the main Dashboard")
        self.clean_up_menus()
        return super().unlink()
