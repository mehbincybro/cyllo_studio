# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.http import request


class WorkSpace(models.TransientModel):
    """model help to move, copy documents"""
    _name = 'work.space'
    _description = "Work Space"

    workspace_ids = fields.Many2many('document.workspace', required=True)
    doc_ids = fields.Many2many('document.file', help="Related documents", string='Document')
    move = fields.Boolean(compute="_compute_move", help="Indicates whether to perform a move operation")

    @api.depends('workspace_ids')
    def _compute_move(self):
        """ compute function to enable move function"""
        if len(self.workspace_ids) > 1:
            self.move = False
        else:
            self.move = True

    def action_copy_docs(self):
        """function to copy documents """
        for workspace in self.workspace_ids.ids:
            for rec in self.doc_ids:
                self.env['document.file'].create({
                    'name': rec.name,
                    'attachment': rec.attachment,
                    'brochure_url': rec.brochure_url,
                    'attachment_id': rec.attachment_id.id,
                    'mimetype': rec.mimetype,
                    'content_url':
                        f"""{request.httprequest.host_url[:-1]}/web/content/{rec.attachment_id.id}/{rec.name}""",
                    'date': fields.Datetime.today().now(),
                    'workspace_id': workspace,
                    'user_id': rec.user_id.id,
                    'extension': rec.name.split(".")[len(rec.name.split(".")) - 1]
                })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_move_docs(self):
        """function to move documents"""
        for rec in self.doc_ids:
            rec.write({'workspace_id': self.workspace_ids})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
