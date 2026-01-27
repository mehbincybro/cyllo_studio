# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class DocumentTrash(models.Model):
    """module to store deleted documents for a specific time, then it automatically """
    _name = 'document.trash'
    _description = 'Document Trash'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(help="Document name")
    attachment = fields.Binary(string='File', readonly=True, help="Document data")
    date = fields.Datetime(help="Document create date")
    workspace_id = fields.Many2one('document.workspace', required=True, help="workspace name")
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user,
                              help="Document owner name, if the document belongs to a specific partner")
    brochure_url = fields.Char(string="URL", help="Document sharable URL")
    extension = fields.Char(help="Document extension, helps to determine the file type")
    priority = fields.Selection([('0', 'None'), ('1', 'Favorite')], help="Favorite button")
    attachment_id = fields.Many2one('ir.attachment',
                                    help="Attachment associated with the document request")
    content_url = fields.Char(help="URL associated with the document content")
    content_type = fields.Selection([('file', 'File'), ('url', 'Url')],
                                    help="Document content type")
    preview = fields.Char(help="Preview URL")
    active = fields.Boolean(help="Indicates if the document request is active or not", default=True)
    deleted_date = fields.Date(help="Document auto delete date")
    mimetype = fields.Char(string='Mime Type', help="Document mimetype")
    description = fields.Text(help="Description of the document")
    security = fields.Selection(
        selection=[('private', 'Private'), ('managers_and_owner', 'Managers & Owner'),
                   ('specific_users', 'Specific Users')], default='managers_and_owner',
        help="Private: only the uploaded user can view, Managers & Owner: Document shared with Managers",
        string="Security Type")
    user_ids = fields.Many2many('res.users', help="Document related users")
    partner_id = fields.Many2one('res.partner', help="Document related")
    auto_delete = fields.Boolean(default=False, help="Document delete status")
    days = fields.Integer(help="auto delete in days")
    delete_date = fields.Date(string='Date Delete', help="Date when the document will be deleted")
    file_url = fields.Char(help="it store url while adding an url document")

    @api.onchange('days')
    def _onchange_days(self):
        """Set the delete date for a record based on the specified number of days. This function calculates and sets
        the delete date for a record by adding the specified number of days to the current date. The record will be
        automatically deleted on the calculated delete date.
        :return: None """
        self.write({'delete_date': fields.Date.add(fields.Date.today(), days=self.days)})

    def action_restore_document(self):
        """ Restore a previously deleted document from the trash. This function restores a deleted document by
        creating a new record in the 'document.file' model with the same attributes as the deleted document. It then
        unlinks the deleted document and returns to the 'Trash' view.
        :return: Window action to view the 'Trash' or restore the document.
        :rtype: dict """
        doc_id = self.env['document.file'].create({
            'name': self.name,
            'extension': self.extension,
            'attachment': self.attachment,
            'date': fields.Date.today(),
            'workspace_id': self.workspace_id.id,
            'user_id': self.user_id.id,
            'content_type': self.content_type,
            'brochure_url': self.brochure_url,
            'active': self.active,
            'mimetype': self.mimetype,
            'description': self.description,
            'content_url': self.content_url,
            'user_ids': self.user_ids.ids,
            'partner_id': self.partner_id,
            'days': self.days,
        })
        attachment_id = self.env['ir.attachment'].sudo().create({'name': self.name,
                                                                 'datas': self.attachment,
                                                                 'res_model': 'document.file',
                                                                 'res_id': self.id,
                                                                 })
        doc_id.attachment_id = attachment_id.id
        self.unlink()
        return {
            'name': _('Trash'),
            'target': 'main',
            'view_mode': 'tree,form',
            'res_model': 'document.trash',
            'type': 'ir.actions.act_window',
        }

    def auto_delete_doc(self):
        """Automatically delete documents based on a schedule action. This function searches for documents marked
        for automatic deletion (auto_delete=True) and with a delete date less than or equal to the current date.
        It then deletes these documents from the system.
        :return: None"""
        self.search([('auto_delete', '=', True), ('delete_date', '<=', fields.Date.today())]).unlink()
