# -*- coding: utf-8 -*-
from __future__ import absolute_import
import logging
from oopgrade.oopgrade import load_data_records

def up(cursor, installed_version):

    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')

    logger.info('Updating poweremail view...')

    load_data_records(
        cursor, 'poweremail',
        'wizard/wizard_poweremail_preview.xml',
        ['poweremail_preview_form'],
        mode='update'
    )

    logger.info('poweremail view successfully updated.')


def down(cursor, installed_version):
    pass


migrate = up