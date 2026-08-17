#########################################################################
#Power Email is a module for Open ERP which enables it to send mails    #
#Core settings are stored here                                          #
#########################################################################
#   #####     #   #        # ####  ###     ###  #   #   ##  ###   #     #
#   #   #   #  #   #      #  #     #  #    #    # # #  #  #  #    #     #
#   ####    #   #   #    #   ###   ###     ###  #   #  #  #  #    #     #
#   #        # #    # # #    #     # #     #    #   #  ####  #    #     #
#   #         #     #  #     ####  #  #    ###  #   #  #  # ###   ####  #
# Copyright (C) 2009  Sharoon Thomas                                    #
#                                                                       #
#This program is free software: you can redistribute it and/or modify   #
#it under the terms of the GNU General Public License as published by   #
#the Free Software Foundation, either version 3 of the License, or      #
# any later version.                                                    #
#                                                                       #
#This program is distributed in the hope that it will be useful,        #
#but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
#GNU General Public License for more details.                           #
#                                                                       #
#You should have received a copy of the GNU General Public License      #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################
from __future__ import absolute_import
from osv import osv, fields
import netsvc
from tools.translate import _
from .poweremail_template import get_value
from .poweremail_core import filter_send_emails, _priority_selection
from premailer import transform
from tools.safe_eval import safe_eval


