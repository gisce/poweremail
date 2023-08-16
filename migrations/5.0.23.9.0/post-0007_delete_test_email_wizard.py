# -*- coding: utf-8 -*-
import logging
import pooler


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')
    logger.info('Checking if script needs to be run...')
    irmd_names_to_delete = [
        'access_wizard_generate_test_email_r',
        'access_wizard_generate_test_email_w',
        'access_wizard_generate_test_email_u',
        'model_wizard_generate_test_email',
        'field_wizard_generate_test_email_model_ref',
        'field_wizard_generate_test_email_state',
        'action_wizard_generate_email_form',
        'value_wizard_generate_email_form',
        'view_wizard_generate_email_form'
    ]
    q_check_model_is_deleted = """
        SELECT * FROM ir_model_data WHERE name IN %s
    """
    cursor.execute(q_check_model_is_deleted, (tuple(irmd_names_to_delete),))
    res = cursor.fetchall()
    if res:
        logger.info('Script needs to be run.')
        pool = pooler.get_pool(cursor.dbname)
        irmd_o = pool.get('ir.model.data')

        # DELETE PERMISSIONS
        irmd_names_to_delete = [
            'access_wizard_generate_test_email_r',
            'access_wizard_generate_test_email_w',
            'access_wizard_generate_test_email_u',
        ]
        irmd_ids = irmd_o.search(
            cursor, 1, [('name', 'in', irmd_names_to_delete)]
        )
        irmd_vs = irmd_o.read(cursor, 1, irmd_ids, ['id', 'res_id', 'model', 'name'])
        for irmd_v in irmd_vs:
            logger.info('Deleting {}...'.format(irmd_v['name']))
            pool.get(irmd_v['model']).unlink(cursor, 1, [int(irmd_v['res_id'])])
            q_delete_irmd = """
                DELETE FROM ir_model_data WHERE id = %s
            """
            cursor.execute(q_delete_irmd, (irmd_v['id'], ))

        # DELETE MODEL
        irmd_names_to_delete = [
            'model_wizard_generate_test_email'
        ]
        irmd_ids = irmd_o.search(
            cursor, 1, [('name', 'in', irmd_names_to_delete)]
        )
        irmd_vs = irmd_o.read(cursor, 1, irmd_ids, ['id', 'res_id', 'model', 'name'])
        for irmd_v in irmd_vs:
            logger.info('Deleting {}...'.format(irmd_v['name']))
            q_delete_irmd = """
                DELETE FROM ir_model_data WHERE id = %s
            """
            cursor.execute(q_delete_irmd, (irmd_v['id'], ))
            q_delete_model = """
                DELETE FROM ir_model WHERE name = 'wizard.generate.test.email'
            """
            cursor.execute(q_delete_model)

        # DELETE FIELDS
        # FIELDS are deleted on cascade BUT the ir_model_data registry still
        # exists
        irmd_names_to_delete = [
            'field_wizard_generate_test_email_model_ref',
            'field_wizard_generate_test_email_state'
        ]
        irmd_ids = irmd_o.search(
            cursor, 1, [('name', 'in', irmd_names_to_delete)]
        )
        irmd_vs = irmd_o.read(cursor, 1, irmd_ids, ['id', 'res_id', 'model', 'name'])
        for irmd_v in irmd_vs:
            logger.info('Deleting {}...'.format(irmd_v['name']))
            q_delete_irmd = """
                DELETE FROM ir_model_data WHERE id = %s
            """
            cursor.execute(q_delete_irmd, (irmd_v['id'], ))

        # DELETE VIEWS & RELATED STUFF
        irmd_names_to_delete = [
            'action_wizard_generate_email_form',
            'value_wizard_generate_email_form',
            'view_wizard_generate_email_form'
        ]
        irmd_ids = irmd_o.search(
            cursor, 1, [('name', 'in', irmd_names_to_delete)]
        )
        irmd_vs = irmd_o.read(cursor, 1, irmd_ids, ['id', 'res_id', 'model', 'name'])
        for irmd_v in irmd_vs:
            logger.info('Deleting {}...'.format(irmd_v['name']))
            pool.get(irmd_v['model']).unlink(cursor, 1, [int(irmd_v['res_id'])])
            q_delete_irmd = """
                DELETE FROM ir_model_data WHERE id = %s
            """
            cursor.execute(q_delete_irmd, (irmd_v['id'], ))
    else:
        logger.info('Script not needed to be run.')


def down(cursor, installed_version):
    pass


migrate = up
