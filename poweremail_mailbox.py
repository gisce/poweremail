"""
Power Email is a module for Open ERP which enables it to send mails
The mailbox is an object which stores the actual email
"""
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
#(at your option) any later version.                                    #
#                                                                       #
#This program is distributed in the hope that it will be useful,        #
#but WITHOUT ANY WARRANTY; without even the implied warranty of         #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
#GNU General Public License for more details.                           #
#                                                                       #
#You should have received a copy of the GNU General Public License      #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.  #
#########################################################################

from osv import osv, fields
import time
import poweremail_engines
from poweremail_core import filter_send_emails, _priority_selection
import netsvc
from tools.translate import _
import tools
import pooler

import re
import os
import email
from email.utils import make_msgid
import qreu

LOGGER = netsvc.Logger()

class PoweremailMailbox(osv.osv):
    _name = "poweremail.mailbox"
    _description = 'Power Email Mailbox included all type inbox,outbox,junk..'
    _rec_name = "pem_subject"
    _order = "date_mail desc"

    def run_mail_scheduler(self, cursor, user, context=None):
        """
        This method is called by Open ERP Scheduler
        to periodically receive & fetch mails
        """
        try:
            self.get_all_mail(cursor, user, context={'all_accounts':True})
        except Exception, e:
            LOGGER.notifyChannel(
                                 _("Power Email"),
                                 netsvc.LOG_ERROR,
                                 _("Error receiving mail: %s") % str(e))
        try:
            self.send_all_mail(cursor, user, context=context)
        except Exception, e:
            LOGGER.notifyChannel(
                                 _("Power Email"),
                                 netsvc.LOG_ERROR,
                                 _("Error sending mail: %s") % str(e))


    def get_all_mail(self, cr, uid, context=None):
        if context is None:
            context = {}
        #8888888888888 FETCHES MAILS 8888888888888888888#
        #email_account: THe ID of poweremil core account
        #Context should also have the last downloaded mail for an account
        #Normlly this function is expected to trigger from scheduler hence the value will not be there
        core_obj = self.pool.get('poweremail.core_accounts')
        if not 'all_accounts' in context.keys():
            #Get mails from that ID only
            core_obj.get_mails(cr, uid, [context['email_account']])
        else:
            accounts = core_obj.search(cr, uid, [('state', '=', 'approved')], context=context)
            core_obj.get_mails(cr, uid, accounts)

    def get_fullmail(self, cr, uid, context=None):
        if context is None:
            context = {}
        #8888888888888 FETCHES MAILS 8888888888888888888#
        core_obj = self.pool.get('poweremail.core_accounts')
        if 'mailboxref' in context.keys():
            #Get mails from that ID only
            core_obj.get_fullmail(cr, uid, context['email_account'], context)
        else:
            raise osv.except_osv(_("Mail fetch exception"), _("No information on which mail should be fetched fully"))

    def send_all_mail(self, cr, uid, ids=None, context=None):
        if ids is None:
            ids = []
        if context is None:
            context = {}
        #8888888888888 SENDS MAILS IN OUTBOX 8888888888888888888#
        #get ids of mails in outbox
        filters = [('folder', '=', 'outbox'), ('state', '!=', 'sending')]
        if 'filters' in context.keys():
            for each_filter in context['filters']:
                filters.append(each_filter)
        limit = context.get('limit', None)
        order = "priority desc, date_mail desc"
        ids = self.search(cr, uid, filters,
                          limit=limit, order=order,
                          context=context)
        LOGGER.notifyChannel('Power Email', netsvc.LOG_INFO,
                             'Sending All mail (PID: %s)' % os.getpid())
        # To prevent resend the same emails in several send_all_mail() calls
        # We put this in a new cursor/transaction to avoid concurrent
        # transaction isolation problems
        db = pooler.get_db_only(cr.dbname)
        cr_tmp = db.cursor()
        try:
            self.write(cr_tmp, uid, ids, {'state':'sending'}, context)
            cr_tmp.commit()
        except:
            cr_tmp.rollback()
        finally:
            cr_tmp.close()
        #send mails one by one
        self.send_this_mail(cr, uid, ids, context)
        return True

    def send_this_mail(self, cr, uid, ids=None, context=None):
        if ids is None:
            ids = []
        #8888888888888 SENDS THIS MAIL IN OUTBOX 8888888888888888888#
        #send mails one by one
        if not context:
            context = {}
        core_obj = self.pool.get('poweremail.core_accounts')
        conv_obj = self.pool.get('poweremail.conversation')
        for id in ids:
            try:
                context['headers'] = {}
                headers = context['headers']
                values = self.read(cr, uid, id, [], context) #Values will be a dictionary of all entries in the record ref by id
                pem_to = (values['pem_to'] or '').strip()
                if pem_to in ('', 'False'):
                    self.historise(cr, uid, [id],
                                   "No recipient: Email cannot be sent",
                                   context, error=True)
                    continue
                payload = {}
                if values['pem_attachments_ids']:
                    #Get filenames & binary of attachments
                    for attid in values['pem_attachments_ids']:
                        attachment = self.pool.get('ir.attachment').browse(cr, uid, attid, context)#,['datas_fname','datas'])
                        att_name = attachment.datas_fname or attachment.name
                        counter = 1
                        while att_name in payload:
                            att_name = "%s%d" % ( attachment.datas_fname or attachment.name, counter )
                            counter += 1
                        payload[att_name] = attachment.datas
                if values['conversation_id']:
                    mails = conv_obj.browse(cr, uid,
                                            values['conversation_id'][0]).mails
                    headers['References'] = " ".join(
                        [m.pem_message_id for m in mails
                    ])
                    if not headers.get('In-Reply-To', ''):
                        headers['In-Reply-To'] = mails[-1].pem_message_id
                result = core_obj.send_mail(cr, uid,
                                  [values['pem_account_id'][0]],
                                  {'To':values.get('pem_to', u'') or u'', 'CC':values.get('pem_cc', u'') or u'', 'BCC':values.get('pem_bcc', u'') or u''},
                                  values['pem_subject'] or u'',
                                  {'text':values.get('pem_body_text', u'') or u'', 'html':values.get('pem_body_html', u'') or u''},
                                  payload=payload, context=context)
                if result == True:
                    self.write(cr, uid, id, {'folder':'sent', 'state':'na', 'date_mail':time.strftime("%Y-%m-%d %H:%M:%S")}, context)
                    self.historise(cr, uid, [id], "Email sent successfully", context)
                else:
                    self.historise(cr, uid, [id], result, context, error=True)
            except Exception, error:
                logger = netsvc.Logger()
                logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("Sending of Mail %s failed. Probable Reason: Could not login to server\nError: %s") % (id, error))
                self.historise(cr, uid, [id], error, context, error=True)
            self.write(cr, uid, id, {'state':'na'}, context)
        return True

    def send_mail_generic(self, cr, uid, email_from, subject, body,
                          email_to=None, email_cc=None, context=None):
        """ Send an email, if no email_to specified send it to the
        " user that called the function or the email_from if user
        " has no email.
        """

        acc_obj = self.pool.get('poweremail.core_accounts')
        user_obj = self.pool.get('res.users')

        search_params = [('email_id', '=', email_from)]
        acc_id = acc_obj.search(cr, uid, search_params)
        if not acc_id:
            raise osv.except_osv('Error',
                                 _('%s account not found') % email_from)
        else:
            acc_id = acc_id[0]

        user = user_obj.browse(cr, uid, uid)
        if not email_to:
            email_to = user.address_id.email
        if not email_to:
            email_to = email_from

        vals = {
            'pem_from': email_from,
            'pem_to': email_to,
            'pem_subject': subject,
            'pem_body_text': body,
            'pem_account_id': acc_id,
        }
        if email_cc:
            vals['pem_cc'] = email_cc

        mail_id = self.create(cr, uid, vals, context)
        return self.send_this_mail(cr, uid, [mail_id], context)

    def historise(self, cr, uid, ids, message='', context=None, error=False):

        user_obj = self.pool.get('res.users')
        if not context:
            context = {}
        user = user_obj.browse(cr, uid, uid)
        if 'lang' not in context:
            context.update({'lang': user.context_lang})
        for id in ids:
            #Notify the sender errors
            if (context.get('notify_errors', False)
                and error
                and not context.get('bounce', False)):
                mail = self.browse(cr, uid, id)
                vals = {'folder': 'outbox',
                        'history': '',
                        'pem_to': mail.pem_account_id.email_id,
                        'pem_subject': _(u"Error sending email: %s") % mail.pem_subject}
                bounce_mail_id = self.copy(cr, uid, id, vals)
                ctx = context.copy()
                ctx.update({'bounce': True})
                self.send_this_mail(cr, uid, [bounce_mail_id], ctx)
                bounce_mail = self.browse(cr, uid, bounce_mail_id)
                #If bounce mail cannot be sent, unlink it
                if bounce_mail.folder != 'sent':
                    bounce_mail.unlink()
            history = self.read(cr, uid, id, ['history'], context).get('history', '')
            self.write(cr, uid, id, {'history': (history or '') + "\n" + time.strftime("%Y-%m-%d %H:%M:%S") + ": " + tools.ustr(message)}, context)

    def complete_mail(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        #8888888888888 COMPLETE PARTIALLY DOWNLOADED MAILS 8888888888888888888#
        #FUNCTION get_fullmail(self,cr,uid,mailid) in core is used where mailid=id of current email,
        for id in ids:
            self.pool.get('poweremail.core_accounts').get_fullmail(cr, uid, id, context)
            self.historise(cr, uid, [id], "Full email downloaded", context)

    def check_email_valid(self, email):
        """Check if email is valid. Check @ and .
        :email str
        return True/False
        """
        def get_validate_email(email):
            if not re.match(r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$", email):
                return False
            return True

        if not email:
            return False

        emails = email.split(',')
        if len(emails)>0:
            for email in emails:
                if not get_validate_email(email.strip()):
                    return False
                    break
        return True

    def create(self, cursor, user, vals, context=None):
        mail = qreu.Email(vals['pem_mail_orig'])
        vals['pem_subject'] = mail.subject
        for field in ('pem_to', 'pem_cc', 'pem_bcc'):
            if field in vals:
                vals[field] = filter_send_emails(vals[field])
        res_id = super(PoweremailMailbox, self).create(cursor, user, vals,
                                                       context)
        return res_id

    _columns = {
            'pem_from':fields.char(
                            'From',
                            size=64),
            'pem_to':fields.char(
                            'Recepient (To)',
                            size=250,),
            'pem_cc':fields.char(
                            ' CC',
                            size=250),
            'pem_bcc':fields.char(
                            ' BCC',
                            size=250),
            'pem_subject':fields.char(
                            ' Subject',
                            size=200,),
            'pem_body_text':fields.text(
                            'Standard Body (Text)'),
            'pem_body_html':fields.text(
                            'Body (Text-Web Client Only)'),
            'pem_attachments_ids':fields.many2many(
                            'ir.attachment',
                            'mail_attachments_rel',
                            'mail_id',
                            'att_id',
                            'Attachments'),
            'pem_account_id' :fields.many2one(
                            'poweremail.core_accounts',
                            'User account',
                            required=True),
            'pem_user':fields.related(
                            'pem_account_id',
                            'user',
                            type="many2one",
                            relation="res.users",
                            string="User"),
            'server_ref':fields.integer(
                            'Server Reference of mail',
                            help="Applicable for inward items only."),
            'pem_recd':fields.char('Received at', size=50),
            'mail_type':fields.selection([
                            ('multipart/mixed',
                             'Has Attachments'),
                            ('multipart/alternative',
                             'Plain Text & HTML with no attachments'),
                            ('multipart/related',
                             'Intermixed content'),
                            ('text/plain',
                             'Plain Text'),
                            ('text/html',
                             'HTML Body'),
                            ], 'Mail Contents'),
            #I like GMAIL which allows putting same mail in many folders
            #Lets plan it for 0.9
            'folder':fields.selection([
                            ('inbox', 'Inbox'),
                            ('drafts', 'Drafts'),
                            ('outbox', 'Outbox'),
                            ('trash', 'Trash'),
                            ('followup', 'Follow Up'),
                            ('sent', 'Sent Items'),
                            ], 'Folder', required=True),
            'state':fields.selection([
                            ('read', 'Read'),
                            ('unread', 'Un-Read'),
                            ('na', 'Not Applicable'),
                            ('sending', 'Sending'),
                            ], 'Status', required=True),
            'date_mail':fields.datetime(
                            'Rec/Sent Date'),
            'history':fields.text(
                            'History',
                            readonly=True,
                            store=True),
            'pem_message_id': fields.char('Message-Id', size=256,
                                          required=True),
            'pem_mail_orig': fields.text('Original Mail'),
            'priority': fields.selection(_priority_selection,
                                         'Priority')
        }

    _defaults = {
        'state': lambda * a: 'na',
        'folder': lambda * a: 'outbox',
        'pem_message_id': lambda *a: make_msgid('poweremail'),
        'priority': lambda *a: '1',
    }

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        if context.get('company', False):
            users_groups = self.pool.get('res.users').browse(cr, uid, uid, context).groups_id
            group_acc_rel = {}
            #get all accounts and get a table of {group1:[account1,account2],group2:[account1]}
            for each_account_id in self.pool.get('poweremail.core_accounts').search(cr, uid, [('state', '=', 'approved'), ('company', '=', 'yes')], context=context):
                account = self.pool.get('poweremail.core_accounts').browse(cr, uid, each_account_id, context)
                for each_group in account.allowed_groups:
                    if not account.id in group_acc_rel.get(each_group, []):
                        groups = group_acc_rel.get(each_group, [])
                        groups.append(account.id)
                        group_acc_rel[each_group] = groups
            users_company_accounts = []
            for each_group in group_acc_rel.keys():
                if each_group in users_groups:
                    for each_account in group_acc_rel[each_group]:
                        if not each_account in users_company_accounts:
                            users_company_accounts.append(each_account)
            args.append(('pem_account_id', 'in', users_company_accounts))
        return super(osv.osv, self).search(cr, uid, args, offset, limit,
                order, context=context, count=count)

PoweremailMailbox()


class PoweremailConversation(osv.osv):
    """
    This is an ambitious approach to grouping emails
    by automatically grouping attributes
    Something like Gmail
    
    Warning: Incomplete
    """
    _name = "poweremail.conversation"
    _description = "Conversations are groups of related emails"

    def _from_abstract(self, cursor, uid, ids, field_name, arg, context=None):
        res = {}
        mail_obj = self.pool.get('poweremail.mailbox')
        for conv in self.read(cursor, uid, ids, ['mails']):
            res[conv['id']] = ", ".join(
                set([m['pem_from'].split('<')[0].strip()
                     for m in mail_obj.read(cursor, uid, conv['mails'],
                                            ['pem_from'])])
            )
        return res

    _columns = {
        'name': fields.char(
                    'Name',
                    size=250),
        'mails': fields.one2many(
                    'poweremail.mailbox',
                    'conversation_id',
                    'Related Emails'),
        'from_abstract': fields.function(_from_abstract, type='text',
                                         method=True, store=False)
    }
PoweremailConversation()


class PoweremailMailboxConversation(osv.osv):
    _inherit = "poweremail.mailbox"
    _columns = {
        'conversation_id': fields.many2one('poweremail.conversation',
                                           'Conversation')
    }

    def find_conversation(self, cursor, uid, raw_email, context=None):
        """
        Try to find the conversation

        If a mail is a reply. Try to find the conversation to attach. Uses three
        different aproaches:
        1. Search the conversation of mail.parent
        2. Search one email in the "References" Header
        3. Search one email with the same subject (cleaned) and wichi to or from
           contains the email from
        :return: conversation_id
        """

        mail = qreu.Email(raw_email)
        if not mail:
            return False

        if mail.is_reply:
            search_params_rec = []
            if mail.parent:
                search_params_rec.append([
                    ('pem_message_id', '=', mail.parent)
                ])
            if mail.references:
                search_params_rec.append([
                    ('pem_message_id', 'in', mail.references)
                ])
            search_params_rec.append([
                ('pem_subject', '=', mail.subject),
                '|',
                    ('pem_from', 'ilike', mail.from_.address),
                    ('pem_to', 'ilike', mail.from_.address)
            ])
            for search_params in search_params_rec:
                msg_id = self.search(cursor, uid, search_params)
                if msg_id:
                    conv = self.browse(cursor, uid, msg_id[0]).conversation_id
                    conv_id = conv and conv.id or False
                    return conv_id
        return False

    def create(self, cursor, uid, vals, context=None):
        if context is None:
            context = {}
        conv_obj = self.pool.get('poweremail.conversation')
        if not vals.get('conversation_id', False):
            vals['conversation_id'] = self.find_conversation(
                cursor, uid, vals.get('pem_mail_orig', ''), context
            )
            if not vals['conversation_id']:
                conv_id = conv_obj.create(cursor, uid,
                                          {'name': vals['pem_subject']})
                vals['conversation_id'] = conv_id
        res_id = super(PoweremailMailboxConversation,
                       self).create(cursor, uid, vals, context)
        return res_id
PoweremailMailboxConversation()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
