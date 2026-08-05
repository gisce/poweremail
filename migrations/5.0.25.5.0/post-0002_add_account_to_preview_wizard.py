# -*- coding: utf-8 -*-
from oopgrade.oopgrade import load_data_records
from tools.translate import trans_load
from tools import config


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    module_name = 'poweremail'

    list_of_records = [
        'poweremail_preview_form'
    ]
    load_data_records(
        cursor, module_name, 'wizard/wizard_poweremail_preview.xml',
        list_of_records, mode='update')

    trans_load(cursor, '{}/poweremail/i18n/ca_ES.po'.format(config['addons_path']), 'ca_ES')
    trans_load(cursor, '{}/poweremail/i18n/es_ES.po'.format(config['addons_path']), 'es_ES')


def down(cursor, installed_version):
    pass


migrate = up
