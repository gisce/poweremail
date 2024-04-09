# -*- coding: utf-8 -*-
import logging
import pooler
from oopgrade.oopgrade import load_data, load_data_records


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')

    logger.info("Creating pooler")
    pool = pooler.get_pool(cursor.dbname)

    ##UPDATAR UN MODUL NOU AL CREAR-LO O AFEGIR UNA COLUMNA##
    logger.info("Creating table: poweremail.mailbox")
    pool.get("poweremail.mailbox")._auto_init(cursor, context={'module': 'poweremail'})
    logger.info("Table created succesfully.")

    ##UPATAR UN XML SENCER##
    logger.info("Updating XML poweremail_mailbox_cronjobs.xml")
    load_data(
        cursor, 'poweremail', 'poweremail_mailbox_cronjobs.xml', idref=None, mode='update'
    )
    logger.info("XMLs succesfully updated.")


def down(cursor, installed_version):
    pass


migrate = up