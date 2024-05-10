# -*- coding: utf-8 -*-
import logging
import pooler
from oopgrade.oopgrade import load_data_records

def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')

    logger.info("Creating pooler")
    pool = pooler.get_pool(cursor.dbname)

    logger.info("Updating XML's")
    list_of_records = [
        "action_poweremail_enviats_avui",
        "board_poweremail_enviats_avui",
        "action_poweremail_emails_rebuts_avui",
        "view_poweremail_emails_ultims_60_dies",
        "action_poweremail_emails_ultims_60_dies"
    ]
    load_data_records(
        cursor, 'poweremail', 'poweremail_dashboard.xml', list_of_records, mode='update'
    )
    logger.info("XMLs succesfully updated.")

def down(cursor, installed_version):
    pass

migrate = up