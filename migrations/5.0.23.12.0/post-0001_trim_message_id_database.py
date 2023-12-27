# coding=utf-8
import logging
from tqdm import tqdm


logger = logging.getLogger('openerp.migration.' + __name__)


def up(cursor, installed_version):
    if not installed_version:
        return
    cursor.execute("SELECT count(id) FROM poweremail_mailbox where pem_message_id ilike ' %'")
    total_to_migrate = cursor.fetchone()[0]
    t = tqdm(total=total_to_migrate, desc='Migrating messages')
    remaining_to_migrate = total_to_migrate
    while remaining_to_migrate:
        cursor.execute(
            "UPDATE poweremail_mailbox SET pem_message_id = trim(pem_message_id) WHERE id in ("
            "SELECT id from poweremail_mailbox WHERE pem_message_id ilike ' %' LIMIT 1000"
            ")"
        )
        cursor.execute("SELECT count(id) FROM poweremail_mailbox where pem_message_id ilike ' %'")
        remaining_to_migrate = cursor.fetchone()[0]
        t.update(1000)
        t.display()
    t.close()


def down(cursor, installed_version):
    pass


migrate = up
