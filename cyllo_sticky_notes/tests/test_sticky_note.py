# -*- coding: utf-8 -*-
from odoo.tests import common


class TestStickyNotes(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.sticky_note = cls.env['sticky.note'].create({
            'title': 'Test note',
            'description': 'This note is created to test',
            'company_id': cls.env.company.id
        })

    def test_edit_note(self):
        args = {'title': 'Edited title', 'description': 'Edited description', 'id': self.sticky_note.id}
        self.sticky_note.edit_note(args)
        self.assertEqual(self.sticky_note.title, 'Edited title')
        self.assertEqual(self.sticky_note.description, 'Edited description')
