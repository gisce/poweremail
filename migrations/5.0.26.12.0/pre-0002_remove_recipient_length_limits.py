# coding=utf-8


def up(cursor, installed_version):
    if not installed_version:
        return

    cursor.execute("SET LOCAL lock_timeout = '5s'")
    cursor.execute("""
        ALTER TABLE poweremail_mailbox
            ALTER COLUMN pem_to TYPE text,
            ALTER COLUMN pem_cc TYPE text,
            ALTER COLUMN pem_bcc TYPE text
    """)
    cursor.execute("""
        ALTER TABLE poweremail_templates
            ALTER COLUMN def_to TYPE text,
            ALTER COLUMN def_cc TYPE text,
            ALTER COLUMN def_bcc TYPE text
    """)
    cursor.execute("ANALYZE poweremail_mailbox")
    cursor.execute("ANALYZE poweremail_templates")


def down(cursor, installed_version):
    pass


migrate = up
