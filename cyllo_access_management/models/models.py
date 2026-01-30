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
from lxml import etree
import psycopg2

from odoo import api, models
from odoo.osv import expression

class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        user = self.env.user
        company_id = self.env.company.id
        try:
            with self.env.cr.savepoint():
                profiles = user.profile_ids
                if not profiles:
                    return res

                access_mgmt = self.env['profile.management'].sudo().search([
                    ('profile_ids', 'in', profiles.ids),('is_activated','=',True),"|",
                    ('company_ids','in',[company_id]),('company_ids','=',False)
                ])
        except psycopg2.errors.UndefinedTable:
            return res
        if not access_mgmt:
            return res

        model = res['model']
        is_profile_readonly = True if True in  access_mgmt.mapped(
            'is_readonly') else False
        disable_chatter = True if True in access_mgmt.mapped(
            'disable_chatter') else False
        buttons_to_hide = access_mgmt.hide_buttons_tabs_ids.filtered(
            lambda r: r.model_id.model == model
        ).mapped('button_ids')
        tabs_to_hide = access_mgmt.hide_buttons_tabs_ids.filtered(
            lambda r: r.model_id.model == model
        ).mapped('tab_ids')
        filters_to_hide = access_mgmt.hide_filters_ids.filtered(
            lambda r: r.model_id.model == model
        ).mapped('filter_ids')
        groups_to_hide = access_mgmt.hide_filters_ids.filtered(
            lambda r: r.model_id.model == model
        ).mapped('group_ids')
        field_rules = access_mgmt.field_access_ids.filtered(
            lambda r: r.model_id.model == model
        )
        model_rules = access_mgmt.model_access_ids.filtered(
            lambda r: r.model_id.model == model
        )

        arch = etree.fromstring(res['arch'])

        if is_profile_readonly:
            arch.set("edit", "false")
            arch.set("create", "false")
            arch.set("delete", "false")
        if disable_chatter:
            chatter_nodes = arch.xpath("//chatter") + arch.xpath(
                "//div[contains(@class, 'oe_chatter')]")
            for node_chat in chatter_nodes:
                parent = node_chat.getparent()
                if parent is not None:
                    parent.remove(node_chat)

        if buttons_to_hide:
            for btn in buttons_to_hide:
                for node_btn in arch.xpath(f"//button[@name='{btn.name}']"):
                    node_btn.set("invisible", "1")

        if tabs_to_hide:
            for tab in tabs_to_hide:
                for node_tab in arch.xpath(f"//page[@string='{tab.string}']"):
                    node_tab.set("invisible", "1")

        if filters_to_hide:
            for flt in filters_to_hide:
                for node_flt in arch.xpath(f"//filter[@string='{flt.string}']"):
                    node_flt.set("invisible", "1")

        if groups_to_hide:
            for group in groups_to_hide:
                for node_grp in arch.xpath(
                        f"//filter[@string='{group.string}']"):
                    node_grp.set("invisible", "1")

        if field_rules:
            for rule in field_rules:
                for node_field in arch.xpath(
                        f"//field[@name='{rule.field_id.name}']"):

                    if rule.is_readonly:
                        node_field.set("readonly", "1")

                    if rule.is_invisible:
                        node_field.set("invisible", "1")

                    if rule.is_required:
                        node_field.set("required", "1")

                    if rule.remove_link:
                        node_field.set("options",
                                       '{"no_open": True, "no_create": True}')

        if model_rules:
            rule = model_rules[0]
            if rule.is_readonly:
                arch.set("edit","false")
                arch.set("create","false")
                arch.set("delete","false")

            if rule.hide_create:
                arch.set("create", "false")

            if rule.hide_edit:
                arch.set("edit", "false")

            if rule.hide_delete:
                arch.set("delete", "false")

            if rule.hide_archive:
                arch.set("archive", "false")

            if rule.hide_duplicate:
                arch.set("duplicate", "false")


        res['arch'] = etree.tostring(arch, encoding="unicode")
        return res

    @api.model
    def _search(self, domain, *args, **kwargs):
        if self.env.context.get("skip_profile_domain"):
            return super()._search(domain, *args, **kwargs)
        user = self.env.user
        try:
            with self.env.cr.savepoint():
                profiles = user.profile_ids
                company_id = self.env.context.get('allowed_company_ids')
                if profiles:
                    access_mgmt = self.env['profile.management'].sudo().with_context(
                        skip_profile_domain=True).search([
                        ('profile_ids', 'in', profiles.ids),('is_activated','=',True),
                        "|",('company_ids','in',company_id),('company_ids','=',False)
                    ])
                    if access_mgmt:
                        extra_domains = access_mgmt.domain_access_ids.filtered(
                            lambda r: r.model_name == self._name
                        ).mapped("domain")
                        for dom in extra_domains:
                            try:
                                dom_list = eval(dom) if dom else []
                                domain = expression.AND([domain, dom_list])
                            except Exception:
                                pass
        except psycopg2.errors.UndefinedTable:
            pass
        return super()._search(domain, *args, **kwargs)
