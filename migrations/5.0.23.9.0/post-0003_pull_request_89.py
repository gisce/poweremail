# -*- coding: utf-8 -*-
import logging
import pooler
from oopgrade.oopgrade import load_data


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')
    model = 'wizard.change.folder.email'
    pool = pooler.get_pool(cursor.dbname)
    if pool.get(model):
        logger.info('Migration script for pull request #89 not necessary.')
    else:
        logger.info('Migration script for pull request #89...')
        logger.info("Creating model: {}...".format(model))
        pool.get(model)._auto_init(cursor, context={'module': 'poweremail'})
        logger.info("Updating permissions...")
        load_data(
            cursor, 'poweremail', 'security/ir.model.access.csv', mode='update'
        )
        logger.info("Creating views...")
        load_data(
            cursor, 'poweremail', "wizard/wizard_poweremail.xml", mode='init'
        )
        logger.info('Migration script for pull request #89 finished succesfully.')


def down(cursor, installed_version):
    pass


migrate = up
