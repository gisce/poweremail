# -*- coding: utf-8 -*-
import logging
import pooler
from oopgrade.oopgrade import load_data, load_data_records, add_columns


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')
    q_check_columns_exists = """
        SELECT * FROM information_schema.columns
        WHERE table_name = 'poweremail_templates'
        AND column_name = 'attach_record_items'
    """
    cursor.execute(q_check_columns_exists)
    res = cursor.fetchall()
    if res:
        logger.info('Migration script for pull request #100...')
        logger.info('Adding column attach_record_items to poweremail_templates table')
        add_columns(cursor, {
            'poweremail_templates': [('attach_record_items', 'boolean')]
        })
        load_data_records(
            cursor, 'poweremail', "poweremail_template_view.xml", [
                'poweremail_template_form',
            ], mode='init'
        )
        logger.info(
            'Migration script for pull request #100 finished succesfully.')

    else:
        logger.info('Migration script for pull request #100 not necessary.')


def down(cursor, installed_version):
    pass


migrate = up
