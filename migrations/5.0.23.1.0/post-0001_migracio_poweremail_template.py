# -*- coding: utf-8 -*-
import logging
import pooler
from oopgrade.oopgrade import load_data


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')

    logger.info("Creating pooler")
    pool = pooler.get_pool(cursor.dbname)

    models = [
        "poweremail.templates"
    ]

    views = [
        "poweremail_template_view.xml"
    ]

    for model in models:
        # Crear les diferents taules
        logger.info("Creating table: {}".format(model))
        pool.get(model)._auto_init(cursor, context={'module': 'poweremail'})
        logger.info("Table created succesfully.")

    for view in views:
        # Crear les diferents vistes
        logger.info("Updating XML {}".format(view))
        load_data(cursor, 'poweremail', view, idref=None, mode='update')
        logger.info("XMLs succesfully updatd.")


def down(cursor, installed_version):
    pass


migrate = up
