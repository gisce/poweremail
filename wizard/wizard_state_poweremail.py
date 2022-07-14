# -*- coding: utf-8 -*-

from osv import osv, fields


class WizardPoweremail(osv.osv_memory):

    _name = 'wizard.change.state.email'

    def _state_selection(self, cursor, uid, context=None):
        return [
            ('read', 'Read'),
            ('unread', 'Un-Read'),
            ('na', 'Not Applicable'),
            ('sending', 'Sending'),
        ]

    def action_change_state_email_form(self, cursor, uid, ids, context=None):
        active_ids = context['active_ids']
        pm_camp_obj = self.pool.get('poweremail.mailbox')
        wizard = self.browse(cursor, uid, ids[0])
        pm_camp_obj.write(cursor, uid, active_ids, {'state': wizard.estat}, context=context)
        wizard.write({'wiz_state': 'end'})


    _columns = {
        'estat': fields.selection(_state_selection, 'Estat', required=True),
        'wiz_state': fields.selection([('init', 'Init'), ('end', 'End')], 'State'),
    }

    _defaults = {
        'estat': lambda *a: 'read',
        'wiz_state': lambda *a: 'init',
    }

WizardPoweremail()