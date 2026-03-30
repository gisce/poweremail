from tools import config
from oopgrade.oopgrade import MigrationHelper
from tools.translate import trans_load


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    helper = MigrationHelper(cursor, 'poweremail')
    helper.init_model(model_name='poweremail.templates',)

    xml_path = 'poweremail_template_view.xml'
    record_ids = [
        'poweremail_template_form',
        'poweremail_template_tree',
    ]
    helper.update_xml_records(xml_path=xml_path, update_record_ids=record_ids)
    trans_load(cursor, '{}/poweremail/i18n/ca_ES.po'.format(config['addons_path']), 'ca_ES')
    trans_load(cursor, '{}/poweremail/i18n/es_ES.po'.format(config['addons_path']), 'es_ES')


def down(cursor, installed_version):
    pass


migrate = up
