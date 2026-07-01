# -*- coding: utf-8 -*-
from oopgrade.oopgrade import MigrationHelper
from tools import config

def up(cursor, installed_version):
    if config.updating_all or not installed_version:
        return

    module = 'poweremail'
    helper = MigrationHelper(cursor, module)
    record_ids = [
        'poweremail_preview_form',
    ]
    helper.update_xml_records('wizard/wizard_poweremail_preview.xml',
                              update_record_ids=record_ids)


def down(cursor, installed_version):
    pass


migrate = up