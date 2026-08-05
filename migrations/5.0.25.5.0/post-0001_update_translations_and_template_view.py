# -*- coding: utf-8 -*-
from tools import config
from tools.translate import trans_load
from oopgrade.oopgrade import load_data_records


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return
    module_name = 'poweremail'
    load_data_records(
        cursor, module_name, "poweremail_template_view.xml", ["poweremail_template_form"], mode='update')

    module_lang = 'en_US'
    cursor.execute("SELECT code FROM res_lang WHERE code != %s", (module_lang,))
    for res in cursor.fetchall():
        trans_load(cursor, '{}/{}/i18n/es_ES.po'.format(config['addons_path'], module_name), res[0])


def down(cursor, installed_version):
    pass


migrate = up
