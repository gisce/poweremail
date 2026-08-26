# coding=utf-8
from tools import config


def up(cursor, installed_version):
    if not installed_version:
        return
    if config.updating_all:
        return

    cursor.execute("""
        INSERT INTO res_config (name, value, description)
        SELECT
            'poweremail_templates_clear_error_on_success',
            '[]',
            'Select the specific IDs of the templates whose error records will be deleted if they were ultimately resubmitted successfully.'
        WHERE NOT EXISTS (
            SELECT 1
            FROM res_config
            WHERE name = 'poweremail_templates_clear_error_on_success'
        );
    """)


def down(cursor, installed_version):
    pass


migrate = up
