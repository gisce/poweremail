# -*- coding: utf-8 -*-
import logging
import pooler

from tools import config
from oopgrade.oopgrade import load_data_records


def up(cursor, installed_version):
    if not installed_version:
        return
    if config.updating_all:
        return
    logger = logging.getLogger('openerp.migration')

    logger.info("Creating pooler")
    pool = pooler.get_pool(cursor.dbname)

    logger.info("Creating table: giscedata.polissa")
    pool.get("poweremail.templates")._auto_init(cursor, context={'module': 'poweremail'})
    logger.info("Table created succesfully.")

    logger.info("Updating XMLs")
    list_of_records = [
        "poweremail_template_form",
    ]
    load_data_records(
        cursor, 'poweremail', 'poweremail_template_view.xml', list_of_records, mode='update'
    )
    logger.info("XMLs succesfully updated.")


def down(cursor, installed_version):
    pass


migrate = up