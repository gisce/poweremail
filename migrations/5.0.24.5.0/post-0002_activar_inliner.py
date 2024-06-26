# coding=utf-8
import logging
import pooler

from oopgrade.oopgrade import load_data_records


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger("openerp.migration")
    logger.info("Creating pooler")
    pool = pooler.get_pool(cursor.dbname)

    # Afegir columna a poweremail.templates
    logger.info("Updating table table: poweremail.templates")
    pool.get("poweremail.templates")._auto_init(
        cursor, context={"module": "poweremail"}
    )
    logger.info("Table updated succesfully.")

    list_of_records = [
        "poweremail_template_form",
    ]
    load_data_records(
        cursor, "poweremail", "poweremail_template_view.xml",
        list_of_records, mode="update"
    )
    logger.info("poweremail_template_view.xml successfully updated")


def down(cursor, installed_version):
    pass


migrate = up
