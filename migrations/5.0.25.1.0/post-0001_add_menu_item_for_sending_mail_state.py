# -*- coding: utf-8 -*-
from tools import config
from oopgrade.oopgrade import load_data_records


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return
    load_data_records(
        cursor, 'poweremail', "poweremail_mailbox_view.xml", [
        "action_poweremail_sending_tree",
        "action_poweremail_sending_tree_company",
        "menu_action_poweremail_sending_tree_company",
        "menu_action_poweremail_sending_tree"
    ], mode='init')


def down(cursor, installed_version):
    pass


migrate = up
