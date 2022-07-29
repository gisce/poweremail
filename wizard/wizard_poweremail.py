# -*- coding: utf-8 -*-

from osv import osv, fields


class WizardPoweremail(osv.osv_memory):

    _name = 'wizard.change.folder.email'

    def _folder_selection(self, cursor, uid, context=None):
        pwmb_obj = self.pool.get('poweremail.mailbox')
        states = pwmb_obj.fields_get(cursor, uid, context=context)['folder']['selection']
        return states

    def action_change_folder_email_form(self, cursor, uid, ids, context=None):
        active_ids = context['active_ids']
        pm_camp_obj = self.pool.get('poweremail.mailbox')
        wizard = self.browse(cursor, uid, ids[0], context=context)
        pm_camp_obj.write(cursor, uid, active_ids, {'folder': wizard.folder}, context=context)
        wizard.write({'state': 'end'}, context=context)


    _columns = {
        'folder': fields.selection(_folder_selection, 'Folder', required=True),
        'state': fields.selection([('init', 'Init'), ('end', 'End')], 'State'),
    }

    _defaults = {
        'folder': lambda *a: 'drafts',
        'state': lambda *a: 'init',
    }

WizardPoweremail()
