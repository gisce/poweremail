# -*- coding: utf-8 -*-
import pooler
from tools import config
from oopgrade.oopgrade import load_data_records


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    pool = pooler.get_pool(cursor.dbname)
    pool.get("poweremail.template.attachment")._auto_init(cursor, context={'module': 'poweremail'})

    load_data_records(
        cursor, 'poweremail', "poweremail_template_view.xml", [
        "poweremail_template_form"
    ], mode='update')


def down(cursor, installed_version):
    pass


migrate = up
