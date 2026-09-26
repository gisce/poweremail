# -*- coding: utf-8 -*-
from oopgrade.oopgrade import column_exists, drop_columns, table_exists
from tools import config


SERVER_ACTION_VIEW_XMLIDS = (
    'view_server_action_form_poweremail_1',
    'view_server_action_form_poweremail_2',
)

POWEREMAIL_TEMPLATE_FIELDS = (
    'auto_email',
    'attached_wkf',
    'attached_activity',
    'server_action',
)


def delete_model_data_for_records(cursor, model, table, record_ids):
    if not record_ids:
        return
    cursor.execute("""
        DELETE FROM ir_model_data
        WHERE model = %s
            AND res_id = ANY(%s)
    """, (model, record_ids))
    cursor.execute("""
        DELETE FROM {table}
        WHERE id = ANY(%s)
    """.format(table=table), (record_ids,))


def remove_xmlid_records(cursor, model, table, names):
    cursor.execute("""
        SELECT res_id
        FROM ir_model_data
        WHERE module = 'poweremail'
            AND name = ANY(%s)
            AND model = %s
    """, (list(names), model))
    record_ids = [row[0] for row in cursor.fetchall()]
    delete_model_data_for_records(cursor, model, table, record_ids)
    cursor.execute("""
        DELETE FROM ir_model_data
        WHERE module = 'poweremail'
            AND name = ANY(%s)
            AND model = %s
    """, (list(names), model))


def remove_field_metadata(cursor, model_name, field_names):
    cursor.execute("""
        SELECT id
        FROM ir_model_fields
        WHERE model = %s
            AND name = ANY(%s)
    """, (model_name, list(field_names)))
    field_ids = [row[0] for row in cursor.fetchall()]
    delete_model_data_for_records(
        cursor, 'ir.model.fields', 'ir_model_fields', field_ids
    )


def remove_poweremail_generated_actions(cursor):
    if not table_exists(cursor, 'ir_act_server'):
        return

    cursor.execute("""
        CREATE TEMP TABLE tmp_poweremail_server_action_ids (
            id INTEGER
        ) ON COMMIT DROP
    """)

    if column_exists(cursor, 'poweremail_templates', 'server_action'):
        cursor.execute("""
            INSERT INTO tmp_poweremail_server_action_ids (id)
            SELECT DISTINCT server_action
            FROM poweremail_templates
            WHERE server_action IS NOT NULL
        """)

    if column_exists(cursor, 'ir_act_server', 'poweremail_template'):
        cursor.execute("""
            INSERT INTO tmp_poweremail_server_action_ids (id)
            SELECT DISTINCT id
            FROM ir_act_server
            WHERE poweremail_template IS NOT NULL
        """)

    if (
        column_exists(cursor, 'workflow_activity', 'action_id')
        and column_exists(cursor, 'poweremail_templates', 'server_action')
    ):
        cursor.execute("""
            UPDATE workflow_activity
            SET action_id = NULL
            WHERE action_id IN (
                SELECT id
                FROM tmp_poweremail_server_action_ids
            )
        """)

    if column_exists(cursor, 'poweremail_templates', 'server_action'):
        cursor.execute("""
            UPDATE poweremail_templates
            SET server_action = NULL
            WHERE server_action IS NOT NULL
        """)

    cursor.execute("""
        DELETE FROM ir_act_server
        WHERE id IN (
            SELECT id
            FROM tmp_poweremail_server_action_ids
        )
    """)

    drop_columns(cursor, [('ir_act_server', 'poweremail_template')])


def up(cursor, installed_version):
    if not installed_version or config.updating_all:
        return

    remove_xmlid_records(
        cursor, 'ir.ui.view', 'ir_ui_view', SERVER_ACTION_VIEW_XMLIDS
    )
    remove_poweremail_generated_actions(cursor)
    drop_columns(
        cursor,
        [('poweremail_templates', field) for field in POWEREMAIL_TEMPLATE_FIELDS]
    )
    remove_field_metadata(cursor, 'poweremail.templates', POWEREMAIL_TEMPLATE_FIELDS)
    remove_field_metadata(cursor, 'ir.actions.server', ('poweremail_template',))


def down(cursor, installed_version):
    pass


migrate = up
