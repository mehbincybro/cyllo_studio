# -*- coding: utf-8 -*-
from odoo import fields, models


class BackupDestination(models.Model):
    """DbBackup provides an interface to manage database
       backups of Local Server, Remote Server, Google Drive, Dropbox, Onedrive,
       Nextcloud and Amazon S3"""
    _name = 'backup.destination'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Database Backup Destination'

    name = fields.Char(help='Name of the location type')
    image = fields.Binary(help='Logo of backup destination')
    code = fields.Char(help='Code for destination locations')

    def action_create_request(self):
        """ This method is used to initiate a request for db backup creation"""
        return {
            "type": "ir.actions.act_window",
            "res_model": "db.backup.configure",
            'view_mode': 'tree,form',
            "name": 'Backup Creation',
            "domain": [('backup_destination', '=', self.code)],
            "context": {
                'default_backup_destination': self.code,
            },
        }
