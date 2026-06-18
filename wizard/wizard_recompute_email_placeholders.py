# -*- coding: utf-8 -*-
from osv import osv, fields
from tools.translate import _
from tools.sql_utils import readonly


class WizardRecomputeEmailPlaceholders(osv.osv_memory):
    _name = 'wizard.recompute.email.placeholders'

    def _parse_reference(self, reference):
        if not reference or ',' not in reference:
            return False, False
        model, res_id = reference.rsplit(',', 1)
        try:
            res_id = int(res_id)
        except (TypeError, ValueError):
            return False, False
        return model, res_id

    def _get_fields_to_recompute(self):
        return [
            'pem_from',
            'pem_to',
            'pem_cc',
            'pem_bcc',
            'pem_subject',
            'pem_body_text',
            'pem_body_html',
            'pem_account_id',
            'mail_type',
            'priority',
        ]

    def _validate_mail(self, cursor, uid, mail, context=None):
        if mail.folder != 'error':
            raise osv.except_osv(
                _('Error'),
                _('Only emails in error folder can be recomputed.')
            )
        if not mail.template_id:
            raise osv.except_osv(
                _('Error'),
                _('Email %s has no template associated.') % mail.id
            )
        model, res_id = self._parse_reference(mail.reference)
        if not model or not res_id:
            raise osv.except_osv(
                _('Error'),
                _('Email %s has no valid source document reference.') % mail.id
            )
        if model != mail.template_id.object_name.model:
            raise osv.except_osv(
                _('Error'),
                _('Email %s source document does not match its template model.') % mail.id
            )
        model_obj = self.pool.get(model)
        if not model_obj or not model_obj.search(cursor, uid, [('id', '=', res_id)], context=context):
            raise osv.except_osv(
                _('Error'),
                _('Email %s source document no longer exists.') % mail.id
            )
        return res_id

    def action_recompute(self, cursor, uid, ids, context=None):
        if context is None:
            context = {}
        mailbox_obj = self.pool.get('poweremail.mailbox')
        template_obj = self.pool.get('poweremail.templates')
        active_ids = context.get('active_ids') or []
        fields_to_recompute = self._get_fields_to_recompute()

        for mail in mailbox_obj.browse(cursor, uid, active_ids, context=context):
            record_id = self._validate_mail(cursor, uid, mail, context=context)
            values = template_obj.get_mailbox_values(
                cursor, uid, mail.template_id, record_id, context=context
            )
            values = dict(
                (field_name, values[field_name])
                for field_name in fields_to_recompute
            )
            mailbox_obj.write(cursor, uid, [mail.id], values, context=context)
            mailbox_obj.historise(
                cursor, uid, [mail.id],
                _('Template placeholders recomputed'),
                context=context
            )

        self.write(cursor, uid, ids, {
            'wiz_state': 'end',
            'updated_count': len(active_ids),
        }, context=context)
        return True

    _columns = {
        'wiz_state': fields.selection([
            ('init', 'Init'),
            ('end', 'End'),
        ], 'State'),
        'updated_count': fields.integer('Updated emails', readonly=True),
    }

    _defaults = {
        'wiz_state': lambda *a: 'init',
        'updated_count': lambda *a: 0,
    }


WizardRecomputeEmailPlaceholders()
