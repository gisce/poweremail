from tools import config
import pooler


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    pool = pooler.get_pool(cursor.dbname)

    pool.get("poweremail.templates")._auto_init(cursor, context={'module': 'poweremail'})


def down(cursor, installed_version):
    pass


migrate = up