# -*- coding: utf-8 -*-
from tools import config
from oopgrade.oopgrade import MigrationHelper
from tools.translate import trans_load


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    helper = MigrationHelper(cursor, 'poweremail')
    helper.update_xml_records(
        xml_path='poweremail_send_wizard.xml',
        update_record_ids=['poweremail_send_wizard_form']
    )
    trans_load(cursor, '{}/{}/i18n/ca_ES.po'.format(config['addons_path'], 'poweremail'), 'ca_ES')
    trans_load(cursor, '{}/{}/i18n/es_ES.po'.format(config['addons_path'], 'poweremail'), 'es_ES')


def down(cursor, installed_version):
    pass


