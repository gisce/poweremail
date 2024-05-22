# -*- coding: utf-8 -*-
import logging
from oopgrade.oopgrade import load_data_records
import pooler


def up(cursor, installed_version):
    if not installed_version:
        return

    pool = pooler.get_pool(cursor.dbname)
    logger = logging.getLogger('openerp.migration')

    logger.info("Adding related column to poweremail.templates")
    pool.get("poweremail.templates")._auto_init(cursor, context={'module': 'poweremail'})
    logger.info("Related column loaded successfully.")

    view = "poweremail_template_view.xml"
    view_record = [
        "poweremail_template_form",
    ]
    logger.info("Updating XML {}".format(view))

    load_data_records(cursor, 'poweremail', view, view_record, mode='update')

    logger.info("XMLs succesfully updated.")


def down(cursor, installed_version):
    pass


migrate = up
