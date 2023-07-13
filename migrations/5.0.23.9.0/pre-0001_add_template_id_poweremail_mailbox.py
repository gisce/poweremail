# coding=utf-8
import logging
from oopgrade import oopgrade


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')
    logger.info('Adding template_id column to poweremail mailbox table...')
    oopgrade.add_columns(
        cursor, {
            'poweremail_mailbox': [
                ('template_id', 'many2one'),
            ]
        }
    )
    logger.info('Column added')


def down(cursor, installed_version):
    pass


migrate = up
