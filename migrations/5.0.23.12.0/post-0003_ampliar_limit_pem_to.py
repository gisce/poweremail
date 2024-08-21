# coding=utf-8
import logging
from tqdm import tqdm
from tools import config

logger = logging.getLogger('openerp.migration.' + __name__)


def up(cursor, installed_version):
    if not installed_version:
        return

    if config.updating_all:
        return

    cursor.execute("alter table poweremail_mailbox alter column pem_to type character varying(800);")


def down(cursor, installed_version):
    pass


migrate = up
