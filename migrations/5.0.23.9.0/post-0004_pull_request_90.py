# -*- coding: utf-8 -*-
import logging
import pooler
from oopgrade.oopgrade import load_data


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')
    model = 'wizard.send.email'
    pool = pooler.get_pool(cursor.dbname)
    q_check_model_exists = """
        SELECT * FROM ir_model_data WHERE name = 'model_wizard_send_email'
    """
    cursor.execute(q_check_model_exists)
    res = cursor.fetchall()
    if res:
        logger.info('Migration script for pull request #90 not necessary.')
    else:
        logger.info('Migration script for pull request #90...')
        logger.info("Creating model: {}...".format(model))
        pool.get(model)._auto_init(cursor, context={'module': 'poweremail'})
        logger.info("Updating permissions...")
        load_data(
            cursor, 'poweremail', 'security/ir.model.access.csv', mode='update'
        )
        logger.info("Creating views...")
        load_data(
            cursor, 'poweremail', "wizard/wizard_send_email.xml", mode='init'
        )
        logger.info('Migration script for pull request #90 finished succesfully.')


def down(cursor, installed_version):
    pass


migrate = up
