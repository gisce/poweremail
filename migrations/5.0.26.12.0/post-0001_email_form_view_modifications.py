# -*- coding: utf-8 -*-
from tools import config
from oopgrade.oopgrade import load_data, MigrationHelper

def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    # Update all views and menuitems across the modified XML files
    load_data(cursor, 'poweremail', 'poweremail_core_view.xml', idref=None, mode='update')
    load_data(cursor, 'poweremail', 'poweremail_mailbox_view.xml', idref=None, mode='update')

    helper = MigrationHelper(cursor, 'poweremail')
    helper.update_xml_records(
        xml_path='wizard/wizard_emails_generats.xml',
        update_record_ids=[
            'menu_wizard_emails_generats'
        ]
    )

def down(cursor, installed_version):
    pass

migrate = up