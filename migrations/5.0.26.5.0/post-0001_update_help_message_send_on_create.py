from tools import config
from oopgrade.oopgrade import MigrationHelper


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    helper = (MigrationHelper(cursor, 'poweremail')
              .init_model(model_name='poweremail.templates'))


def down(cursor, installed_version):
    pass


migrate = up