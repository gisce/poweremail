# -*- coding: utf-8 -*-
import logging
from oopgrade.oopgrade import column_exists, add_columns, drop_columns


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')
    columns = []
    # Crear les diferents columnes
    if column_exists(cursor, 'poweremail_templates', 'attach_record_items'):
        logger.info("'attach_record_items' already exists, skipping'")
    else:
        columns.append(('attach_record_items', 'boolean'))

    if columns:
        logger.info("Adding new columns...")
        add_columns(cursor, {
            'poweremail_templates': columns
        })
        logger.info("new columns added. Setting default value...")
        cursor.execute("""
            UPDATE poweremail_templates set attach_record_items = false
        """)
        logger.info("Done")

    logger.info('Migration successful.')


def down(cursor, installed_version):
    pass


migrate = up
