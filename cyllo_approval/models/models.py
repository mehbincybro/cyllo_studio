# -*- coding: utf-8 -*-
from odoo import api,models
from lxml import etree

from odoo.exceptions import ValidationError


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    # ✅ Handle dynamic approve/reject actions globally
    def action_dynamic_approve(self):
        """Called when clicking the dynamically injected Approve button."""
        self.ensure_one()
        request = self.x_approval_request_ids[0]
        if request.approver_id.id != self.env.uid:
            raise ValidationError("You are not allowed to approve this step.")
        request.sudo().action_approve()
        # Optional: do something on the document itself
        self.message_post(body="Record Approved via dynamic approval flow.")

    def action_dynamic_reject(self):
        """Called when clicking the dynamically injected Reject button."""
        self.ensure_one()
        request = self.x_approval_request_ids[0]
        if request.approver_id.id != self.env.uid:
            raise ValidationError("You are not allowed to reject this step.")
        request.sudo().action_reject()
        # Optional: do something on the document itself
        self.message_post(body="Record Rejected via dynamic approval flow.")

    def action_dynamic_transfer(self):
        """Called when clicking the dynamically injected Transfer button."""
        self.ensure_one()
        request = self.x_approval_request_ids[0]
        if request.approver_id.id != self.env.uid:
            raise ValidationError("You are not allowed to transfer this step.")
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'approval.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': request.id,
                'default_current_user_id': self.env.uid,
            },
        }

    def action_request_approval(self):
        """Open wizard to request approval with sequencing support"""

        ApprovalRule = self.env['approval.rule'].sudo()
        ApprovalRequest = self.env['approval.request'].sudo()

        # Fetch all state rules for this model
        rules = ApprovalRule.search([
            ('model_name', '=', self._name),
            ('rule_type', '=', 'state'),
        ])

        if not rules:
            return

        ordered = rules.sorted(key=lambda r: r.sequence)

        # 🔍 Find the NEXT rule that needs approval
        next_rule = None

        for rule in ordered:
            existing = ApprovalRequest.search([
                ('rule_id', '=', rule.id),
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
            ], order="id desc", limit=1)

            # ✅ Already approved → skip to next
            if existing and existing.state == 'approved':
                continue

            # ⏳ Already pending → use this rule
            if existing and existing.state == 'pending':
                next_rule = rule
                break

            # 🎯 No request yet or rejected/done → this is the next one
            next_rule = rule
            break

        # Fallback to first rule if none found (shouldn't happen)
        if not next_rule:
            next_rule = ordered[0]

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_rule_id': next_rule.id,
                'default_res_model': self._name,
                'default_res_id': self.id,
            },
        }

    def action_open_approval_requests(self):
        """Open all approval requests related to the document."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Approval Requests",
            "res_model": "approval.request",
            "view_mode": "tree,form",
            "domain": [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id)
            ],
            "target": "current",
        }

    @api.model
    def _approval_request_count(self):
        """Compute count for stat button."""
        ApprovalRequest = self.env["approval.request"]
        for rec in self:
            rec.x_approval_request_count = ApprovalRequest.search_count([
                ("res_model", "=", rec._name),
                ("res_id", "=", rec.id)
            ])

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)

        if view_type != 'form':
            return res

        user = self.env.user
        model_name = res.get('model')
        ApprovalRule = self.env['approval.rule'].sudo()

        # Fetch ALL rules for this model (state or button)
        rules = ApprovalRule.search([('model_name', '=', model_name)])

        if not rules:
            return res

        ordered_rules = rules.sorted(key=lambda r: r.sequence)

        # Determine which rule applies to this user (for comment field and button rules)
        active_rule = next(
            (
                r for r in ordered_rules
                if (
                    (r.user_id and r.user_id.id == user.id) or
                    (r.group_id and r.group_id in user.groups_id)
                )
            ),
            None
        )

        arch = etree.fromstring(res['arch'])

        # Ensure hidden dynamic fields exist
        def ensure_hidden_field(field_name):
            if not arch.xpath(f'//field[@name="{field_name}"]'):
                sheet_nodes = arch.xpath('//sheet')
                if sheet_nodes:
                    field = etree.Element('field', {
                        'name': field_name,
                        'invisible': '1'
                    })
                    sheet_nodes[0].insert(0, field)

        ensure_hidden_field("x_approval_request_ids")
        ensure_hidden_field("x_is_state_approval")
        ensure_hidden_field("x_approval_comment")
        ensure_hidden_field("x_current_approver_id")
        ensure_hidden_field("x_current_group_id")
        ensure_hidden_field("x_approval_request_count")

        sheet_nodes = arch.xpath('//sheet')
        if sheet_nodes:
            sheet = sheet_nodes[0]

            warning_div = etree.Element(
                'div',
                {
                    'class': 'alert alert-warning o_form_label',
                    'role': 'alert',
                    'invisible': "not x_is_state_approval or "
                                 "x_approval_request_ids"
                }
            )
            warning_div.text = "Approval is required before changing the state. Please request approval."
            sheet.insert(0, warning_div)

            # Only show comment group if there's an active rule for this user and it allows comments
            if active_rule and active_rule.is_comment:
                comment_group = etree.Element(
                    "group",
                    {
                        "string": "Approval Comment",
                        "invisible": "not x_approval_request_ids"
                    }
                )
                comment_field = etree.Element("field", {
                    "name": "x_approval_comment",
                    "placeholder": "Enter your private approval comment"
                })

                comment_group.append(comment_field)
                sheet.append(comment_group)

        # Inject header buttons
        headers = arch.xpath('//header')
        if headers:
            header = headers[0]

            approve_btn = etree.Element('button', {
                'name': 'action_dynamic_approve',
                'string': 'Approve',
                'type': 'object',
                'class': 'oe_highlight cyllo_approval_btn',
                'invisible': "not (x_approval_request_ids and "
                             "x_current_approver_id == uid)"
            })
            reject_btn = etree.Element('button', {
                'name': 'action_dynamic_reject',
                'string': 'Reject',
                'type': 'object',
                'class': 'btn-secondary cyllo_approval_btn',
                'invisible': "not (x_approval_request_ids and "
                             "x_current_approver_id == uid)"
            })
            transfer_btn = etree.Element('button', {
                'name': 'action_dynamic_transfer',
                'string': 'Transfer',
                'type': 'object',
                'class': 'btn-info cyllo_approval_btn',
                'invisible': "not (x_approval_request_ids and "
                             "x_current_approver_id == uid)"
            })
            request_btn = etree.Element('button', {
                'name': 'action_request_approval',
                'string': 'Request Approval',
                'type': 'object',
                'class': 'btn-secondary',
                'invisible': "not x_is_state_approval or x_approval_request_ids"
            })

            stat_btn = etree.Element("button", {
                "name": "action_open_approval_requests",
                "type": "object",
                "class": "oe_stat_button",
                "icon": "fa-check-square",
                "invisible": "x_approval_request_count == 0",
            })
            field_count = etree.Element("field", {
                "name": "x_approval_request_count",
                "widget": "statinfo"
            })
            stat_btn.append(field_count)

            header.append(approve_btn)
            header.append(reject_btn)
            header.append(request_btn)
            header.append(transfer_btn)
            header.append(stat_btn)

        # === BUTTON RULE LOGIC ===
        # If there's an active button rule for this user, apply additional visibility logic
        if active_rule and active_rule.rule_type == "button":
            button_nodes = arch.xpath(
                f".//button[@name='{active_rule.button_id.name}']")

            if button_nodes:
                target_conditions = []
                for btn in button_nodes:
                    inv = btn.get("invisible")
                    if inv:
                        target_conditions.append(f"({inv})")

                if target_conditions:
                    combined_invisible = " and ".join(target_conditions)
                    approval_buttons = arch.xpath(
                        ".//button[contains(@class,'cyllo_approval_btn')]"
                    )

                    for btn in approval_buttons:
                        own_inv = btn.get("invisible")
                        if own_inv:
                            final = f"({own_inv}) or ({combined_invisible})"
                        else:
                            final = combined_invisible
                        btn.set("invisible", final)

        res['arch'] = etree.tostring(arch, encoding='unicode')
        return res
