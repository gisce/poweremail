# -*- encoding: utf-8 -*-
import logging
import pooler
from oopgrade.oopgrade import load_data, load_data_records


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')

    ##UPDATAR UNA PART DE L'XML (POSAR LA ID)##
    logger.info("Updating XMLs")
    list_of_records = [
        "poweremail_template_form"
    ]
    load_data_records(
        cursor, 'poweremail', 'poweremail_template_view.xml',
        list_of_records, mode='update'
    )
    logger.info("XMLs succesfully updated.")


def down(cursor, installed_version):
    pass


migrate = up
