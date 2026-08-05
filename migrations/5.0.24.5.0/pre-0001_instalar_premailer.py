# coding=utf-8
import logging
from tools import pip_install


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger("openerp.migration")
    logger.info('Installing premailer package...')
    pip_install('premailer==2.9.6', '--force')
    logger.info('Premailer package installed successfully!')


def down(cursor, installed_version):
    pass


migrate = up
