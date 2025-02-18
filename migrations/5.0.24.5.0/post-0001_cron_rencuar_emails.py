# -*- coding: utf-8 -*-
import logging
from oopgrade.oopgrade import load_data


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')

    ##UPATAR UN XML SENCER##
    logger.info("Updating XML poweremail_mailbox_cronjobs.xml")
    load_data(
        cursor, 'poweremail', 'poweremail_mailbox_cronjobs.xml', idref=None, mode='update'
    )
    logger.info("XMLs succesfully updated.")


def down(cursor, installed_version):
    pass


migrate = up