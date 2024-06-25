# -*- coding: utf-8 -*-
import logging
from oopgrade.oopgrade import load_data_records
import pooler


def up(cursor, installed_version):
    if not installed_version:
        return

    logger = logging.getLogger('openerp.migration')
    logger.info("Creating pooler")
    pool = pooler.get_pool(cursor.dbname)

    uid = 1
    irmd_o = pool.get('ir.model.data')
    varconf_k = 'poweremail_n_mails_per_batch'
    irmd_id = irmd_o.search(cursor, uid, [('name', '=', varconf_k)])
    if not irmd_id:
        varconf_o = pool.get('res.config')
        varconf_id = varconf_o.search(cursor, uid, [('name', '=', varconf_k)])
        if varconf_id:
            varconf_v = varconf_o.get(cursor, uid, varconf_k)
            varconf_o.unlink(cursor, uid, varconf_id)
        load_data_records(
            cursor, 'poweremail', 'data/res_config.xml', ['poweremail_n_mails_per_batch'], mode='init'
        )
        if varconf_id:
            varconf_o.set(cursor, uid, varconf_k, varconf_v)


def down(cursor, installed_version):
    pass


migrate = up