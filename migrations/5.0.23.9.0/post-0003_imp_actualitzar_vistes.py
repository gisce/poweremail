# -*- coding: utf-8 -*-
import logging
from oopgrade.oopgrade import load_data_records


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')

    logger.info('Updating views...')

    load_data_records(
        cursor, 'poweremail', "poweremail_template_view.xml", [
            "poweremail_template_form",
            "poweremail_basic_template_form",
        ], mode='update'
    )
    load_data_records(
        cursor, 'poweremail', "wizard/wizard_poweremail_preview.xml", [
            "poweremail_preview_form",
            "wizard_poweremail_preview",
        ], mode='update'
    )
    logger.info('XML successfully updated.')


def down(cursor, installed_version):
    pass


migrate = up