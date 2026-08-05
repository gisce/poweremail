# coding=utf-8
import logging
from oopgrade.oopgrade import load_data_records

logger = logging.getLogger('openerp.migration.' + __name__)


def up(cursor, installed_version):
    if not installed_version:
        return
    load_data_records(cursor, 'poweremail', 'poweremail_core_view.xml', [
        'action_poweremail_mailbox_error',
        'view_poweremail_mailbox_error_graph',
        'action_view_poweremail_mailbox_error_graph',
        'action_poweremail_mailbox_to_sent',
        'view_poweremail_mailbox_graph',
        'action_view_poweremail_mailbox_to_sent_graph',
        'action_poweremail_mailbox_sent',
        'action_view_poweremail_mailbox_sent_graph',
        'action_poweremail_mailbox_sent_today',
        'action_view_poweremail_mailbox_sent_today_graph',
        'poweremail_core_accounts_form',
    ])


def down(cursor, installed_version):
    pass


migrate = up
