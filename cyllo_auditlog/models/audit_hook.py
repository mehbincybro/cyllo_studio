from odoo import models, api, fields, _
from odoo.http import request
from odoo.tools import config
import logging
import json
from datetime import datetime

_logger = logging.getLogger(__name__)


class BaseAuditHook(models.AbstractModel):
    _inherit = 'base'

    def _get_audit_rules(self):
        """Get all active audit rules for this model with request-level caching."""
        req = self._get_safe_request()
        if not req or getattr(req, 'audit_internal_call', False): return []

        # Optimization: Use request cache to avoid repeated searches in the same request
        if not hasattr(req, 'audit_rules_cache'): req.audit_rules_cache = {}
        if self._name in req.audit_rules_cache:
            return req.audit_rules_cache[self._name]

        # Critical: Only search if we aren't already searching (recursion guard)
        try:
            req.audit_internal_call = True
            rules = self.env['audit.rule'].sudo().search([
                ('model_id.model', '=', self._name), ('active', '=', True)
            ])
            req.audit_rules_cache[self._name] = rules
            return rules
        finally:
            req.audit_internal_call = False

    def _get_safe_request(self):
        """Safely retrieve the request object and check if auditing should be active."""
        # Fast bypass during module installation or upgrades
        if config.get('init') or config.get('update'):
            return False

        try:
            # Check for request and verify it has a database (avoids background sync issues)
            if request and hasattr(request, 'db') and request.db:
                return request
        except (RuntimeError, AttributeError):
            pass
        return False

    def _should_track_user(self, rule):
        """Check if current user should be tracked"""
        return rule.sudo()._should_track_user(self.env.user)

    def _should_track_field(self, rule, field_name):
        """Check if a field should be tracked based on rule configuration"""
        scope = rule.tracking_scope
        if scope == 'all': return True
        fields = rule.sudo().tracked_field_ids if scope == 'tracked' else rule.sudo().excluded_field_ids
        return (field_name in fields.mapped('name')) == (scope == 'tracked')

    def _prepare_audit_log_vals(self, rule, operation, res_id, changes=None):
        """Prepare values for audit log creation"""
        vals = {
            'user_id': self.env.user.id,
            'model_id': rule.model_id.id,
            'res_id': res_id,
            'operation': operation,
            'log_level': rule.log_level,
            'session_id': self._get_session_id() if rule.track_session else False,
            'ip_address': self._get_client_ip() if rule.track_ip else False,
        }

        if changes and operation == 'write':
            TECHNICAL = {'write_date', 'write_uid', 'needed_terms_dirty', 'message_has_error',
                         'message_main_attachment_id', 'tax_totals', 'invoice_payments_widget',
                         'invoice_outstanding_credits_debits_widget'}
            interesting = [f for f in changes if f not in TECHNICAL]
            field = interesting[0] if len(interesting) == 1 else (
                "Multiple Fields" if interesting else list(changes.keys())[0])
            vals.update({
                'field_name': field,
                'old_value': str(changes.get(field, next(iter(changes.values())))['old']) or '',
                'new_value': str(changes.get(field, next(iter(changes.values())))['new']) or '',
            })
        return vals

    def _create_audit_log(self, rule, operation, res_id, changes=None):
        """Create audit log entry with lines"""
        if operation == 'write' and not changes: return False
        try:
            log = self.env['audit.log'].sudo().create(
                self._prepare_audit_log_vals(rule.sudo(), operation, res_id, changes))
            if changes and operation == 'write':
                self.env['audit.log.line'].sudo().create([{
                    'log_id': log.id, 'field_name': f,
                    'old_value': str(c['old']) if c['old'] is not None else '',
                    'new_value': str(c['new']) if c['new'] is not None else '',
                } for f, c in changes.items()])
            return log
        except Exception:
            _logger.error("Failed to create audit log", exc_info=True)
            return False

    def _get_client_ip(self):
        """Get client IP address"""
        if not (request and hasattr(request, 'httprequest')): return ''
        env = request.httprequest.environ
        return env.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.httprequest.remote_addr or ''

    def _get_session_id(self):
        """Get or create audit.session record for current request"""
        session = self.env['audit.session'].sudo().get_or_create_session()
        return session.id if session else False

    def _get_x2many_changes_desc(self, rule, field_name, commands, sub_old_values=None):
        """Parse x2many commands with rule-based sub-field filtering."""
        if not commands: return ""
        rel_model = self.env[self._fields[field_name].comodel_name].sudo()
        details = []
        for cmd in commands:
            if not isinstance(cmd, (list, tuple)): continue
            ctype, cid = cmd[0], cmd[1]
            if ctype == 0:
                details.append(
                    f"New line: { {k: v for k, v in cmd[2].items() if k not in ['write_date', 'write_uid', 'id']} }")
            elif ctype == 1:
                diffs = []
                for f, nv in cmd[2].items():
                    if f in ['write_date', 'write_uid', 'id'] or not self._should_track_field(rule, f): continue
                    ov = (sub_old_values or {}).get(cid, {}).get(f) or rel_model.browse(cid)[f]
                    if str(ov) != str(nv): diffs.append(f"{f}: {ov} -> {nv}")
                if diffs: details.append(f"Line #{cid} ({', '.join(diffs)})")
            elif ctype == 2:
                details.append(f"Delete line #{cid}")
        return f" | Details: {'; '.join(details)}" if details else ""

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self._name in ['audit.log', 'audit.rule', 'audit.log.line']: return records
        for rule in self._get_audit_rules():
            if rule.track_create and self._should_track_user(rule):
                for r in records: self._create_audit_log(rule, 'create', r.id)
        return records

    def write(self, vals):
        if self._name in ['audit.log', 'audit.rule', 'audit.log.line']: return super().write(vals)
        rules = [r for r in self._get_audit_rules() if r.track_write and self._should_track_user(r)]
        if not rules: return super().write(vals)

        SKIP = {
            'write_date', 'write_uid', '__last_update', 'message_ids', 'activity_ids',
            'message_follower_ids', 'message_has_error', 'message_main_attachment_id',
            'needed_terms_dirty', 'tax_totals', 'invoice_payments_widget',
            'invoice_outstanding_credits_debits_widget', 'is_move_sent'
        }
        tracked_fields = [f for f in vals if f not in SKIP] or []
        old_vals, sub_old = {}, {}

        for rule in rules:
            for rec in self:
                old_vals.setdefault(rec.id, {})
                for f in tracked_fields:
                    if self._should_track_field(rule, f) and f in self._fields:
                        val = rec[f]
                        if self._fields[f].type == 'many2one':
                            old_vals[rec.id][f] = f"{val.display_name} (ID: {val.id})" if val else ""
                        elif self._fields[f].type in ['many2many', 'one2many']:
                            old_vals[rec.id][f] = f"{len(val)} records: {val.mapped('display_name')}"
                            for sub_cmd in (vals.get(f) or []):
                                if isinstance(sub_cmd, (list, tuple)) and sub_cmd[0] == 1:
                                    sub_rec = self.env[self._fields[f].comodel_name].sudo().browse(sub_cmd[1])
                                    sub_old.setdefault(sub_cmd[1],
                                                       {sf: sub_rec[sf] for sf in sub_cmd[2] if sf in sub_rec._fields})
                        else:
                            old_vals[rec.id][f] = val

        result = super().write(vals)
        for rule in rules:
            for rec in self:
                changes = {}
                for f, ov in old_vals.get(rec.id, {}).items():
                    if not self._should_track_field(rule, f): continue  # Ensure per-rule filtering
                    nv = rec[f]
                    if self._fields[f].type == 'many2one':
                        nvd = f"{nv.display_name} (ID: {nv.id})" if nv else ""
                        if ov != nvd: changes[f] = {'old': ov, 'new': nvd}
                    elif self._fields[f].type in ['many2many', 'one2many']:
                        nvd = f"{len(nv)} records: {nv.mapped('display_name')}"
                        if ov != nvd or f in vals:
                            changes[f] = {'old': ov,
                                          'new': f"{nvd}{self._get_x2many_changes_desc(rule, f, vals.get(f), sub_old)}"}
                    elif str(ov) != str(nv):
                        changes[f] = {'old': ov, 'new': nv}
                if changes: self._create_audit_log(rule, 'write', rec.id, changes)
        return result

    def unlink(self):
        if self._name in ['audit.log', 'audit.rule', 'audit.log.line']: return super().unlink()
        rules = [r for r in self._get_audit_rules() if r.track_unlink and self._should_track_user(r)]
        for rule in rules:
            for rec in self: self._create_audit_log(rule, 'unlink', rec.id)
        return super().unlink()

    def _log_read_action(self, res_ids):
        """Internal helper to log read actions once per request/record."""
        req = self._get_safe_request()
        if not req or not res_ids or getattr(req, 'audit_internal_call', False): return

        # More aggressive system exclusion to handle upgrades smoothly
        SYSTEM_MODELS = {
            'audit.log', 'audit.rule', 'audit.log.line', 'bus.bus',
            'ir.module.module', 'ir.model', 'ir.model.fields', 'ir.ui.view',
            'ir.actions.report', 'ir.attachment', 'res.users.log', 'ir.http'
        }
        if self._name in SYSTEM_MODELS or self._name.startswith('ir.'): return

        rules = [r for r in self._get_audit_rules() if r.track_read and self._should_track_user(r)]
        if not rules: return

        # Use request cache instead of recordset attribute
        if not hasattr(req, 'audit_read_logged'):
            req.audit_read_logged = set()

        for rule in rules:
            for rid in res_ids:
                key = (rule.id, self._name, rid)
                if key not in req.audit_read_logged:
                    self._create_audit_log(rule, 'read', rid)
                    req.audit_read_logged.add(key)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        """Override search_read to log read actions on the results."""
        # FIX: Check if we're already in a read logging operation using request cache
        req = self._get_safe_request()
        if req and getattr(req, 'audit_skip_read', False):
            return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order,
                                       **read_kwargs)

        res = super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order, **read_kwargs)

        # Only log if we have results and we're not in an internal call
        if res and req:
            try:
                # Set flag in request to prevent recursion
                req.audit_skip_read = True
                # Extract IDs from results
                res_ids = [r['id'] for r in res if r.get('id')]
                if res_ids:
                    self._log_read_action(res_ids)
            finally:
                if req:
                    req.audit_skip_read = False

        return res

    @api.model
    def web_read(self, specification):
        """Override web_read to log read actions."""
        # FIX: Check if we're already in a read logging operation using request cache
        req = self._get_safe_request()
        if req and getattr(req, 'audit_skip_read', False):
            return super().web_read(specification)

        # Get the records first
        records = self
        res = super().web_read(specification)

        # Only log if we have records and we're not in an internal call
        if records and req:
            try:
                req.audit_skip_read = True
                self._log_read_action(records.ids)
            finally:
                if req:
                    req.audit_skip_read = False

        return res

    def read(self, fields=None, load='_classic_read'):
        """Override read to log read actions."""
        # FIX: Check if we're already in a read logging operation using request cache
        req = self._get_safe_request()
        if req and getattr(req, 'audit_skip_read', False):
            return super().read(fields=fields, load=load)

        res = super().read(fields=fields, load=load)

        # Only log if we have records and we're not in an internal call
        if self and req:
            try:
                req.audit_skip_read = True
                self._log_read_action(self.ids)
            finally:
                if req:
                    req.audit_skip_read = False

        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Override name_search to log read actions on found records."""
        # FIX: Check if we're already in a read logging operation using request cache
        req = self._get_safe_request()
        if req and getattr(req, 'audit_skip_read', False):
            return super().name_search(name=name, args=args, operator=operator, limit=limit)

        res = super().name_search(name=name, args=args, operator=operator, limit=limit)

        # Only log if we have results and we're not in an internal call
        if res and req:
            try:
                req.audit_skip_read = True
                # Extract IDs from name_search results [(id, name), ...]
                res_ids = [r[0] for r in res if r and r[0]]
                if res_ids:
                    self._log_read_action(res_ids)
            finally:
                if req:
                    req.audit_skip_read = False

        return res