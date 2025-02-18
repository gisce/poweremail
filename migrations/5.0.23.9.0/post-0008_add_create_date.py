# -*- coding: utf-8 -*-
import logging
from oopgrade.oopgrade import load_data_records


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')

    logger.info('Adding the menu to see all the emails')

    view = "poweremail_mailbox_view.xml"
    view_record = [
        "poweremail_all_emails_tree",
        "poweremail_inbox_tree",
        "poweremail_drafts_tree",
        "poweremail_outbox_tree",
        "poweremail_sentbox_tree",
        "poweremail_followbox_tree",
        "poweremail_trashbox_tree",
        "poweremail_errorbox_tree",
    ]
    logger.info("Updating XML {}".format(view))
    load_data_records(
        cursor, 'poweremail', view, view_record, mode='update'
    )
    logger.info('XML successfully updated.')


def down(cursor, installed_version):
    pass


migrate = up