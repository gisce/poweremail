# -*- coding: utf-8 -*-
import logging

from tools import config
from oopgrade.oopgrade import load_data, MigrationHelper

def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return
    logger = logging.getLogger('openerp.migration')

    logger.info('Loading new XML poweremail_dashboard.xml')
    helper = MigrationHelper(cursor, 'poweremail')
    helper.update_xml(
        xml_path='poweremail_dashboard.xml',
        mode='init'
    )
    logger.info('XML successfully loaded')

def down(cursor, installed_version):
    pass

migrate = up