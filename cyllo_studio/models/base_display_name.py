# -*- coding: utf-8 -*-
from odoo.models import BaseModel


_ORIGINAL_COMPUTE_DISPLAY_NAME = BaseModel._compute_display_name

def _cyllo_compute_display_name(self):
    """
    Global display_name override:
    - If ir.model.cy_display_field is set for self._name, use that field's value
      as the display name.
    - Otherwise, fallback to Odoo's original _compute_display_name.
    """
    if not self:
        return

    try:
        model_rec = self.env['ir.model'].sudo().search([('model', '=', self._name)], limit=1)
        custom_field = model_rec.cy_display_field if model_rec else False
    except Exception:
        custom_field = False
    if not custom_field or custom_field not in self._fields:
        return _ORIGINAL_COMPUTE_DISPLAY_NAME(self)
    for rec in self:
        val = rec[custom_field]
        if hasattr(val, 'display_name'):
            name = val.display_name or ''
        elif isinstance(val, (list, tuple)):
            name = ', '.join([getattr(v, 'display_name', str(v)) for v in val]) if val else ''
        else:
            name = str(val) if val not in (False, None) else ''
        rec.display_name = name
    empties = self.filtered(lambda r: not r.display_name)
    if empties:
        _ORIGINAL_COMPUTE_DISPLAY_NAME(empties)
BaseModel._compute_display_name = _cyllo_compute_display_name
