# -*- coding: utf-8 -*-

from oopgrade.oopgrade import MigrationHelper, load_data
from tools import config


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    helper = MigrationHelper(cursor, 'poweremail')
    helper.init_model(model_name='poweremail.account.domain')
    helper.init_model(model_name='poweremail.core_accounts')
    load_data(
        cursor,
        'poweremail',
        'security/ir.model.access.csv',
        mode='update',
    )
    helper.update_xml_records(
        xml_path='poweremail_core_view.xml',
        update_record_ids=['poweremail_core_accounts_form'],
    )


def down(cursor, installed_version):
    pass


migrate = up
