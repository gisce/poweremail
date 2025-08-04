# -*- coding: utf-8 -*-

from oopgrade.oopgrade import load_data_records
from tools import config


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    list_of_records = [
        'action_template_emails',
        'value_template_emails',
    ]
    load_data_records(
        cursor, 'poweremail', 'poweremail_mailbox_view.xml',
        list_of_records, mode='init')


def down(cursor, installed_version):
    pass


migrate = up
