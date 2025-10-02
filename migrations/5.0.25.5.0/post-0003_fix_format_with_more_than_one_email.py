# -*- coding: utf-8 -*-
from tools import config


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    cursor.execute("UPDATE res_partner_address SET email = REPLACE(email, ';', ',') WHERE email LIKE '%;%'")

def down(cursor, installed_version):
    pass


migrate = up