class poweremail_send_wizard(osv.osv_memory):
    _name = 'poweremail.send.wizard'
    _description = 'This is the wizard for sending mail'
    _rec_name = "subject"

    def _get_accounts(self, cr, uid, context=None):
        if context is None:
            context = {}
        users_obj = self.pool.get('res.users')
        accounts_obj = self.pool.get('poweremail.core_accounts')
        template = self._get_template(cr, uid, context)
        if not template:
            return []
        user_company = users_obj.read(
            cr, uid, uid, ['company_id'])['company_id'][0]
        company_users = users_obj.search(
            cr, uid, [
                ('company_id', '=', user_company)
            ]
        )
        logger = netsvc.Logger()

        if template.enforce_from_account:
            return [(template.enforce_from_account.id, '%s (%s)' % (template.enforce_from_account.name, template.enforce_from_account.email_id))]
        elif (context.get('from', False) and
              isinstance(context.get('from'), int)):
            # If account provided from context, check availability
            account = accounts_obj.browse(cr, uid, context.get('from'), context)
            if ((account.user.id == uid or (
                account.company == 'yes' and
                account.user.id in company_users
            )) and account.state == 'approved'):
                return [(
                    account.id, "{} ({})".format(account.name, account.email_id)
                )]
        else:
            # Check for user's accounts available
            search_params = [
                ('company', '=', 'no'),
                ('user', '=', uid)
            ]
            accounts_id = accounts_obj.search(
                cr, uid, search_params, context=context)
            search_params = [
                ('company', '=', 'yes'),
                ('user', 'in', company_users)
            ]
            company_accounts_ids = accounts_obj.search(
                cr, uid, search_params, context=context)
            if accounts_id:
                return [
                    (r.id, r.name + " (" + r.email_id + ")")
                    for r in accounts_obj.browse(cr, uid, accounts_id, context)
                ]
            elif company_accounts_ids:
                return [
                    (r.id, r.name + " (" + r.email_id + ")")
                    for r in accounts_obj.browse(
                        cr, uid, company_accounts_ids, context)
                ]
            else:
                logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("No personal email accounts are configured for you. \nEither ask admin to enforce an account for this template or get yourself a personal power email account."))
                raise osv.except_osv(_("Power Email"),_("No personal email accounts are configured for you. \nEither ask admin to enforce an account for this template or get yourself a personal power email account."))

    def get_value(self, cursor, user, template, message, context=None, id=None):
        """Gets the value of the message parsed with the content of object id (or the first 'src_rec_ids' if id is not given)"""
        if not message:
            return ''
        if not id:
            id = context['src_rec_ids'][0]
        return get_value(cursor, user, id, message, template, context)

    def _get_template(self, cr, uid, context=None):
        if context is None:
            context = {}
        if not 'template' in context and not 'template_id' in context:
            return None
        template_obj = self.pool.get('poweremail.templates')
        if 'template_id' in context.keys():
            template_ids = template_obj.search(cr, uid, [('id','=',context['template_id'])], context=context)
        elif 'template' in context.keys():
            # Old versions of poweremail used the name of the template. This caused
            # problems when the user changed the name of the template, but we keep the code
            # for compatibility with those versions.
            template_ids = template_obj.search(cr, uid, [('name','=',context['template'])], context=context)
        if not template_ids:
            return None

        template = template_obj.browse(cr, uid, template_ids[0], context)

        lang = context.get('src_rec_ids') and self.get_value(
            cr, uid, template, template.lang, context)
        if lang:
            # Use translated template if necessary
            ctx = context.copy()
            ctx['lang'] = lang
            template = template_obj.browse(cr, uid, template.id, ctx)
        return template

    def _get_rel_model(self, cr, uid, context=None):
        if context is None:
            context = {}
        result = False
        model_name = context.get('src_model')
        if not model_name and context.get('template_id'):
            template = self.pool.get('poweremail.templates').simple_browse(
                cr, uid, int(context['template_id']), context=context)
            model_name = template.object_name.model
        if model_name:
            result = self.pool.get('ir.model').search(
                cr, uid, [('model', '=', model_name)], context=context)[0]
        return result

    def _get_preview_models(self, cr, uid, context=None):
        result = []
        template = self._get_template(cr, uid, context)
        if template:
            result = [(template.object_name.model, template.object_name.name)]
        return result

    def _get_source_context(self, cr, uid, wizard, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        if not ctx.get('src_rec_ids'):
            model_name, record_id = wizard.model_ref.split(',', 1)
            record_id = int(record_id)
            ctx['src_model'] = model_name
            ctx['src_rec_ids'] = [record_id]
            ctx['active_id'] = record_id
        return ctx

    def _get_template_value(self, cr, uid, field, context=None):
        template = self._get_template(cr, uid, context)
        if not template:
            return False

        template_values = {
            'def_to': template.def_to,
            'def_cc': template.def_cc,
            'def_bcc': template.def_bcc,
            'def_subject': template.def_subject,
            'def_body_text': template.def_body_text,
            'def_body_html': template.def_body_html,
            'file_name': template.file_name,
            'single_email': template.single_email,
            'def_priority': template.def_priority,
        }
        value = template_values[field]
        if not context.get('src_rec_ids') or len(context['src_rec_ids']) > 1:
            return value

        value = self.get_value(cr, uid, template, value, context)
        if template.inline and field == 'def_body_text':
            value = transform(value)
        return value

    def _get_preview_values(self, cr, uid, context=None):
        template = self._get_template(cr, uid, context)
        return {
            'to': filter_send_emails(
                self._get_template_value(cr, uid, 'def_to', context)),
            'cc': filter_send_emails(
                self._get_template_value(cr, uid, 'def_cc', context)),
            'bcc': filter_send_emails(
                self._get_template_value(cr, uid, 'def_bcc', context)),
            'subject': self._get_template_value(
                cr, uid, 'def_subject', context),
            'body_text': self._get_template_value(
                cr, uid, 'def_body_text', context),
            'body_html': self._get_template_value(
                cr, uid, 'def_body_html', context),
            'report': self._get_template_value(
                cr, uid, 'file_name', context),
            'signature': template.use_sign,
            'priority': self._get_template_value(
                cr, uid, 'def_priority', context),
        }

    _columns = {
        'state':fields.selection([
                        ('single','Simple Mail Wizard Step 1'),
                        ('multi','Multiple Mail Wizard Step 1'),
                        ('send_type','Send Type'),
                        ('done','Wizard Complete')
                                  ],'Status',readonly=True),
        'ref_template':fields.many2one('poweremail.templates','Template',readonly=True),
        'model_ref': fields.reference('Template reference', selection=_get_preview_models, size=64, required=True),
        'rel_model':fields.many2one('ir.model','Model',readonly=True),
        'from':fields.selection(_get_accounts,'From Account',select=True),
        'to':fields.char('To',size=250,required=True),
        'cc':fields.char('CC',size=250,),
        'bcc':fields.char('BCC',size=250,),
        'subject':fields.char('Subject',size=200),
        'body_preview':fields.text('Body Preview', readonly=True),
        'body_text':fields.text('Body',),
        'body_html':fields.text('Body',),
        'report':fields.char('Report File Name',size=100,),
        'signature':fields.boolean('Attach my signature to mail'),
        #'filename':fields.text('File Name'),
        'requested':fields.integer('No of requested Mails',readonly=True),
        'generated':fields.integer('No of generated Mails',readonly=True),
        'full_success':fields.boolean('Complete Success',readonly=True),
        'attachment_ids': fields.many2many('ir.attachment','send_wizard_attachment_rel', 'wizard_id', 'attachment_id', 'Attachments'),
        'single_email': fields.boolean("Single email", help="Check it if you want to send a single email for several records (the optional attachment will be generated as a single file for all these records). If you don't check it, an email with its optional attachment will be send for each record."),
        'priority': fields.selection(_priority_selection, 'Priority'),
        'env': fields.text('Extra scope variables'),
    }

    _defaults = {
        'state': lambda self, cr, uid, ctx:
            len(ctx.get('src_rec_ids', [])) > 1 and 'send_type' or 'single',
        'rel_model': _get_rel_model,
        'model_ref': lambda self, cr, uid, ctx: (
            ctx.get('src_model') and len(ctx.get('src_rec_ids', [])) == 1
            and '%s,%s' % (ctx['src_model'], ctx['src_rec_ids'][0]) or False),
        'to': lambda self,cr,uid,ctx: filter_send_emails(self._get_template_value(cr, uid, 'def_to', ctx)),
        'cc': lambda self,cr,uid,ctx: filter_send_emails(self._get_template_value(cr, uid, 'def_cc', ctx)),
        'bcc': lambda self,cr,uid,ctx: filter_send_emails(self._get_template_value(cr, uid, 'def_bcc', ctx)),
        'subject':lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'def_subject', ctx),
        'body_text':lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'def_body_text', ctx),
        'body_html':lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'def_body_html', ctx),
        'report': lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'file_name', ctx),
        'signature': lambda self,cr,uid,ctx: self._get_template(cr, uid, ctx).use_sign,
        'ref_template':lambda self,cr,uid,ctx: self._get_template(cr, uid, ctx).id,
        'requested': lambda self, cr, uid, ctx: len(ctx.get('src_rec_ids', [])),
        'full_success': lambda *a: False,
        'single_email':lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'single_email', ctx),
        'priority': lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'def_priority', ctx),
    }

    def fields_get(self, cr, uid, fields=None, context=None, read_access=True):
        if context is None:
            context = {}
        result = super(poweremail_send_wizard, self).fields_get(cr, uid, fields, context, read_access)
        if 'attachment_ids' in result and 'src_model' in context:
            result['attachment_ids']['domain'] = [('res_model','=',context['src_model']),('res_id','=',context['active_id'])]
        return result

    def preview_mail(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        wizard = self.simple_browse(cr, uid, ids[0], context=context)
        ctx = self._get_source_context(cr, uid, wizard, context)
        ctx.update(safe_eval(wizard.env or '{}'))
        ctx['src_rec_ids'] = ctx['src_rec_ids'][:1]
        values = self._get_preview_values(cr, uid, ctx)
        values['body_preview'] = values['body_text']
        return self.write(cr, uid, ids, values, context=context)

    def compute_second_step(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        wizard = self.browse(cr, uid, ids[0], context)
        if not wizard.single_email:
            return self.write(cr, uid, ids, {'state': 'multi'}, context)
        # We send a single email for several records. We compute the values from the first record
        ctx = context.copy()
        ctx.update(safe_eval(wizard.env or '{}'))
        ctx['src_rec_ids'] = ctx['src_rec_ids'][:1]
        values = self._get_preview_values(cr, uid, ctx)
        values['ref_template'] = self._get_template(cr, uid, ctx).id
        values['state'] = 'single'
        return self.write(cr, uid, ids, values, context = context)

    def sav_to_drafts(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mailid = self.save_to_mailbox(cr, uid, ids, context)
        if self.pool.get('poweremail.mailbox').write(cr, uid, mailid, {'folder':'drafts'}, context):
            return {'type':'ir.actions.act_window_close' }

    def send_mail(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mailbox_obj = self.pool.get('poweremail.mailbox')
        folder = context.get('folder', 'outbox')
        values = {'folder': folder}

        mail_ids = self.save_to_mailbox(cr, uid, ids, context)

        if mail_ids:
            for mail_id in mail_ids:
                if not mailbox_obj.is_valid(cr, uid, mail_id):
                    values['folder'] = 'error'
                    mailbox_v = mailbox_obj.read(cr, uid, mail_id, ['history'], context=context)
                    values['history'] = '{}\n{}'.format(
                        _(u'Not valid destiny email'), mailbox_v['history'] or ''
                    )
                else:
                    values['folder'] = folder
                mailbox_obj.write(cr, uid, [mail_id], values, context)

        return {'type': 'ir.actions.act_window_close'}

    def get_generated(self, cr, uid, ids=None, context=None):
        if ids is None:
            ids = []
        if context is None:
            context = {}
        folder = context.get('folder', 'outbox')
        logger = netsvc.Logger()
        if context['src_rec_ids'] and len(context['src_rec_ids'])>1:
            #Means there are multiple items selected for email.
            mail_ids = self.save_to_mailbox(cr, uid, ids, context)
            if mail_ids:
                self.pool.get('poweremail.mailbox').write(cr, uid, mail_ids, {'folder': folder}, context)
                logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("Emails for multiple items saved in outbox."))
                self.write(cr, uid, ids, {
                    'generated':len(mail_ids),
                    'state':'done'
                }, context)
            else:
                raise osv.except_osv(_("Power Email"),_("Email sending failed for one or more objects."))
        return True

    def save_to_mailbox(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        template_o = self.pool.get('poweremail.templates')

        wiz = self.simple_browse(cr, uid, ids[0], context=context)
        ctx = self._get_source_context(cr, uid, wiz, context)
        ctx.update(safe_eval(wiz.env or '{}'))
        template = self._get_template(cr, uid, ctx)
        src_rec_ids = ctx['src_rec_ids'][: ]

        from_val = wiz['from']
        if isinstance(from_val, (list, tuple)):
            from_val = from_val[0]
        if from_val:
            ctx['account_id'] = int(from_val)

        ctx['single_email'] = wiz.single_email
        ctx['use_sign'] = wiz.signature
        # The wizard decides the destination folder after generating the mail.
        ctx['save_to_drafts'] = True
        ctx['wizard_attachment_ids'] = [attachment.id for attachment in wiz.attachment_ids]

        ctx['wizard_overrides'] = {
            'to': wiz.to,
            'cc': wiz.cc,
            'bcc': wiz.bcc,
            'subject': wiz.subject,
            'body_text': wiz.body_text,
            'body_html': wiz.body_html,
            'priority': wiz.priority,
            'report': wiz.report,
        }
        mail_id = template_o.generate_mail_sync(cr, uid, template.id, src_rec_ids, context=ctx)
        if not mail_id:
            return []
        return list(mail_id) if isinstance(mail_id, (list, tuple)) else [mail_id]


poweremail_send_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
