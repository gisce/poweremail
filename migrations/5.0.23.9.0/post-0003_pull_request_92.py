# -*- coding: utf-8 -*-
import logging
import pooler
from oopgrade.oopgrade import load_data, load_data_records


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')
    model = 'wizard.generate.test.email'
    pool = pooler.get_pool(cursor.dbname)
    if pool.get(model):
        logger.info('Migration script for pull request #92 not necessary.')
    else:
        logger.info('Migration script for pull request #92...')
        logger.info("Creating model: {}...".format(model))
        pool.get(model)._auto_init(cursor, context={'module': 'poweremail'})
        # permissions added in #107
        # logger.info("Updating permissions...")
        # load_data(
        #     cursor, 'poweremail', 'security/ir.model.access.csv', mode='update'
        # )
        logger.info("Creating views...")
        load_data(
            cursor, 'poweremail', "wizard/wizard_generate_test_email.xml", mode='init'
        )
        load_data_records(
            cursor, 'poweremail', "poweremail_template_view.xml", [
                'poweremail_basic_template_form',
                'poweremail_basic_template_tree',
                'action_poweremail_basic_template_all',
                'action_poweremail_basic_template_tree_all',
                'action_poweremail_basic_template_form_all',
                'menu_poweremail_basic_templates_all',
            ], mode='init'
        )
        logger.info('Migration script for pull request #92 finished succesfully.')


def down(cursor, installed_version):
    pass


migrate = up
