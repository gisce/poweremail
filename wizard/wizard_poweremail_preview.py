from __future__ import absolute_import

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
        'state': fields.selection([('init', 'Init'), ('end', 'End')], 'State'),
    }

    _defaults = {
        'state': lambda *a: 'init',
    }

    def render_body_text(self, cursor, uid, template, record_id, context=None):
        return get_value(cursor, uid, record_id, template.def_body_text, template, context)

    def on_change_ref(self, cr, uid, ids, model_ref, context=None):
        if context is None:
            context = {}
        if not model_ref:
            return {}
        template_o = self.pool.get('poweremail.templates')
        vals = {}
        model_name, record_id = model_ref.split(',')
        record_id = int(record_id)
        res = {}
        if record_id:
            template_id = context.get('active_id')
            if not template_id:
                raise osv.except_osv('Error !', 'active_id missing from context')

            mailbox_values = template_o.get_mailbox_values(
                cr, uid, template_id, record_id, context=context
            )

            vals['to'] = mailbox_values['pem_to']
            vals['cc'] = mailbox_values['pem_cc']
            vals['bcc'] = mailbox_values['pem_bcc']
            vals['subject'] = mailbox_values['pem_subject']
            vals['body_text'] = mailbox_values['pem_body_text']
            # vals['report'] = get_value(cr, uid, record_id, template.file_name, template, context)
            res = {'value': vals}

        return res

    def action_generate_static_mail(self, cursor, uid, ids, context=None):
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
        model_ref = wizard.model_ref.split(',')
        model_name = model_ref[0]
        model_id = int(model_ref[1])

        if not isinstance(template_ids, (list, tuple)):
            template_ids = [template_ids]

        mailbox_ids = []
        for template_id in template_ids:
            template = template_obj.browse(cursor, uid, template_id, context=context)
            mailbox_id = template_obj._generate_mailbox_item_from_template(
                cursor, uid, template, model_id, context=context
            )
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
