# -*- coding: utf-8 -*-
from oopgrade.oopgrade import load_data_records


def up(cursor, installed_version):
    if not installed_version:
        return

    load_data_records(cursor, 'poweremail', 'wizard/wizard_poweremail_preview.xml', ['poweremail_preview_form'])


def down(cursor, installed_version):
    pass


migrate = up
