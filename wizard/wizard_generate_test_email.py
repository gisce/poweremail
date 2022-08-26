# -*- coding: utf-8 -*-

from osv import osv, fields
from tools.translate import _
import tools


class WizardGenerateTestEmail(osv.osv_memory):

    _name = 'wizard.generate.test.email'

    def action_generate_static_mail(self, cursor, uid, ids, context=None):
        if context is None:
            context = {}
            
        template_obj = self.pool.get('poweremail.templates')
        mailbox_obj = self.pool.get('poweremail.mailbox')

        wizard = self.browse(cursor, uid, ids[0], context=context)
        template_ids = context['active_ids']

        if not isinstance(template_ids, (list, tuple)):
            template_ids = [template_ids]

        mailbox_ids = []
        for template_id in template_ids:
            template = template_obj.browse(cursor, uid, template_id, context=context)
            if not template:
                raise Exception("The requested template could not be loaded")

            from_account = template_obj.get_from_account_id_from_template(
                cursor, uid, template.id, context=context
            )

            mail_vals = {
                'pem_from': tools.ustr(from_account['name']) + \
                            "<" + tools.ustr(from_account['email_id']) + ">",
                'pem_to': template.def_to,
                'pem_cc': False,
                'pem_bcc': False,
                'pem_subject': template.name,
                'pem_body_text': template.def_body_text,
                'pem_account_id': from_account['id'],
                'priority': '1',
                'state': 'na',
                'mail_type': 'multipart/alternative'
            }

            mailbox_id = mailbox_obj.create(cursor, uid, mail_vals)
            mailbox_ids.append(mailbox_id)

        wizard.write({'state': 'end'}, context=context)

        return {
            'domain': "[('id','in', %s)]" % str(mailbox_ids),
            'name': _('Generated Email'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'poweremail.mailbox',
            'type': 'ir.actions.act_window'
        }
    
    _columns = {
        'state': fields.selection([('init', 'Init'), ('end', 'End')], 'State'),
    }

    _defaults = {
        'state': lambda *a: 'init',
    }



WizardGenerateTestEmail()
