# -*- coding: utf-8 -*-
from tools import config
from tools.translate import trans_load
from oopgrade.oopgrade import MigrationHelper

def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    module = 'poweremail'
    helper = MigrationHelper(cursor, module_name=module)

    helper.init_model('ir.actions.report.xml')

    helper.update_xml_records(
        xml_path='poweremail_template_view.xml',
        init_record_ids=[
            'act_report_xml_view_poweremail'
        ]
    )

    # Translations
    trans_load(cursor, '{}/{}/i18n/es_ES.po'.format(config['addons_path'], module), 'es_ES')
    trans_load(cursor, '{}/{}/i18n/ca_ES.po'.format(config['addons_path'], module), 'ca_ES')

def down(cursor, installed_version):
    pass

migrate = up
