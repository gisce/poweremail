# -*- coding: utf-8 -*-
from oopgrade.oopgrade import load_data_records
from tools import config
from tools.translate import trans_load


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    load_data_records(
        cursor, 'poweremail', "poweremail_template_view.xml", [
            "poweremail_template_form"
        ], mode='update')

    trans_load(cursor, '{}/{}/i18n/ca_ES.po'.format(config['addons_path'], 'poweremail'), 'ca_ES')
    trans_load(cursor, '{}/{}/i18n/es_ES.po'.format(config['addons_path'], 'poweremail'), 'es_ES')


def down(cursor, installed_version):
    pass


migrate = up
