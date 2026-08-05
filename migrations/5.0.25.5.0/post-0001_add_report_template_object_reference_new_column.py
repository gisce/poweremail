from tools import config
from oopgrade.oopgrade import MigrationHelper


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    helper = MigrationHelper(
        cursor,
        'poweremail',
    )

    # Add the new field to the model
    helper.init_model(
        model_name='poweremail.templates',
    )

    # Update the form view to include the new field
    helper.update_xml_records(
        xml_path='poweremail_template_view.xml',
        update_record_ids=['poweremail_template_form']
    )


def down(cursor, installed_version):
    pass


migrate = up