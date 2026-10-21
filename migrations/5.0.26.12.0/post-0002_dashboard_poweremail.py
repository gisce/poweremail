# -*- coding: utf-8 -*-
import logging

import pooler
from tools import config
from oopgrade.oopgrade import MigrationHelper

def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return
    logger = logging.getLogger('openerp.migration')

    logger.info('Loading new XML poweremail_dashboard.xml')

    uid = 1
    pool = pooler.get_pool(cursor.dbname)

    module = 'account_balance_reporting'

    helper = MigrationHelper(cursor, module)
    helper.update_xml(
        xml_path='poweremail_dashboard.xml',
        mode='init'
    )
    logger.info('XML successfully loaded')

    module_obj = pool.get('ir.module.module')
    module_id = module_obj.search(cursor, uid, [('name', '=', module)])
    if module_id:
        module_obj.update_translations(cursor, uid, module_id)

def down(cursor, installed_version):
    pass

migrate = up