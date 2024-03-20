# -*- coding: utf-8 -*-
import logging
import pooler
from oopgrade.oopgrade import load_data, load_data_records


def up(cursor, installed_version):
    if not installed_version:
        return
    pool = pooler.get_pool(cursor.dbname)
    logger = logging.getLogger('openerp.migration')

    pool.get("poweremail.preview")._auto_init(cursor, context={'module': 'poweremail'})
    logger.info("Updating XML wizard_poweremail_preview.xml")
    load_data_records(
        cursor, 'poweremail', 'wizard/wizard_poweremail_preview.xml', ['poweremail_preview_form'], mode='update')
    logger.info("XMLs succesfully updated.")


def down(cursor, installed_version):
    pass

migrate = up
