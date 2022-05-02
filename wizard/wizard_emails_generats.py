# -*- coding: utf-8 -*-
from osv import osv, fields


class WizardEmailsGeneratsModel(osv.osv_memory):
    _name = 'wizard.emails.generats.model'

    def _get_references(self, cr, uid, context=None):
        dataobj = self.pool.get('ir.model')
        ids = dataobj.search(cr, uid, [])
        res = dataobj.read(cr, uid, ids, ['model', 'name'], context)
        return [(r['model'], r['name']) for r in res]

    def get_reference_items(self, cursor, uid, reference, context=None):
        references = set()
        references.add(reference)
        return references

    def _get_default_reference(self, cursor, uid, context=None):
        if context is None:
            context = {}
        model_name = context.get('model_name')
        res = ''
        if model_name:
            res = '{},{}'.format(model_name, context['active_ids'][0])
        return res

    def list_all_emails(self, cursor, uid, ids, context=None):
        if context is None:
            context = {}
        wizard = self.browse(cursor, uid, ids[0], context=context)
        reference = wizard['reference']
        references = self.get_reference_items(cursor, uid, reference, context=context)

        return {
            'domain': [('reference', 'in', references)],
            'name': 'Correos relacionados',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'poweremail.mailbox',
            'type': 'ir.actions.act_window',
            'view_id': False
        }

    _columns = {
        'reference': fields.reference('Model', selection=_get_references, required=True, size=128),
    }

    _defaults = {
        'reference': _get_default_reference,
    }

WizardEmailsGeneratsModel()
