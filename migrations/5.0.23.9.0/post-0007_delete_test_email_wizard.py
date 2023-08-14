# -*- coding: utf-8 -*-
import logging
import pooler


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')
    q_check_model_is_deleted = """
        SELECT * FROM ir_model_data WHERE name = 'model_wizard_generate_test_email'
    """
    cursor.execute(q_check_model_is_deleted)
    res = cursor.fetchall()
    if res:
        logger.info('Deleting models related to the wizard_generate_test_email...')
        pool = pooler.get_pool(cursor.dbname)
        irmd_o = pool.get('ir.model.data')

        irmd_names_to_delete = [
            'access_wizard_generate_test_email_r',
            'access_wizard_generate_test_email_w',
            'access_wizard_generate_test_email_u',
            'model_wizard_generate_test_email'
        ]
        irmd_ids = irmd_o.search(
            cursor, 1, [('name', 'in', irmd_names_to_delete)]
        )
        irmd_vs = irmd_o.read(cursor, 1, irmd_ids, ['id', 'res_id', 'model'])
        for irmd_v in irmd_vs:
            pool.get(irmd_v['model']).unlink(cursor, 1, [int(irmd_v['res_id'])])
            q_delete_irmd = """
                DELETE FROM ir_model_data WHERE id = %s
            """
            cursor.execute(q_delete_irmd, (irmd_v['id'], ))


def down(cursor, installed_version):
    pass


migrate = up
