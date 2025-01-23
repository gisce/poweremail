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
import base64
import time
from tools.translate import _
import tools
from .poweremail_template import get_value
from .poweremail_core import filter_send_emails, _priority_selection
from premailer import transform


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

        lang = self.get_value(cr, uid, template, template.lang, context)
        if lang:
            # Use translated template if necessary
            ctx = context.copy()
            ctx['lang'] = lang
            template = template_obj.browse(cr, uid, template.id, ctx)
        return template

    def _get_template_value(self, cr, uid, field, context=None):
        template = self._get_template(cr, uid, context)
        if not template:
            return False
        if len(context['src_rec_ids']) > 1: # Multiple Mail: Gets original template values for multiple email change
            return getattr(template, field)
        else: # Simple Mail: Gets computed template values
            value = self.get_value(cr, uid, template, getattr(template, field), context)
            if template.inline and field == 'def_body_text':
                value = transform(value)

            return value

    _columns = {
        'state':fields.selection([
                        ('single','Simple Mail Wizard Step 1'),
                        ('multi','Multiple Mail Wizard Step 1'),
                        ('send_type','Send Type'),
                        ('done','Wizard Complete')
                                  ],'Status',readonly=True),
        'ref_template':fields.many2one('poweremail.templates','Template',readonly=True),
        'rel_model':fields.many2one('ir.model','Model',readonly=True),
        'rel_model_ref':fields.integer('Referred Document',readonly=True),
        'from':fields.selection(_get_accounts,'From Account',select=True),
        'to':fields.char('To',size=250,required=True),
        'cc':fields.char('CC',size=250,),
        'bcc':fields.char('BCC',size=250,),
        'subject':fields.char('Subject',size=200),
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
    }

    _defaults = {
        'state': lambda self,cr,uid,ctx: len(ctx['src_rec_ids']) > 1 and 'send_type' or 'single',
        'rel_model': lambda self,cr,uid,ctx: self.pool.get('ir.model').search(cr,uid,[('model','=',ctx['src_model'])],context=ctx)[0],
        'rel_model_ref': lambda self,cr,uid,ctx: ctx['active_id'],
        'to': lambda self,cr,uid,ctx: filter_send_emails(self._get_template_value(cr, uid, 'def_to', ctx)),
        'cc': lambda self,cr,uid,ctx: filter_send_emails(self._get_template_value(cr, uid, 'def_cc', ctx)),
        'bcc': lambda self,cr,uid,ctx: filter_send_emails(self._get_template_value(cr, uid, 'def_bcc', ctx)),
        'subject':lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'def_subject', ctx),
        'body_text':lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'def_body_text', ctx),
        'body_html':lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'def_body_html', ctx),
        'report': lambda self,cr,uid,ctx: self._get_template_value(cr, uid, 'file_name', ctx),
        'signature': lambda self,cr,uid,ctx: self._get_template(cr, uid, ctx).use_sign,
        'ref_template':lambda self,cr,uid,ctx: self._get_template(cr, uid, ctx).id,
        'requested':lambda self,cr,uid,ctx: len(ctx['src_rec_ids']),
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

    def compute_second_step(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        wizard = self.browse(cr, uid, ids[0], context)
        if not wizard.single_email:
            return self.write(cr, uid, ids, {'state': 'multi'}, context)
        # We send a single email for several records. We compute the values from the first record
        ctx = context.copy()
        ctx['src_rec_ids'] = ctx['src_rec_ids'][:1]
        values = {
            'to': self._get_template_value(cr, uid, 'def_to', ctx),
            'cc': self._get_template_value(cr, uid, 'def_cc', ctx),
            'bcc': self._get_template_value(cr, uid, 'def_bcc', ctx),
            'subject': self._get_template_value(cr, uid, 'def_subject', ctx),
            'body_text': self._get_template_value(cr, uid, 'def_body_text', ctx),
            'body_html': self._get_template_value(cr, uid, 'def_body_html', ctx),
            'report': self._get_template_value(cr, uid, 'file_name', ctx),
            'signature': self._get_template(cr, uid, ctx).use_sign,
            'ref_template': self._get_template(cr, uid, ctx).id,
            'state': 'single',
        }
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

    def get_end_value(self, cr, uid, src_rec_id, value, template, context=None):
        if context is None:
            context = {}
        if len(context['src_rec_ids']) > 1:  # Multiple Mail: Gets value from the template
            return self.get_value(cr, uid, template, value, context, src_rec_id)
        else:
            return value

    def create_mail(self, cr, uid, screen_vals, src_rec_id, vals, context=None):
        if context is None:
            context = {}

        mailbox_obj = self.pool.get('poweremail.mailbox')
        res_users_obj = self.pool.get('res.users')

        vals.update(context.get("extra_vals", {}))
        if screen_vals['signature']:
            signature = res_users_obj.read(cr, uid, uid, ['signature'], context=context)['signature']
            if signature:
                vals['pem_body_text'] = tools.ustr(vals['pem_body_text'] or '') + '\n--\n' + signature
                vals['pem_body_html'] = tools.ustr(vals['pem_body_html'] or '') + signature
        # Create partly the mail and later update attachments
        ctx = context.copy()
        ctx.update({'src_rec_id': src_rec_id})
        mail_id = mailbox_obj.create(cr, uid, vals, context=ctx)
        return mail_id

    def create_report_attachment(self, cr, uid, template, vals, screen_vals, mail_id, report_record_ids, src_rec_id, context=None):
        if context is None:
            context = {}

        ir_act_rep_xml_obj = self.pool.get('ir.actions.report.xml')
        ir_model_obj = self.pool.get('ir.model')
        attach_obj = self.pool.get('ir.attachment')

        if template.report_template:
            reportname_read = ir_act_rep_xml_obj.read(
                cr, uid, template.report_template.id, ['report_name'], context=context
            )['report_name']
            reportname = 'report.' + reportname_read
            data = {}
            data['model'] = ir_model_obj.browse(cr, uid, screen_vals['rel_model'], context=context).model
            service = netsvc.LocalService(reportname)
            if template.report_template.context:
                context.update(eval(template.report_template.context))
            if screen_vals['single_email'] and len(report_record_ids) > 1:
                # The optional attachment will be generated as a single file for all these records
                (result, format) = service.create(cr, uid, report_record_ids, data, context=context)
            else:
                (result, format) = service.create(cr, uid, [src_rec_id], data, context=context)
            attach_vals = {
                'name': _('%s (Email Attachment)') % tools.ustr(vals['pem_subject']),
                'datas': base64.b64encode(result),
                'datas_fname': tools.ustr(
                    self.get_end_value(
                        cr, uid, src_rec_id, screen_vals['report'], template, context=context
                    ) or _('Report')
                ) + "." + format,
                'description': vals['pem_body_text'] or _("No Description"),
                'res_model': 'poweremail.mailbox',
                'res_id': mail_id
            }
            attachment_id = attach_obj.create(cr, uid, attach_vals, context=context)
            return attachment_id
        return False

    def process_extra_attachment_in_template(self, cr, uid, template, src_rec_id, mail_id, data, context=None):
        if context is None:
            context = {}

        attach_obj = self.pool.get('ir.attachment')

        attachment_ids = []
        # For each extra attachment in template
        for tmpl_attach in template.tmpl_attachment_ids:
            report = tmpl_attach.report_id
            reportname = 'report.%s' % report.report_name
            data['model'] = report.model
            model_obj = self.pool.get(report.model)
            # Parse search params
            search_params = eval(self.get_value(cr, uid, template, tmpl_attach.search_params,context, src_rec_id))
            report_model_ids = model_obj.search(cr, uid, search_params, context=context)
            file_name = self.get_value(cr, uid, template, tmpl_attach.file_name, context, src_rec_id)
            if report_model_ids:
                service = netsvc.LocalService(reportname)
                (result, format) = service.create(cr, uid, report_model_ids, data, context=context)
                attach_vals = {
                    'name': file_name,
                    'datas': base64.b64encode(result),
                    'datas_fname': file_name,
                    'description': _("No Description"),
                    'res_model': 'poweremail.mailbox',
                    'res_id': mail_id
                }
                attachment_id = attach_obj.create(cr, uid, attach_vals, context=context)
                attachment_ids.append(attachment_id)
        return attachment_ids

    def add_attachment_documents(self, cr, uid, screen_vals, mail_id, context=None):
        if context is None:
            context = {}

        attach_obj = self.pool.get('ir.attachment')

        attach_values = {
                'res_model': 'poweremail.mailbox',
                'res_id': mail_id,
        }

        # Add document attachments
        attachment_ids_doc = []
        for attachment_id in screen_vals.get('attachment_ids', []):
            new_id = attach_obj.copy(cr, uid, attachment_id, attach_values, context=context)
            attachment_ids_doc.append(new_id)
        return attachment_ids_doc

    def add_template_attachments(self, cr, uid, template, mail_id, context=None):
        if context is None:
            context = {}

        attach_obj = self.pool.get('ir.attachment')

        # Add template attachments
        search_params = [
            ('res_model', '=', 'poweremail.templates'),
            ('res_id', '=', template.id),
        ]
        if context.get('lang'):
            search_params.append(('datas_fname', 'ilike', '%%.%s.%%' % context['lang']))
            attach_ids = attach_obj.search(cr, uid, search_params, context=context)
        else:
            return []
        attachment_ids_templ = []
        for attach in attach_obj.browse(cr, uid, attach_ids, context=context):
            attach_values = {
                'res_model': 'poweremail.mailbox',
                'res_id': mail_id,
                'name': attach.name.replace('.%s' % context['lang'], ''),
                'datas_fname': attach.datas_fname.replace('.%s' % context['lang'], '')
            }
            new_id = attach_obj.copy(cr, uid, attach.id, attach_values, context=context)
            attachment_ids_templ.append(new_id)
        return attachment_ids_templ

    def add_record_attachments(self, cursor, uid, template, src_rec_id, context=None):
        attachment_ids = []
        if template.attach_record_items:
            attachment_o = self.pool.get('ir.attachment')
            attachment_sp = [('res_model', '=', template.object_name.model),
                             ('res_id', '=', src_rec_id)]

            if template.record_attachment_categories:
                attachment_sp.append(('category_id', 'in', [c.id for c in template.record_attachment_categories]))
            attachment_ids = attachment_o.search(cursor, uid, attachment_sp, context=context)
        return attachment_ids

    def create_partner_event(self, cr, uid, template, vals, data, src_rec_id, mail_id, attachment_ids, context=None):
        if context is None:
            context = {}

        rrlink_obj = self.pool.get('res.request.link')
        mailgate_obj = self.pool.get('mailgate.message')

        # Create a partner event
        if template.partner_event and self._get_template_value(cr, uid, 'partner_event', context=context):
            name = vals['pem_subject']
            if isinstance(name, str):
                name = unicode(name, 'utf-8')
            if len(name) > 64:
                name = name[:61] + '...'
            model = res_id = False
            if template.report_template and rrlink_obj.search(cr, uid, [
                ('object', '=', data['model'])], context=context):
                model = data['model']
                res_id = src_rec_id
            elif attachment_ids and rrlink_obj.search(cr, uid, [('object', '=', 'ir.attachment')], context=context):
                model = 'ir.attachment'
                res_id = attachment_ids[0]
            cr.execute("SELECT state from ir_module_module where state='installed' and name = 'mail_gateway'")
            mail_gateway = cr.fetchall()
            if mail_gateway:
                values = {
                    'history': True,
                    'name': name,
                    'date': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': uid,
                    'email_from': vals['pem_from'] or None,
                    'email_to': vals['pem_to'] or None,
                    'email_cc': vals['pem_cc'] or None,
                    'email_bcc': vals['pem_bcc'] or None,
                    'message_id': mail_id,
                    'description': vals['pem_body_text'] and vals['pem_body_text'] or vals['pem_body_html'],
                    'partner_id': self.get_value(cr, uid, template, template.partner_event, context, src_rec_id),
                    'model': model,
                    'res_id': res_id,
                }
                mailgate_obj.create(cr, uid, values, context=context)

    def save_to_mailbox(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        core_accounts_obj = self.pool.get('poweremail.core_accounts')
        mailbox_obj = self.pool.get('poweremail.mailbox')
        template_o = self.pool.get('poweremail.templates')

        mail_ids = []
        template = self._get_template(cr, uid, context)
        screen_vals = self.read(cr, uid, ids[0], [], context)
        if isinstance(screen_vals, list):  # Solves a bug in v5.0.16
            screen_vals = screen_vals[0]
        report_record_ids = context['src_rec_ids'][:]
        if screen_vals['single_email'] and len(context['src_rec_ids']) > 1:
            # We send a single email for several records
            context['src_rec_ids'] = context['src_rec_ids'][:1]
        for src_rec_id in context['src_rec_ids']:
            attachment_ids = []
            accounts = core_accounts_obj.read(cr, uid, screen_vals['from'], context=context)
            vals = {
                'pem_from': tools.ustr(accounts['name']) + "<" + tools.ustr(accounts['email_id']) + ">",
                'pem_to': self.get_end_value(cr, uid, src_rec_id, screen_vals['to'], template, context=context),
                'pem_cc': self.get_end_value(cr, uid, src_rec_id, screen_vals['cc'], template, context=context),
                'pem_bcc': self.get_end_value(cr, uid, src_rec_id, screen_vals['bcc'], template, context=context),
                'pem_subject': self.get_end_value(cr, uid, src_rec_id, screen_vals['subject'], template,
                                                  context=context),
                'pem_body_text': self.get_end_value(cr, uid, src_rec_id, screen_vals['body_text'], template,
                                                    context=context),
                'pem_body_html': self.get_end_value(cr, uid, src_rec_id, screen_vals['body_html'], template,
                                                    context=context),
                'pem_account_id': screen_vals['from'],
                'priority': screen_vals['priority'],
                'state': 'na',
                'mail_type': 'multipart/alternative',
                'template_id': template.id
                # Options:'multipart/mixed','multipart/alternative','text/plain','text/html'
            }
            ctx = context.copy()
            if template.inline:
                vals['pem_body_text'] = transform(vals['pem_body_text'])

            mail_id = self.create_mail(cr, uid, screen_vals, src_rec_id, vals, context=ctx)
            mail_ids.append(mail_id)
            # Ensure report is rendered using template's language. If not found, user's launguage is used.
            ctx = context.copy()
            ctx['lang'] = template_o.get_email_lang(cr, uid, template, src_rec_id, context=ctx)
            attachment_id = self.create_report_attachment(
                cr, uid, template, vals, screen_vals, mail_id, report_record_ids, src_rec_id, context=ctx
            )
            if attachment_id:
                attachment_ids.append(attachment_id)
            data = {}
            attachment_ids_extra = self.process_extra_attachment_in_template(
                cr, uid, template, src_rec_id, mail_id, data, context=ctx
            )
            attachment_ids.extend(attachment_ids_extra)
            # Add document attachments
            attachment_ids_doc = self.add_attachment_documents(cr, uid, screen_vals, mail_id, context=ctx)
            attachment_ids.extend(attachment_ids_doc)
            # Add template attachments
            attachment_ids_templ = self.add_template_attachments(cr, uid, template, mail_id, context=ctx)
            attachment_ids.extend(attachment_ids_templ)
            # Add record attachments
            attachment_ids_record = self.add_record_attachments(cr, uid, template, src_rec_id, context=ctx)
            attachment_ids.extend(attachment_ids_record)

            if attachment_ids:
                mailbox_vals = {
                    'pem_attachments_ids': [[6, 0, attachment_ids]],
                    'mail_type': 'multipart/mixed'
                }
                mailbox_obj.write(cr, uid, mail_id, mailbox_vals, context=context)
            self.create_partner_event(cr, uid, template, vals, data, src_rec_id, mail_id, attachment_ids, context=ctx)
        return mail_ids

poweremail_send_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
