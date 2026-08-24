# -*- coding: utf-8 -*-
from tools import config
from oopgrade.oopgrade import MigrationHelper

def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    helper = MigrationHelper(cursor, 'poweremail')

    helper.init_model('ir.actions.report.xml')

    helper.update_xml_records(
        xml_path='poweremail_template_view.xml',
        init_record_ids=[
            'act_report_xml_view_poweremail'
        ]
    )

def down(cursor, installed_version):
    pass

migrate = up
