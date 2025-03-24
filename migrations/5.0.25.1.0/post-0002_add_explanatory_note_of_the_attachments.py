# -*- coding: utf-8 -*-
from tools import config
from oopgrade.oopgrade import load_data_records


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return
    load_data_records(
        cursor, 'poweremail', "poweremail_template_view.xml", [
        "poweremail_template_form"
    ], mode='init')


def down(cursor, installed_version):
    pass


migrate = up
