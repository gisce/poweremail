# -*- coding: utf-8 -*-
from tools import config
from oopgrade.oopgrade import MigrationHelper


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    helper = MigrationHelper(cursor, 'poweremail')
    helper.update_xml_records(
        xml_path='poweremail_send_wizard.xml',
        update_record_ids=['poweremail_send_wizard_form']
    )


def down(cursor, installed_version):
    pass


