from __future__ import absolute_import

import sys
import traceback
from mako.exceptions import html_error_template

from osv import osv, fields
from ..poweremail_template import get_value
from tools.translate import _
import tools
from premailer import transform


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
        'lang': fields.char('Language', size=6, readonly=True),
        'body_text': fields.text('Body', readonly=True),
        'body_html': fields.text('Body', readonly=True),
        'report': fields.char('Report Name', size=100, readonly=True),
        'env': fields.text('Extra scope variables'),
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
        wizard_values = self.read(cr, uid, ids, ['model_ref', 'env'], context=context)

        if context is None:
            context = {}
        if not wizard_values:
            return {}

        wizard_values = wizard_values[0]
        model_name, record_id = wizard_values['model_ref'].split(',')
        record_id = int(record_id)
        template = self.pool.get('poweremail.templates').browse(cr, uid, context['active_id'], context=context)
        # Search translated template
        lang = get_value(cr, uid, record_id, template.lang, template, context)
        ctx = context.copy()

        if lang:
            ctx.update({'lang': lang})
            template = self.pool.get('poweremail.templates').browse(cr, uid, context['active_id'], ctx)

        vals = {'lang': str(lang)}
        mail_fields = ['to', 'cc', 'bcc', 'subject', 'body_text', 'body_html', 'report']
        ctx['raise_exception'] = True
        if wizard_values['env']:
            ctx.update(eval(wizard_values['env']))
        for field in mail_fields:
            try:
                if field == 'report':
                    field_value = template.file_name
                else:
                    field_value = getattr(template, "def_{}".format(field))

                vals[field] = get_value(
                    cr, uid, record_id, field_value, template, ctx
                )
                if field == 'body_text' and template.inline:
                    vals[field] = transform(vals[field])

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

            ctx = context.copy()
            ctx['src_rec_id'] = model_id
            ctx['src_model'] = template.object_name.model
            mailbox_id = template_obj.generate_mail_sync(cursor, uid, template_id, model_id, context=ctx)

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
