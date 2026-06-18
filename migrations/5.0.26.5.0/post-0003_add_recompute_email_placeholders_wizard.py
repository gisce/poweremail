# -*- coding: utf-8 -*-
from tools import config
from oopgrade.oopgrade import MigrationHelper, load_data


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    helper = MigrationHelper(cursor, 'poweremail')
    helper.init_model(model_name='wizard.recompute.email.placeholders')
    helper.update_xml_records(
        xml_path='wizard/wizard_recompute_email_placeholders.xml',
        update_record_ids=[
            'action_wizard_recompute_email_placeholders',
            'value_wizard_recompute_email_placeholders',
            'view_wizard_recompute_email_placeholders',
        ],
    )
    load_data(
        cursor, 'poweremail', 'security/ir.model.access.csv', mode='update',
    )


def down(cursor, installed_version):
    pass


migrate = up
