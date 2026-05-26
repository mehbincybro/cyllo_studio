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

from odoo import _, api, fields, models
from odoo.exceptions import UserError
import json

# TRACKED_PRODUCT_FIELDS = [
#         'name', 'default_code', 'barcode', 'categ_id', 'list_price',
#         'standard_price', 'uom_id', 'uom_po_id', 'description',
#         'description_sale', 'description_picking', 'taxes_id',
#         'supplier_taxes_id', 'type', 'tracking', 'weight', 'volume',
#         'sale_ok', 'purchase_ok', 'active', 'version',
#         # add any other fields you want to track
#     ]

EXCLUDED_FIELDS = {
    # System/technical fields that should never be tracked
    'id', 'create_uid', 'create_date', 'write_uid', 'write_date',
    '__last_update', 'display_name', 'image_1920', 'image_1024',
    'image_512', 'image_256', 'image_128', 'activity_ids',
    'message_ids', 'message_follower_ids', 'website_message_ids',
    'rating_ids', 'product_variant_ids', 'product_variant_id',
    'product_variant_count', 'packaging_ids', 'seller_ids',
    'bom_ids', 'bom_count', 'used_in_bom_count',
    'has_configurable_attributes', 'is_product_variant',
    'can_image_1024_be_zoomed', 'image_1920',
    'product_properties',  # properties field
    'description_picking', 'description_pickingout', 'description_pickingin',
    'purchase_line_warn_msg', 'sale_line_warn_msg',
    'description_purchase',
}

EXCLUDED_FIELD_TYPES = {
    'one2many', 'binary', 'html', 'properties',
}


