# -*- coding: utf-8 -*-
import logging
from oopgrade.oopgrade import load_data_records
from oopgrade.oopgrade import load_data
from tools.translate import trans_load
from tools import config


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')

    record_names = [
        'action_poweremail_inbox_tree',
        'action_poweremail_outbox_tree',
        'action_poweremail_drafts_tree',
        'action_poweremail_follow_tree',
        'action_poweremail_sent_tree',
        'action_poweremail_trash_tree',
        'action_poweremail_inbox_tree_company',
        'action_poweremail_outbox_tree_company',
        'action_poweremail_drafts_tree_company',
        'action_poweremail_follow_tree_company',
        'action_poweremail_sent_tree_company',
        'action_poweremail_sent_tree_company',
        'action_poweremail_trash_tree_company',
        'action_poweremail_error_tree_company'
    ]
    load_data_records(cursor, 'poweremail', 'poweremail_mailbox_view.xml', record_names, mode='update')
    load_data(
        cursor, 'poweremail', 'security/ir.model.access.csv', idref=None, mode='update'
    )
    logger.info("XMLs succesfully updatd.")
    trans_load(cursor, '{}/poweremail/i18n/ca_ES.po'.format(config['addons_path']), 'ca_ES')
    trans_load(cursor, '{}/poweremail/i18n/es_ES.po'.format(config['addons_path']), 'es_ES')


def down(cursor, installed_version):
    pass


migrate = up