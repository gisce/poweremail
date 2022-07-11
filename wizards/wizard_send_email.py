# -*- coding: utf-8 -*-

from osv import osv, fields


class WizardSendPoweremail(osv.osv_memory):

    _name = 'wizard.send.email'

    def action_send_email_form(self, cursor, uid, ids, context=None):
        #Cridar send_this_mail
        active_ids = context['active_ids']
        pm_camp_obj = self.pool.get('poweremail.mailbox')
        wizard = self.browse(cursor, uid, ids[0])
        pm_camp_obj.send_this_mail(cursor, uid, active_ids, context=context)
        wizard.write({'state': 'end'})


    _columns = {
        'state': fields.selection([('init', 'Init'), ('end', 'End')], 'State'),
    }

    _defaults = {
        'state': lambda *a: 'init',
    }

WizardSendPoweremail()