class PlmEco(models.Model):
    """ Engineering Change Order (ECO) Model. """
    _name = 'plm.eco'
    _description = 'Engineering Change Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
    )
    product_id = fields.Many2one(
        'product.template',
        string='Product',
        tracking=True,
    )
    bom_id = fields.Many2one(
        'mrp.bom',
        string='Bill of Materials',
        tracking=True,
    )
    type_id = fields.Many2one(
        'plm.eco.type',
        string='ECO Type',
        required=True,
        tracking=True,
    )
    eco_type = fields.Selection(
        related='type_id.eco_type',
        string='Type Category',
        store=True,
    )
    description = fields.Text(
        string='Description',
    )
    requested_by = fields.Many2one(
        'res.users',
        string='Requested By',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )


    # FOR COMPARISON, EVEN IN EFFECTIVE STAGE
    original_bom_id = fields.Many2one(
        'mrp.bom',
        string="Original BoM",
        readonly=True,
    )

    comparison_bom_id = fields.Many2one(
        'mrp.bom',
        string="Compared Revised BoM",
        readonly=True,
    )

    diff_snapshot_html = fields.Html(string='Diff Snapshot')
    product_snapshot = fields.Text(string='Product Snapshot')

    document_ids = fields.One2many(
        'document.file',
        'eco_id',
        string='Documents'
    )


    stage_id = fields.Many2one(
        'plm.eco.stage',
        string='Stage',
        required=True,
        default=lambda self: self._default_stage_id(),
        group_expand='_read_group_stage_ids',
        tracking=True,
    )

    is_new_stage = fields.Boolean(compute='_compute_stage_flags')
    is_progress_stage = fields.Boolean(compute='_compute_stage_flags')
    is_done_stage = fields.Boolean(compute='_compute_stage_flags')
    is_cancelled_stage = fields.Boolean(compute='_compute_stage_flags')

    new_bom_version = fields.Char(
        string='Version',
        related='revised_bom_id.version',
    )
    new_product_version = fields.Char(
        string='Version',
        related='product_id.version',
    )

    apply_on = fields.Selection(
        [
            ('product', 'Product'),
            ('bom', 'BoM')
        ],
        string="Apply On",
        related="type_id.eco_type",
        readonly=True
    )

    revised_bom_id = fields.Many2one('mrp.bom', string="New revised BoM", readonly=True)
    document_count = fields.Integer(compute='_compute_document_count')
    company_id= fields.Many2one("res.company", string="Company", compute="_compute_company_id", store=True)

    @api.depends("product_id", "bom_id")
    def _compute_company_id(self):
        for rec in self:
            if rec.product_id:
                rec.company_id = rec.product_id.company_id
            elif rec.bom_id:
                rec.company_id = rec.bom_id.company_id
            else:
                rec.company_id = False


    @api.depends('stage_id')
    def _compute_stage_flags(self):
        for eco in self:
            eco.is_new_stage = eco.stage_id and not eco.stage_id.in_progress and not eco.stage_id.done and not eco.stage_id.cancelled
            eco.is_progress_stage = eco.stage_id.in_progress if eco.stage_id else False
            eco.is_done_stage = eco.stage_id.done if eco.stage_id else False
            eco.is_cancelled_stage = eco.stage_id.cancelled if eco.stage_id else False

    def action_start_revision(self):
        self.ensure_one()
        progress_stage = self.env['plm.eco.stage'].search([('in_progress', '=', True)], order='sequence, id', limit=1)
        if not progress_stage:
            raise UserError(_("No progress stage configured in the system."))
        if self.apply_on == 'product' and self.product_id:
            self.product_snapshot = self._capture_product_snapshot()
        self.stage_id = progress_stage.id

    def action_apply_revision(self):
        self.ensure_one()
        done_stage = self.env['plm.eco.stage'].search([('done', '=', True)], limit=1)
        if not done_stage:
            raise UserError(_("No completed (Done) stage configured in the system."))

        wizard_model = self.env['plm.eco.compare.wizard']
        self.diff_snapshot_html = wizard_model._generate_html_diff(self)

        self.stage_id = done_stage.id

    def action_cancel_revision(self):
        self.ensure_one()
        cancelled_stage = self.env['plm.eco.stage'].search([('cancelled', '=', True)], limit=1)
        if not cancelled_stage:
            raise UserError(_("No cancelled stage configured in the system."))
        self.stage_id = cancelled_stage.id



    def _default_stage_id(self):
        """ Find the default first stage. """
        stage = self.env['plm.eco.stage'].search([], order='sequence, id', limit=1)
        return stage.id if stage else False

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """ Group by stage to display stages correctly in kanban columns. """
        return self.env['plm.eco.stage'].search([], order=order)

    @api.model_create_multi
    def create(self, vals_list):
        """ Generate sequence-based name on creation. """
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('plm.eco') or '/'
        ecos = super(PlmEco, self).create(vals_list)
        for eco in ecos:
            if eco.stage_id.in_progress:
                # Trigger progress actions
                if eco.apply_on == 'bom' and eco.bom_id and not eco.revised_bom_id:
                    source_bom = eco.bom_id
                    new_bom = source_bom.copy({
                        'active': False,
                        'version': eco._increment_version(source_bom.version or '1')
                    })
                    eco.revised_bom_id = new_bom.id
            elif eco.stage_id.done:
                # Trigger done actions
                if eco.apply_on == 'bom' and eco.bom_id:
                    if not eco.revised_bom_id:
                        source_bom = eco.bom_id
                        new_bom = source_bom.copy({
                            'active': False,
                            'version': eco._increment_version(source_bom.version or '1')
                        })
                        eco.revised_bom_id = new_bom.id
                    eco.revised_bom_id.action_unarchive()
                    eco.bom_id.action_archive()
                    eco.revised_bom_id.update({
                        'eco_ids' : [fields.Command.set(eco.bom_id.eco_ids.ids)]
                    })
                elif eco.apply_on == 'product' and eco.product_id:
                    eco._increment_version(eco.product_id.version or '1')
        return ecos

    def write(self, vals):
        """ Intercept stage transitions and execute workflow actions. """
        if 'stage_id' in vals:
            for eco in self:
                old_stage = eco.stage_id
                new_stage = self.env['plm.eco.stage'].browse(vals['stage_id'])

                # Prevent Effective → Progress/Cancelled
                if old_stage.done and (new_stage.in_progress or new_stage.cancelled):
                    raise UserError(
                        _("An ECO in Effective stage cannot be moved back to In Progress or Cancelled stage.")
                    )

                # If moving to progress stage
                if new_stage.in_progress and not old_stage.in_progress:
                    if eco.apply_on == 'bom' and eco.bom_id and not eco.revised_bom_id:
                        source_bom = eco.bom_id
                        new_bom = source_bom.copy({
                            'active': False,
                            'version': eco._increment_version(source_bom.version or '1')
                        })
                        eco.write({
                            'original_bom_id': source_bom.id,
                            'comparison_bom_id': new_bom.id,
                            'revised_bom_id': new_bom.id,
                        })
                # If moving to done stage
                elif new_stage.done and not old_stage.done:
                    if eco.apply_on == 'bom' and eco.bom_id:
                        if not eco.revised_bom_id:
                            source_bom = eco.bom_id
                            new_bom = source_bom.copy({
                                'active': False,
                                'version': eco._increment_version(source_bom.version or '1')
                            })
                            eco.write({
                                'original_bom_id': source_bom.id,
                                'comparison_bom_id': new_bom.id,
                                'revised_bom_id': new_bom.id,
                            })
                        eco.revised_bom_id.action_unarchive()
                        eco.bom_id.action_archive()
                        eco.revised_bom_id.update({
                            'eco_ids' : [fields.Command.set(eco.bom_id.eco_ids.ids)]
                        })
                    elif eco.apply_on == 'product' and eco.product_id:
                        eco.product_id.version = eco._increment_version(eco.product_id.version or '1')


        return super(PlmEco, self).write(vals)

    def _increment_version(self, current_version):
        """ Increments versions (e.g. 1 -> 2, V1 -> V2, etc.) """
        if not current_version:
            return '1'
        import re
        if current_version.isdigit():
            return str(int(current_version) + 1)
        match = re.search(r'(\d+)$', current_version)
        if match:
            num = int(match.group(1))
            new_num = str(num + 1)
            return current_version[:-len(match.group(1))] + new_num
        return current_version + '1'


    def action_show_bom(self):
        self.ensure_one()
        if self.bom_id:
            return {
                'name': _('BoM'),
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.bom',
                'view_mode': 'form',
                'res_id': self.revised_bom_id.id,
            }



    def action_show_product(self):
        """ Open the product template form view. """
        self.ensure_one()

        return {
            'name': _('Product'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'view_mode': 'form',
            'res_id': self.product_id.id,
        }


    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['document.file'].search_count([('eco_id', '=', rec.id)])

    def action_show_documents(self):
        self.ensure_one()
        workspace = self.env['document.workspace'].search([('name', '=', 'PLM')], limit=1)
        workspace_id = workspace.id if workspace else False

        from odoo.http import request
        if request:
            request.session['active_eco_id'] = self.id

        return {
            'name': _('Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.file',
            'view_mode': 'kanban,tree,form',
            'domain': [('eco_id', '=', self.id)],
            'context': {
                'default_eco_id': self.id,
                'default_workspace_id': workspace.id,
            }
        }

    def action_compare_revisions(self):
        self.ensure_one()
        return {
            'name': _('Compare Revisions'),
            'type': 'ir.actions.act_window',
            'res_model': 'plm.eco.compare.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_eco_id': self.id,
            }
        }

    def _capture_product_snapshot(self):
        product = self.product_id
        snapshot = {}

        for field_name, field in product._fields.items():
            if field_name in EXCLUDED_FIELDS:
                continue
            if field.type in EXCLUDED_FIELD_TYPES:
                continue
            if not field.store:  # skip computed non-stored fields
                continue
            try:
                val = product[field_name]
                snapshot[field_name] = self._normalize_field_value(val)
            except Exception:
                continue
        return json.dumps(snapshot)

    def _normalize_field_value(self, val):
        if val is False or val is None or val == '':
            return ''
        if hasattr(val, 'ids'):  # Many2many — before display_name
            return ', '.join(sorted(val.mapped('display_name')))
        if hasattr(val, 'display_name'):  # Many2one
            return val.display_name or ''
        if isinstance(val, float) and val == 0.0:
            return ''  # treat 0.0 as empty too
        return str(val)