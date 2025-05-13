# -*- coding: utf-8 -*-
from oopgrade.oopgrade import load_data_records
from tools import config
import pooler


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


def down(cursor, installed_version):
    pass


migrate = up
