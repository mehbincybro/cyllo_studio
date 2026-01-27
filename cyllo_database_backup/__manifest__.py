# -*- coding: utf-8 -*-
{
    'name': "Database Backup Management",
    'version': "1.0",
    'summary': """Generate automatic backup of databases and store to local,
     google drive, dropbox, nextcloud, amazon S3, onedrive or remote server""",
    'description': """This module has been developed for creating database 
     backups automatically and store it to the different locations.""",
    'author': "Cyllo",
    'website': "https://www.cyllo.com",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'category': 'Extra Tools',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/backup_destination_data.xml',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'data/discuss_channel_data.xml',
        'wizards/dropbox_auth_code_views.xml',
        'views/db_backup_configure_views.xml',
        'views/backup_destination_views.xml',
    ],
    'external_dependencies': {
        'python': ['dropbox', 'pyncclient', 'boto3', 'nextcloud-api-wrapper',
                   'paramiko']},
    'installable': True,
    'license': 'LGPL-3',
    'auto_install': False,
    'application': False,
}
