# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StickyNote(models.Model):
    """This class represents a Sticky Note model for storing note details"""
    _name = "sticky.note"
    _description = "Sticky Note"

    title = fields.Char(help="title of the note")
    description = fields.Char(help="description of the note")
    colour = fields.Char(help="color of the note", string="Color")
    create_date = fields.Datetime(string="Created Date", help="Create date of a note")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, help="Current Company")

    @api.model
    def edit_note(self, args):
        """Edit an existing Sticky Note with the provided arguments"""
        note_id = args['id']
        records = self.env['sticky.note'].browse(note_id)
        records.write(args)
