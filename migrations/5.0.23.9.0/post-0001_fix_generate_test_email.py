# -*- coding: utf-8 -*-
import logging
from oopgrade.oopgrade import load_data_records


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')

    logger.info('Fix generate test email...')

    view = "wizard/wizard_generate_test_email.xml"
    view_record = ["view_wizard_generate_email_form"]

    logger.info("Updating XML {}".format(view))
    load_data_records(cursor, 'poweremail', view, view_record, mode='update')
    logger.info("XMLs succesfully updated.")


def down(cursor, installed_version):
    pass


migrate = up