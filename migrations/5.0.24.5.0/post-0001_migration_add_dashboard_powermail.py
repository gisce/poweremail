# -*- coding: utf-8 -*-
import logging
import pooler
from oopgrade.oopgrade import load_data, load_data_records


def up(cursor, installed_version):
    if not installed_version:
        return
    logger = logging.getLogger('openerp.migration')
    logger.info("Creating pooler")
    pool = pooler.get_pool(cursor.dbname)

    logger.info("Updating XML wizard/wizard_accions_massives_lot_view.xml")
    load_data(
        cursor, 'poweremail', 'poweremail_dashboard.xml', idref=None, mode='update'
    )
    logger.info("XMLs succesfully updated.")

def down(cursor, installed_version):
    pass

migrate = up