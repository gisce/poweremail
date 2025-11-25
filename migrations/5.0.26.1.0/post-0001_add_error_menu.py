# -*- coding: utf-8 -*-
from oopgrade.oopgrade import MigrationHelper


def up(cursor, installed_version):
    from tools import config
    if config.updating_all or not installed_version:
        return

    module = 'giscedata_telegestio'
    helper = MigrationHelper(cursor, module)
    record_list = [
        'action_poweremail_error_tree_personal',
        'menu_poweremail_error_personal',

    ]
    helper.update_xml_records('oorq_view.xml', update_record_ids=record_list)



def down(cursor, installed_version):
    pass


migrate = up