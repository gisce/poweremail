# -*- coding: utf-8 -*-

from tools.translate import trans_load
from tools import config


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    module = 'poweremail'
    trans_load(cursor, '{}/{}/i18n/es_ES.po'.format(config['addons_path'], module), 'es_ES')
    trans_load(cursor, '{}/{}/i18n/ca_ES.po'.format(config['addons_path'], module), 'ca_ES')


def down(cursor, installed_version):
    pass


migrate = up
