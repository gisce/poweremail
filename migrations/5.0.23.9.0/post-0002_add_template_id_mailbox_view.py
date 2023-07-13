import logging
from oopgrade.oopgrade import load_data_records


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')
    logger.info('Updating account mailbox view (poweremail_mailbox_form)...')
    load_data_records(
        cursor, 'poweremail',
        'poweremail_mailbox_view.xml', ['poweremail_mailbox_form']
    )
    logger.info('View updated (poweremail_mailbox_form)!')


def down(cursor, installed_version):
    pass


migrate = up
