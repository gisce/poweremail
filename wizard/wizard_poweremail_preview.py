from __future__ import absolute_import

import sys
import traceback
from mako.exceptions import html_error_template

from osv import osv, fields
from ..poweremail_template import get_value
from tools.translate import _
import tools


class poweremail_preview(osv.osv_memory):
    _name = "poweremail.preview"
    _description = "Power Email Template Preview"

    def _ref_models(self, cursor, uid, context=None):
        template_obj = self.pool.get('poweremail.templates')

        if not context:
            context = {}

        template_ids = context.get('active_ids', [])

        if not isinstance(template_ids, (list, tuple)):
            template_ids = [template_ids]
        res = []
        for template in template_obj.browse(cursor, uid, template_ids, context=context):
            template_model = template.object_name.model
            template_name = template.object_name.name
            res.append((template_model, template_name))

        return res

    def get_save_to_draft(self, cursor, uid, context=None):
        template_obj = self.pool.get('poweremail.templates')

        if not context:
            context = {}
        template_ids = context.get('active_ids', [])

        res = template_obj.read(cursor, uid, template_ids, ['save_to_drafts'])[0]['save_to_drafts']
        return res

    _columns = {
        'model_ref': fields.reference(
            "Template reference", selection=_ref_models,
            size=64, required=True
        ),
        'to': fields.char('To', size=250, readonly=True),
        'cc': fields.char('CC', size=250, readonly=True),
        'bcc': fields.char('BCC', size=250, readonly=True),
        'subject': fields.char('Subject', size=200, readonly=True),
        'body_text': fields.text('Body', readonly=True),
        'body_html': fields.text('Body', readonly=True),
        'report': fields.char('Report Name', size=100, readonly=True),
        'state': fields.selection([('init', 'Init'), ('end', 'End'), ('error', 'Error')], 'State'),
        'save_to_drafts_prev': fields.boolean('Save to Drafts',
                                         help="When automatically sending emails generated from"
                                              " this template, save them into the Drafts folder rather"
                                              " than sending them immediately."),
    }

    _defaults = {
        'state': lambda *a: 'init',
        'save_to_drafts_prev': get_save_to_draft
    }

    def action_generate_static_mail(self, cr, uid, ids, context=None):
        wizard_values = self.read(cr, uid, ids, ['model_ref'], context=context)

        if context is None:
            context = {}
        if not wizard_values:
            return {}

        vals = {}
        model_name, record_id = wizard_values[0]['model_ref'].split(',')
        record_id = int(record_id)
        template = self.pool.get('poweremail.templates').browse(cr, uid, context['active_id'], context=context)
        # Search translated template
        lang = get_value(cr, uid, record_id, template.lang, template, context)
        ctx = context.copy()

        if lang:
            ctx.update({'lang': lang})
            template = self.pool.get('poweremail.templates').browse(cr, uid, context['active_id'], ctx)

        mail_fields = ['to', 'cc', 'bcc', 'subject', 'body_text', 'body_html', 'report']
        ctx.update({'raise_exception': True})
        for field in mail_fields:
            try:
                if field == 'report':
                    field_value = template.file_name
                else:
                    field_value = getattr(template, "def_{}".format(field))
                vals[field] = get_value(cr, uid, record_id, field_value, template, ctx)
            except Exception as e:
                if field == 'body_text':
                    vals[field] = html_error_template().render()
                else:
                    tb = traceback.format_tb(sys.exc_info()[2])
                    vals[field] = '{}\n{}'.format(e.message, ''.join(tb))
                vals['state'] = 'error'

        self.write(cr, uid, ids, vals, context=context)
        return True


    def action_send_static_mail(self, cursor, uid, ids, context=None):
        if context is None:
            context = {}

        template_obj = self.pool.get('poweremail.templates')
        mailbox_obj = self.pool.get('poweremail.mailbox')

        wizard = self.browse(cursor, uid, ids[0], context=context)
        template_ids = context['active_ids']

        if not wizard.model_ref:
            raise osv.except_osv(
                _('Error'),
                _('No model reference defined')
            )
        model_name, model_id = wizard.model_ref.split(',')
        model_id = int(model_id)

        if not isinstance(template_ids, (list, tuple)):
            template_ids = [template_ids]

        mailbox_ids = []
        for template_id in template_ids:
            template = template_obj.browse(cursor, uid, template_id,
                                           context=context)
            if not template:
                raise Exception("The requested template could not be loaded")

            from_account = template_obj.get_from_account_id_from_template(
                cursor, uid, template.id, context=context
            )

            # Evaluates an expression and returns its value
            # recid: ID of the target record under evaluation
            # message: The expression to be evaluated
            # template: BrowseRecord object of the current template
            # return: Computed message (unicode) or u""

            pem_too = get_value(
                cursor, uid, model_id, message=template.def_to,
                template=template, context=context
            )
            def_subject = get_value(
                cursor, uid, model_id, message=template.def_subject,
                template=template, context=context
            )

            body_text = get_value(
                cursor, uid, model_id, message=template.def_body_text,
                template=template, context=context
            )

            mail_vals = {
                'pem_from': tools.ustr(from_account['name']) + \
                            "<" + tools.ustr(from_account['email_id']) + ">",
                'pem_to': pem_too,
                'pem_cc': False,
                'pem_bcc': False,
                'pem_subject': def_subject,
                'pem_body_text': body_text,
                'pem_account_id': from_account['id'],
                'priority': '1',
                'state': 'na',
                'mail_type': 'multipart/alternative',
                'template_id': template_id
            }

            mailbox_id = mailbox_obj.create(cursor, uid, mail_vals)
            if wizard.save_to_drafts_prev:
                mailbox_obj.write(cursor, uid, mailbox_id, {'folder': 'drafts'}, context=context)

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


poweremail_preview()
