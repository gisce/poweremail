# -*- encoding: utf-8 -*-
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

from __future__ import absolute_import
from osv import osv, fields
import smtplib
import base64
from email.header import decode_header
from six.moves import StringIO
import re
import netsvc
import poplib
import imaplib
import string
import email
import time, datetime
from tools.translate import _
from tools import config
import tools
import six

from qreu import Email
from qreu.address import Address, parseaddr, getaddresses
from qreu.sendcontext import Sender, SMTPSender
from html2text import html2text


_MAIL_COUNT_MARGIN = 4

def filter_send_emails(emails_str):
    if not emails_str:
        emails_str = ''
    emails = getaddresses([emails_str])
    return ", ".join(Address(*mail).display for mail in emails)

_priority_selection = [('0', 'Low'),
                       ('1', 'Normal'),
                       ('2', 'High')]


def get_email_default_lang():
    return config.get('lang', config.get('default_lang', 'en_US'))


class poweremail_core_accounts(osv.osv):
    """
    Object to store email account settings
    """
    _name = "poweremail.core_accounts"
    _known_content_types = ['multipart/mixed',
                            'multipart/alternative',
                            'multipart/related',
                            'text/plain',
                            'text/html'
                            ]
    _columns = {
        'name': fields.char('Email Account Desc',
                        size=64, required=True,
                        readonly=True, select=True,
                        states={'draft':[('readonly', False)]}),
        'user':fields.many2one('res.users',
                        'Related User', required=True,
                        readonly=True, states={'draft':[('readonly', False)]}),
        'email_id': fields.char('Email ID',
                        size=120, required=True,
                        readonly=True, states={'draft':[('readonly', False)]} ,
                        help="eg: yourname@yourdomain.com"),
        'smtpserver': fields.char('Server',
                        size=120, required=True,
                        readonly=True, states={'draft':[('readonly', False)]},
                        help="Enter name of outgoing server, eg: smtp.gmail.com"),
        'smtpport': fields.integer('SMTP Port ',
                        size=64, required=True,
                        readonly=True, states={'draft':[('readonly', False)]},
                        help="Enter port number, eg: SMTP-587 "),
        'smtpuname': fields.char('User Name',
                        size=120, required=False,
                        readonly=True, states={'draft':[('readonly', False)]}),
        'smtppass': fields.char('Password',
                        size=120, invisible=True,
                        required=False, readonly=True,
                        states={'draft':[('readonly', False)]}),
        'smtptls': fields.boolean(
            'Use TLS', readonly=True,
            states={'draft':[('readonly', False)]},
            help='Start a TLS connection after the SMTP connection'
                 ' (Usually port 587)'
        ),
        'smtpssl': fields.boolean(
            'Use SSL', readonly=True,
            states={'draft': [('readonly', False)]},
            help='Start a SMTP connection through SSL (Usually port 465)'
        ),
        'send_pref': fields.selection([
                                      ('html', 'HTML otherwise Text'),
                                      ('text', 'Text otherwise HTML'),
                                      ('both', 'Both HTML & Text')
                                      ], 'Mail Format', required=True),
        'iserver':fields.char('Incoming Server',
                        size=100, readonly=True,
                        states={'draft':[('readonly', False)]},
                        help="Enter name of incoming server, eg: imap.gmail.com"),
        'isport': fields.integer('Port',
                        readonly=True, states={'draft':[('readonly', False)]},
                        help="For example IMAP: 993,POP3:995"),
        'isuser':fields.char('User Name',
                        size=100, readonly=True,
                        states={'draft':[('readonly', False)]}),
        'ispass':fields.char('Password',
                        size=100, readonly=True,
                        states={'draft':[('readonly', False)]}),
        'iserver_type': fields.selection([
                        ('imap', 'IMAP'),
                        ('pop3', 'POP3')
                        ], 'Server Type', readonly=True,
                        states={'draft':[('readonly', False)]}),
        'isssl':fields.boolean('Use SSL',
                        readonly=True, states={
                                           'draft':[('readonly', False)]
                                           }),
        'isfolder':fields.char('Folder',
                        readonly=True, size=100,
                        help="Folder to be used for downloading IMAP mails.\n" \
                        "Click on adjacent button to select from a list of folders."),
        'last_mail_id':fields.integer(
                        'Last Downloaded Mail', readonly=True),
        'rec_headers_den_mail':fields.boolean(
                        'First Receive headers, then download mail'),
        'dont_auto_down_attach':fields.boolean(
                        'Dont Download attachments automatically'),
        'allowed_groups':fields.many2many(
                        'res.groups',
                        'account_group_rel', 'templ_id', 'group_id',
                        string="Allowed User Groups",
                        help="Only users from these groups will be " \
                        "allowed to send mails from this ID."),
        'company':fields.selection([
                        ('yes', 'Yes'),
                        ('no', 'No')
                        ], 'Company Mail A/c',
                        readonly=True,
                        help="Select if this mail account does not belong " \
                        "to specific user but the organisation as a whole. " \
                        "eg: info@somedomain.com",
                        required=True, states={
                                           'draft':[('readonly', False)]
                                           }),

        'state':fields.selection([
                                  ('draft', 'Initiated'),
                                  ('suspended', 'Suspended'),
                                  ('approved', 'Approved')
                                  ],
                        'Account Status', required=True, readonly=True),
    }

    _defaults = {
         'name':lambda self, cursor, user, context:self.pool.get(
                                                'res.users'
                                                ).read(
                                                        cursor,
                                                        user,
                                                        user,
                                                        ['name'],
                                                        context
                                                        )['name'],
         'smtpssl':lambda * a:True,
         'state':lambda * a:'draft',
         'user':lambda self, cursor, user, context:user,
         'iserver_type':lambda * a:'imap',
         'isssl': lambda * a: True,
         'last_mail_id':lambda * a:0,
         'rec_headers_den_mail':lambda * a:True,
         'dont_auto_down_attach':lambda * a:True,
         'send_pref':lambda * a: 'html',
         'smtptls':lambda * a:True,
     }

    _sql_constraints = [
        (
         'email_uniq',
         'unique (email_id)',
         'Another setting already exists with this email ID !')
    ]

    def _constraint_unique(self, cursor, user, ids):
        """
        This makes sure that you dont give personal
        users two accounts with same ID (Validated in sql constaints)
        However this constraint exempts company accounts.
        Any no of co accounts for a user is allowed
        """
        if self.read(cursor, user, ids, ['company'])[0]['company'] == 'no':
            accounts = self.search(cursor, user, [
                                                 ('user', '=', user),
                                                 ('company', '=', 'no')
                                                 ])
            if len(accounts) > 1 :
                return False
            else :
                return True
        else:
            return True

    _constraints = [
        (_constraint_unique,
         'Error: You are not allowed to have more than 1 account.',
         [])
    ]

    def on_change_emailid(self, cursor, user, ids, name=None, email_id=None, context=None):
        """
        Called when the email ID field changes.
        
        UI enhancement
        Writes the same email value to the smtpusername
        and incoming username
        """
        #TODO: Check and remove the write. Is it needed?
        self.write(cursor, user, ids, {'state':'draft'}, context=context)
        return {
                'value': {
                          'state': 'draft',
                          'smtpuname':email_id,
                          'isuser':email_id
                          }
                }

    def login_smtp(self, cursor, uid, core_account, smtp_conn, context=None):
        if context is None:
            context = {}

        smtp_conn.login(core_account.smtpuname, core_account.smtppass.encode('ascii'))

    def _get_outgoing_server(self, cursor, user, ids, context=None):
        """
        Returns the Out Going Connection (SMTP) object
        
        @attention: DO NOT USE except_osv IN THIS METHOD
        @param cursor: Database Cursor
        @param user: ID of current user
        @param ids: ID/list of ids of current object for
                    which connection is required
                    First ID will be chosen from lists
        @param context: Context
        
        @return: SMTP server object or Exception
        """
        #Type cast ids to integer
        if type(ids) == list:
            ids = ids[0]
        this_object = self.browse(cursor, user, ids, context)
        if this_object:
            if this_object.smtpserver and this_object.smtpport:
                try:
                    if this_object.smtpssl:
                        serv = smtplib.SMTP_SSL(this_object.smtpserver, this_object.smtpport)
                    else:
                        serv = smtplib.SMTP(this_object.smtpserver, this_object.smtpport)
                    serv.ehlo()
                    if this_object.smtptls:
                        serv.starttls()
                        serv.ehlo()
                except Exception as error:
                    raise error
                try:
                    if serv.has_extn('AUTH'):
                        if this_object.smtpuname or this_object.smtppass:
                            self.login_smtp(cursor, user, this_object, serv, context=context)
                except Exception as error:
                    raise error
                return serv
            raise Exception(_("SMTP SERVER or PORT not specified"))
        raise Exception(_("Core connection for the given ID does not exist"))

    def check_outgoing_connection(self, cursor, user, ids, context=None):
        """
        checks SMTP credentials and confirms if outgoing connection works
        (Attached to button)
        @param cursor: Database Cursor
        @param user: ID of current user
        @param ids: list of ids of current object for
                    which connection is required
        @param context: Context
        """
        try:
            self._get_outgoing_server(cursor, user, ids, context)
            raise osv.except_osv(_("SMTP Test Connection Was Successful"), '')
        except osv.except_osv as success_message:
            raise success_message
        except Exception as error:
            raise osv.except_osv(
                                 _("Out going connection test failed"),
                                 _("Reason: %s") % error
                                 )

    def login_imap(self, cursor, uid, core_account, imap_connection, context=None):
        if context is None:
            context = {}

        imap_connection.login(core_account.isuser, core_account.ispass)

    def _get_imap_server(self, cursor, uid, record):
        """
        @param record: Browse record of current connection
        @return: IMAP or IMAP_SSL object
        """
        logger = netsvc.Logger()

        if record:
            try:
                if record.isssl:
                    serv = imaplib.IMAP4_SSL(record.iserver, record.isport)
                else:
                    serv = imaplib.IMAP4(record.iserver, record.isport)
            except imaplib.IMAP4.error as error:
                logger.notifyChannel(
                    _("Power Email"),
                    netsvc.LOG_ERROR,
                    _("IMAP Server Error: {}".format(error))
                )

            try:
                self.login_imap(cursor, uid, record, serv)
            except imaplib.IMAP4.error as error:
                msg = _("IMAP Server Login Error: {}".format(error))
                logger.notifyChannel(
                    _("Power Email"),
                    netsvc.LOG_ERROR,
                    msg
                )
                raise Exception(msg)

            return serv

    def _get_pop3_server(self, record):
        """
        @param record: Browse record of current connection
        @return: POP3 or POP3_SSL object
        """
        if record:
            if record.isssl:
                serv = poplib.POP3_SSL(record.iserver, record.isport)
            else:
                serv = poplib.POP3(record.iserver, record.isport)
            #Now try to login
            serv.user(record.isuser)
            serv.pass_(record.ispass)
            return serv
        raise Exception(
                        _("Programming Error in _get_pop3_server method. The record received is invalid.")
                        )

    def _get_incoming_server(self, cursor, user, ids, context=None):
        """
        Returns the Incoming Server object
        Could be IMAP/IMAP_SSL/POP3/POP3_SSL
        
        @attention: DO NOT USE except_osv IN THIS METHOD
        
        @param cursor: Database Cursor
        @param user: ID of current user
        @param ids: ID/list of ids of current object for
                    which connection is required
                    First ID will be chosen from lists
        @param context: Context
        
        @return: IMAP/POP3 server object or Exception
        """
        #Type cast ids to integer
        if type(ids) == list:
            ids = ids[0]
        this_object = self.browse(cursor, user, ids, context)
        if this_object:
            #First validate data
            if not this_object.iserver:
                raise Exception(_("Incoming server is not defined"))
            if not this_object.isport:
                raise Exception(_("Incoming port is not defined"))
            if not this_object.isuser:
                raise Exception(_("Incoming server user name is not defined"))
            if not this_object.isuser:
                raise Exception(_("Incoming server password is not defined"))
            #Now fetch the connection
            try:
                if this_object.iserver_type == 'imap':
                    serv = self._get_imap_server(cursor, user, this_object)
                elif this_object.iserver_type == 'pop3':
                    serv = self._get_pop3_server(this_object)
                return serv
            except Exception as error:
                raise Exception(error)
        raise Exception(
                    _("The specified record for connection does not exist")
                        )

    def check_incoming_connection(self, cursor, user, ids, context=None):
        """
        checks incoming credentials and confirms if outgoing connection works
        (Attached to button)
        @param cursor: Database Cursor
        @param user: ID of current user
        @param ids: list of ids of current object for
                    which connection is required
        @param context: Context
        """
        try:
            self._get_incoming_server(cursor, user, ids, context)
        except osv.except_osv as success_message:
            raise success_message
        except Exception as error:
            raise osv.except_osv(
                                 _("In coming connection test failed"),
                                 _("Reason: %s") % error
                                 )
        raise osv.except_osv(_("Incoming Test Connection Was Successful"), '')

    def do_approval(self, cr, uid, ids, context={}):
        #TODO: Check if user has rights
        self.write(cr, uid, ids, {'state':'approved'}, context=context)
#        wf_service = netsvc.LocalService("workflow")

    def smtp_connection(self, cursor, user, id, context=None):
        """
        This method should now wrap smtp_connection
        """
        #This function returns a SMTP server object
        logger = netsvc.Logger()
        core_obj = self.browse(cursor, user, id, context)
        if core_obj.smtpserver and core_obj.smtpport and core_obj.state == 'approved':
            try:
                serv = self._get_outgoing_server(cursor, user, id, context)
            except Exception as error:
                logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("Mail from Account %s failed on login. Probable Reason: Could not login to server\nError: %s") % (id, error))
                return False
            #Everything is complete, now return the connection
            return serv
        else:
            logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("Mail from Account %s failed. Probable Reason: Account not approved") % id)
            return False

#**************************** MAIL SENDING FEATURES ***********************#
    def split_to_ids(self, ids_as_str):
        """
        Identifies email IDs separated by separators
        and returns a list
        TODO: Doc this
        "a@b.com,c@bcom; d@b.com;e@b.com->['a@b.com',...]"
        """
        email_sep_by_commas = ids_as_str \
            .replace('; ', ',') \
            .replace(';', ',')  \
            .replace(', ', ',') \
            .replace('"', '')   \
            .replace("'", "")
        return email_sep_by_commas.split(',')

    def get_ids_from_dict(self, addresses={}):
        """
        TODO: Doc this
        """
        result = {'all':[]}
        keys = ['To', 'CC', 'BCC', 'FROM']
        for each in keys:
            ids_as_list = self.split_to_ids(addresses.get(each, u''))
            while u'' in ids_as_list:
                ids_as_list.remove(u'')
            if each == 'FROM':
                result[each] = ids_as_list[0]
            else:
                result[each] = ids_as_list
            result['all'].extend(ids_as_list)
        return result

    def send_mail(self, cr, uid, ids,
                  addresses, subject='', body=None, payload=None, context=None):
        def create_qreu(headers, payload, **kwargs):
            mail = Email(**{
                'subject': kwargs.get('subject'),
                'from': kwargs.get('from'),
                'to': kwargs.get('to'),
                'cc': kwargs.get('cc'),
                'bcc': kwargs.get('bcc'),
                'body_text': kwargs.get('body_text'),
                'body_html': kwargs.get('body_html')
            })
            for header, value in headers.items():
                mail.add_header(header, value)
            # Add all attachments (if any)
            for file_name in payload.keys():
                # Decode b64 from raw base64 attachment and write it to a buffer
                attachment_buffer = StringIO()
                attachment_buffer.write(
                    base64.b64decode(payload[file_name]))
                mail.add_attachment(
                    input_buff=attachment_buffer,
                    attname=file_name
                )
                del attachment_buffer
            return mail

        def parse_body_html(pem_body_html, pem_body_text):
            html = pem_body_text if not pem_body_html else pem_body_html
            if (
                html and html.strip()[0] != '<' and
                "<br/>" not in html and
                "<br>" not in html
            ):
                html = html.replace('\n', '<br/>')
            return html

        def parse_sender(pem_account, pem_addresses):
            from_addr = pem_addresses.get('FROM', False)
            sender_addr = pem_account
            if from_addr:
                # If custom from address
                from_addr = Address(*parseaddr(from_addr))
                account_addr = Address(*parseaddr(pem_account))
                if from_addr.display_name:
                    # If from address has display name, use it with account addr
                    sender_addr = u'{} <{}>'.format(
                        from_addr.display_name,
                        account_addr.address
                    ).strip()
                if from_addr.address != account_addr.address:
                    # ADD the custom from address to BCC
                    if not pem_addresses.get('BCC', False):
                        pem_addresses['BCC'] = []
                    pem_addresses['BCC'].append(u'{}'.format(from_addr.address))
                    pem_addresses['BCC'] = list(set(pem_addresses['BCC']))
            return sender_addr

        if body is None:
            body = {}
        if payload is None:
            payload = {}
        if context is None:
            context = {}
        logger = netsvc.Logger()
        # Get Addresses to send the email
        sender_str = ''
        try:
            addresses_list = self.get_ids_from_dict(addresses)
        except Exception as error:
            logger.notifyChannel(
                _("Power Email"), netsvc.LOG_ERROR,
                _("Cannot send mails of accounts {} "
                  "when the addresses list is empty").format(ids)
            )
            return error
        # Get email Data
        subject = subject or context.get('subject', '') or ''
        body_html = parse_body_html(
            pem_body_html=tools.ustr(body.get('html', '')),
            pem_body_text=tools.ustr(body.get('text', ''))
        )
        extra_headers = context.get('headers', {})
        # Try to send the e-mail from each allowed account
        # Only one mail is sent
        for account_id in ids:
            account = self.browse(cr, uid, account_id, context)
            # Update the sender address from account
            sender_name = account.name + " <" + account.email_id + ">"
            sender_name = parse_sender(
                pem_account=sender_name,
                pem_addresses=addresses_list
            )
            # If the account is a company account, update the header
            if account.user.company_id:
                extra_headers.update({
                    'Organitzation': account.user.company_id.name
                })
            elif 'Organitzation' in extra_headers:
                extra_headers.pop('Organitzation')
            # Use sender if debug is set
            sender = (Sender if config.get('debug_mode', False) else SMTPSender)
            with sender(
                host=account.smtpserver,
                port=account.smtpport,
                user=account.smtpuname,
                passwd=account.smtppass,
                tls=account.smtptls,
                ssl=account.smtpssl
            ):
                mail = Email()
                try:
                    mail = create_qreu(
                        headers=extra_headers, payload=payload,
                        **{
                            'subject': subject,
                            'from': sender_name,
                            'to': addresses_list.get('To', []),
                            'cc': addresses_list.get('CC', []),
                            'bcc': addresses_list.get('BCC', []),
                            'body_text': tools.ustr(body.get('text', '')),
                            'body_html': body_html
                        }
                    )
                except Exception as error:
                    logger.notifyChannel(
                        _("Power Email"), netsvc.LOG_ERROR,
                        _("Could not create mail \"{subject}\" "
                          "from Account \"{account.name}\".\n"
                          "Description: {error}").format(**locals())
                    )
                    return error
                try:
                    return mail.send()
                except Exception as error:
                    logger.notifyChannel(
                        _("Power Email"), netsvc.LOG_ERROR,
                        _("Sending mail from Account {} failed.\n"
                          "Description: {}").format(account_id, error)
                    )
                    # If error sending,
                    #  retry with another account if there is any
                    continue

    def extracttime(self, time_as_string):
        """
        TODO: DOC THis
        """
        logger = netsvc.Logger()
        #The standard email dates are of format similar to:
        #Thu, 8 Oct 2009 09:35:42 +0200
        #print time_as_string
        date_as_date = False
        convertor = {'+':1, '-':-1}
        try:
            time_as_string = time_as_string.replace(',', '')
            date_list = time_as_string.split(' ')
            date_temp_str = ' '.join(date_list[1:5])
            if len(date_list) >= 6:
                sign = convertor.get(date_list[5][0], False)
            else:
                sign = False
            try:
                dt = datetime.datetime.strptime(
                                            date_temp_str,
                                            "%d %b %Y %H:%M:%S")
            except:
                try:
                    dt = datetime.datetime.strptime(
                                            date_temp_str,
                                            "%d %b %Y %H:%M")
                except:
                    return False
            if sign:
                try:
                    offset = datetime.timedelta(
                                hours=sign * int(
                                             date_list[5][1:3]
                                                ),
                                             minutes=sign * int(
                                                            date_list[5][3:5]
                                                                )
                                                )
                except Exception as e2:
                    """Looks like UT or GMT, just forget decoding"""
                    return False
            else:
                offset = datetime.timedelta(hours=0)
            dt = dt + offset
            date_as_date = dt.strftime('%Y-%m-%d %H:%M:%S')
            #print date_as_date
        except Exception as e:
            logger.notifyChannel(
                    _("Power Email"),
                    netsvc.LOG_WARNING,
                    _(
                      "Datetime Extraction failed. Date: %s\nError: %s") % (
                                    time_as_string,
                                    e)
                      )
        return date_as_date

    def save_header(self, cr, uid, mail, coreaccountid, serv_ref, context=None):
        """
        TODO:DOC this
        """
        if context is None:
            context = {}
        #Internal function for saving of mail headers to mailbox
        #mail: eMail Object
        #coreaccounti: ID of poeremail core account
        logger = netsvc.Logger()
        mail_obj = self.pool.get('poweremail.mailbox')

        vals = {
            'pem_from':self.decode_header_text(mail['From']),
            'pem_to':mail['To'] and self.decode_header_text(mail['To']) or 'no recepient',
            'pem_cc':self.decode_header_text(mail['cc']),
            'pem_bcc':self.decode_header_text(mail['bcc']),
            'pem_recd':mail['date'],
            'date_mail':self.extracttime(mail['date']) or time.strftime("%Y-%m-%d %H:%M:%S"),
            'pem_subject':self.decode_header_text(mail['subject']),
            'server_ref':serv_ref,
            'folder':'inbox',
            'state':context.get('state', 'unread'),
            'pem_body_text':'Mail not downloaded...',
            'pem_body_html':'Mail not downloaded...',
            'pem_account_id':coreaccountid,
            'pem_message_id': mail['Message-Id'],
            'pem_mail_orig': str(mail)
            }
        #Identify Mail Type
        if mail.get_content_type() in self._known_content_types:
            vals['mail_type'] = mail.get_content_type()
        else:
            logger.notifyChannel(
                    _("Power Email"),
                    netsvc.LOG_WARNING,
                    _("Saving Header of unknown payload (%s) Account: %s.") % (
                                                      mail.get_content_type(),
                                                      coreaccountid)

                    )
        #Create mailbox entry in Mail
        crid = False
        try:
        #print vals
            crid = mail_obj.create(cr, uid, vals, context)
        except Exception as e:
            logger.notifyChannel(
                    _("Power Email"),
                    netsvc.LOG_ERROR,
                    _("Save Header -> Mailbox create error. Account: %s, Mail: %s, Error: %s") % (coreaccountid,
                                                     serv_ref, str(e)))
        #Check if a create was success
        if crid:
            logger.notifyChannel(
                    _("Power Email"),
                    netsvc.LOG_INFO,
                    _("Header for Mail %s Saved successfully as ID: %s for Account: %s.") % (serv_ref, crid, coreaccountid)
                    )
            crid = False
            return True
        else:
            logger.notifyChannel(
                    _("Power Email"),
                    netsvc.LOG_ERROR,
                    _("IMAP Mail -> Mailbox create error. Account: %s, Mail: %s") % (coreaccountid, serv_ref))

    def save_fullmail(self, cr, uid, mail, coreaccountid, serv_ref, context=None):
        """
        TODO: Doc this
        """
        if context is None:
            context = {}
        #Internal function for saving of mails to mailbox
        #mail: eMail Object
        #coreaccounti: ID of poeremail core account
        logger = netsvc.Logger()
        mail_obj = self.pool.get('poweremail.mailbox')
        # Check for existing mails
        message_id = mail['Message-ID'].strip()
        existing_mails = mail_obj.search(
            cr, uid, [
                ('pem_account_id', '=', coreaccountid),
                ('pem_message_id', '=', message_id)
            ]
        )
        if existing_mails:
            last_mail_id = self.read(
                cr, uid, coreaccountid, ['last_mail_id'])['last_mail_id']
            self.write(cr, uid, coreaccountid, {'last_mail_id': last_mail_id+1})
            return False
        # Use Qreu to parse email data (headers and text)
        parsed = Email.parse(mail.as_string())
        parsed_mail = self.get_payloads(parsed)
        vals = {
            'pem_from': parsed.from_.address,
            'pem_to': ','.join(parsed.to),
            'pem_cc': ','.join(parsed.cc),
            'pem_bcc': ','.join(parsed.bcc),
            'pem_recd':mail['date'],
            'date_mail':self.extracttime(
                            mail['date']
                                ) or time.strftime("%Y-%m-%d %H:%M:%S"),
            'pem_subject': parsed.subject,
            'server_ref':serv_ref,
            'folder':'inbox',
            'state':context.get('state', 'unread'),
            'pem_body_text': parsed_mail['text'],
            'pem_body_html': parsed_mail['html'],
            'pem_account_id':coreaccountid,
            'pem_message_id': message_id,
            'pem_mail_orig': six.text_type(parsed.mime_string, errors='ignore')
        }
        #Create the mailbox item now
        crid = False
        try:
            crid = mail_obj.create(cr, uid, vals, context)
        except Exception as e:
            logger.notifyChannel(
                    _("Power Email"),
                    netsvc.LOG_ERROR,
                    _("Save Header -> Mailbox create error. Account: %s, Mail: %s, Error: %s") % (
                                                    coreaccountid,
                                                    serv_ref,
                                                    str(e))
                                )
        #Check if a create was success
        if crid:
            logger.notifyChannel(
                    _("Power Email"),
                    netsvc.LOG_INFO,
                    _("Header for Mail %s Saved successfully as ID: %s for Account: %s.") % (serv_ref,
                                                  crid,
                                                  coreaccountid))
            # Commenting this code due to the attachments being created on
            #  mailbox's create, as we decode the email there with QREU's Email
            #If there are attachments save them as well
            # if parsed_mail['attachments']:
            #     self.save_attachments(cr, uid, mail, crid,
            #                           parsed_mail, coreaccountid, context)
            crid = False
            return True
        else:
            logger.notifyChannel(
                                 _("Power Email"),
                                 netsvc.LOG_ERROR,
                                 _("IMAP Mail -> Mailbox create error. Account: %s, Mail: %s") % (
                                                         coreaccountid,
                                                         mail[0].split()[0]))

    def complete_mail(self, cr, uid, mail, coreaccountid, serv_ref, mailboxref, context=None):
        if context is None:
            context = {}
        #Internal function for saving of mails to mailbox
        #mail: eMail Object
        #coreaccountid: ID of poeremail core account
        #serv_ref:Mail ID in the IMAP/POP server
        #mailboxref: ID of record in malbox to complete
        logger = netsvc.Logger()
        mail_obj = self.pool.get('poweremail.mailbox')
        parsed = Email.parse(mail.as_string())
        parsed_mail = self.get_payloads(parsed)
        vals = {
            'pem_from': parsed.from_.address,
            'pem_to': ','.join(parsed.to) or 'No Recipient',
            'pem_cc': ','.join(parsed.cc),
            'pem_bcc': ','.join(parsed.bcc),
            'pem_recd':mail['date'],
            'date_mail':time.strftime("%Y-%m-%d %H:%M:%S"),
            'pem_subject': parsed.subject,
            'server_ref':serv_ref,
            'folder':'inbox',
            'state':context.get('state', 'unread'),
            'pem_body_text': parsed_mail.get('text', ''),
            'pem_body_html': parsed_mail.get('html', ''),
            'pem_account_id':coreaccountid,
            'pem_message_id': mail['Message-Id'],
            'pem_mail_orig': six.text_type(parsed.mime_string, errors='ignore')
            }
        #Create the mailbox item now
        crid = False
        try:
            crid = mail_obj.write(cr, uid, mailboxref, vals, context)
        except Exception as e:
            logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("Save Mail -> Mailbox write error Account: %s, Mail: %s") % (coreaccountid, serv_ref))
        #Check if a create was success
        if crid:
            logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("Mail %s Saved successfully as ID: %s for Account: %s.") % (serv_ref, crid, coreaccountid))

            # Commenting this code due to the attachments being created on
            #  mailbox's create, as we decode the email there with QREU's Email
            # #If there are attachments save them as well
            # if parsed_mail['attachments']:
            #     self.save_attachments(cr, uid, mail, mailboxref, parsed_mail, coreaccountid, context)
            return True
        else:
            logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("IMAP Mail -> Mailbox create error Account: %s, Mail: %s") % (coreaccountid, mail[0].split()[0]))

    def save_attachments(self, cr, uid, mail, id, parsed_mail, coreaccountid, context=None):
        logger = netsvc.Logger()
        att_obj = self.pool.get('ir.attachment')
        mail_obj = self.pool.get('poweremail.mailbox')
        att_ids = []
        for each in parsed_mail['attachments']:#Get each attachment
            new_att_vals = {
                        'name':self.decode_header_text(mail['subject']) + '(' + each[0] + ')',
                        'datas':base64.b64encode(each[2] or ''),
                        'datas_fname':each[1],
                        'description':(self.decode_header_text(mail['subject']) or _('No Subject')) + " [Type:" + (each[0] or 'Unknown') + ", Filename:" + (each[1] or 'No Name') + "]",
                        'res_model':'poweremail.mailbox',
                        'res_id':id
                            }
            att_ids.append(att_obj.create(cr, uid, new_att_vals, context))
            logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("Downloaded & saved %s attachments Account: %s.") % (len(att_ids), coreaccountid))
            #Now attach the attachment ids to mail
            if mail_obj.write(cr, uid, id, {'pem_attachments_ids':[[6, 0, att_ids]]}, context):
                logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("Attachment to mail for %s relation success! Account: %s.") % (id, coreaccountid))
            else:
                logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("Attachment to mail for %s relation failed Account: %s.") % (id, coreaccountid))

    def get_mails(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        #The function downloads the mails from the POP3 or IMAP server
        #The headers/full mail download depends on settings in the account
        #IDS should be list of id of poweremail_coreaccounts
        logger = netsvc.Logger()
        #The Main reception function starts here
        for id in ids:
            logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("Starting Header reception for account: %s.") % (id))
            rec = self.browse(cr, uid, id, context)
            if rec:
                if rec.iserver and rec.isport and rec.isuser and rec.ispass :
                    if rec.iserver_type == 'imap' and rec.isfolder:
                        #Try Connecting to Server
                        serv = self._get_imap_server(cr, uid, rec)
                        logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("IMAP Server Connected & logged in successfully Account: %s.") % (id))
                        #Select IMAP folder
                        try:
                            typ, msg_count = serv.select('"%s"' % rec.isfolder)
                        except imaplib.IMAP4.error as error:
                            logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("IMAP Server Folder Selection Error Account: %s Error: %s.") % (id, error))
                            raise osv.except_osv(_('Power Email'), _('IMAP Server Folder Selection Error Account: %s Error: %s.\nCheck account settings if you have selected a folder.') % (id, error))
                        logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("IMAP Folder selected successfully Account:%s.") % (id))
                        logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("IMAP Folder Statistics for Account: %s: %s") % (id, serv.status('"%s"' % rec.isfolder, '(MESSAGES RECENT UIDNEXT UIDVALIDITY UNSEEN)')[1][0]))
                        #If there are newer mails than the ones in mailbox
                        #print int(msg_count[0]),rec.last_mail_id

                        msg_count = int(msg_count[0])

                        if rec.last_mail_id < msg_count:
                            for i in range(msg_count, rec.last_mail_id, -1):
                                if rec.rec_headers_den_mail:
                                    message_parts = '(FLAGS BODY[HEADER])'
                                    method = getattr(self, 'save_header')
                                else:
                                    message_parts = '(FLAGS BODY[])'
                                    method = getattr(self, 'save_fullmail')
                                typ, msg = serv.fetch(str(i), message_parts)

                                content = msg[0][1]
                                response = msg[0][0]
                                seq_id = response.split()[0]
                                mail = email.message_from_string(content)
                                ctx = context.copy()
                                if '\Seen' in response:
                                    ctx['state'] = 'read'
                                method(cr, uid, mail, id, seq_id, ctx)
                            # Always write downloaded messages
                            self.write(cr, uid, id, {
                                'last_mail_id': msg_count
                            }, context)

                        elif rec.last_mail_id > msg_count:
                            self.write(cr, uid, id, {'last_mail_id': msg_count - _MAIL_COUNT_MARGIN})

                        serv.close()
                        serv.logout()
                    elif rec.iserver_type == 'pop3':
                        #Try Connecting to Server
                        try:
                            if rec.isssl:
                                serv = poplib.POP3_SSL(rec.iserver, rec.isport)
                            else:
                                serv = poplib.POP3(rec.iserver, rec.isport)
                        except Exception as error:
                            logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("POP3 Server Error Account: %s Error: %s.") % (id, error))
                        #Try logging in to server
                        try:
                            serv.user(rec.isuser)
                            serv.pass_(rec.ispass)
                        except Exception as error:
                            logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("POP3 Server Login Error Account: %s Error: %s.") % (id, error))
                        logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("POP3 Server Connected & logged in successfully Account: %s.") % (id))
                        logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("POP3 Statistics: %s mails of %s size for Account: %s") % (serv.stat()[0], serv.stat()[1], id))
                        #If there are newer mails than the ones in mailbox
                        if rec.last_mail_id < serv.stat()[0]:
                            if rec.rec_headers_den_mail:
                                #Download Headers Only
                                for msgid in range(rec.last_mail_id + 1, serv.stat()[0] + 1):
                                    resp, msg, octet = serv.top(msgid, 20) #20 Lines from the content
                                    mail = email.message_from_string(string.join(msg, "\n"))
                                    if self.save_header(cr, uid, mail, id, msgid):#If saved succedfully then increment last mail recd
                                        self.write(cr, uid, id, {'last_mail_id':msgid}, context)
                            else:#Receive Full Mail first time itself
                                #Download Full RF822 Mails
                                for msgid in range(rec.last_mail_id + 1, serv.stat()[0] + 1):
                                    resp, msg, octet = serv.retr(msgid) #Full Mail
                                    mail = email.message_from_string(string.join(msg, "\n"))
                                    if self.save_header(cr, uid, mail, id, msgid):#If saved succedfully then increment last mail recd
                                        self.write(cr, uid, id, {'last_mail_id':msgid}, context)
                    else:
                        logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("Incoming server login attempt dropped Account: %s Check if Incoming server attributes are complete.") % (id))

    def get_fullmail(self, cr, uid, mailid, context):
        #The function downloads the full mail for which only header was downloaded
        #ID:of poeremail core account
        #context: should have mailboxref, the ID of mailbox record
        server_ref = self.pool.get(
                        'poweremail.mailbox'
                        ).read(cr, uid, mailid,
                               ['server_ref'],
                               context)['server_ref']
        id = self.pool.get(
                        'poweremail.mailbox'
                        ).read(cr, uid, mailid,
                               ['pem_account_id'],
                               context)['pem_account_id'][0]
        logger = netsvc.Logger()
        #The Main reception function starts here
        logger.notifyChannel(
                _("Power Email"),
                netsvc.LOG_INFO,
                _("Starting Full mail reception for mail: %s.") % (id))
        rec = self.browse(cr, uid, id, context)
        if rec:
            if rec.iserver and rec.isport and rec.isuser and rec.ispass :
                if rec.iserver_type == 'imap' and rec.isfolder:
                    #Try Connecting to Server
                    pw_core_obj = self.pool.get('poweremail.core_accounts')
                    serv = pw_core_obj._get_imap_server(cr, uid, rec)
                    logger.notifyChannel(
                                _("Power Email"),
                                netsvc.LOG_INFO,
                                _(
                        "IMAP Server Connected & logged in successfully Account: %s."
                                ) % (id))
                    #Select IMAP folder

                    try:
                        typ, msg_count = serv.select('"%s"' % rec.isfolder)#typ,msg_count: practically not used here
                    except imaplib.IMAP4.error as error:
                        logger.notifyChannel(
                                _("Power Email"),
                                netsvc.LOG_ERROR,
                                _(
                      "IMAP Server Folder Selection Error. Account: %s Error: %s."
                                  ) % (id, error))
                    logger.notifyChannel(
                                _("Power Email"),
                                netsvc.LOG_INFO,
                                _(
                      "IMAP Folder selected successfully Account: %s."
                                  ) % (id))
                    logger.notifyChannel(
                                _("Power Email"),
                                netsvc.LOG_INFO,
                                _(
                      "IMAP Folder Statistics for Account: %s: %s"
                                  ) % (
                           id,
                           serv.status(
                                '"%s"' % rec.isfolder,
                                '(MESSAGES RECENT UIDNEXT UIDVALIDITY UNSEEN)'
                                )[1][0])
                                  )
                    #If there are newer mails than the ones in mailbox
                    typ, msg = serv.fetch(str(server_ref), '(FLAGS RFC822)')
                    for i in range(0, len(msg) / 2):
                        mails = msg[i * 2]
                        flags = msg[(i * 2) + 1]
                        if type(mails) == type(('tuple', 'type')):
                            if '\Seen' in flags:
                                context['state'] = 'read'
                            mail = email.message_from_string(mails[1])
                            self.complete_mail(cr, uid, mail, id,
                                               server_ref, mailid, context)
                    serv.close()
                    serv.logout()
                elif rec.iserver_type == 'pop3':
                    #Try Connecting to Server
                    try:
                        if rec.isssl:
                            serv = poplib.POP3_SSL(
                                            rec.iserver,
                                            rec.isport
                                                )
                        else:
                            serv = poplib.POP3(
                                            rec.iserver,
                                            rec.isport
                                            )
                    except Exception as error:
                        logger.notifyChannel(
                            _("Power Email"),
                            netsvc.LOG_ERROR,
                            _(
                        "POP3 Server Error Account: %s Error: %s."
                            ) % (id, error))
                    #Try logging in to server
                    try:
                        serv.user(rec.isuser)
                        serv.pass_(rec.ispass)
                    except Exception as error:
                        logger.notifyChannel(
                                _("Power Email"),
                                netsvc.LOG_ERROR,
                                _(
                    "POP3 Server Login Error Account: %s Error: %s."
                                ) % (id, error))
                    logger.notifyChannel(
                                _("Power Email"),
                                netsvc.LOG_INFO,
                                _(
                    "POP3 Server Connected & logged in " \
                    "successfully Account: %s."
                                ) % (id))
                    logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("POP3 Statistics: %s mails of %s size for Account: %s:") % (serv.stat()[0], serv.stat()[1], id))
                    #Download Full RF822 Mails
                    resp, msg, octet = serv.retr(server_ref) #Full Mail
                    mail = email.message_from_string(string.join(msg, "\n"))
                    self.complete_mail(cr, uid, mail, id,
                                       server_ref, mailid, context)
                else:
                    logger.notifyChannel(
                        _("Power Email"),
                        netsvc.LOG_ERROR,
                        _(
                        "Incoming server login attempt dropped Account: %s\nCheck if Incoming server attributes are complete."
                        ) % (id))

    def send_receive(self, cr, uid, ids, context=None):
        self.get_mails(cr, uid, ids, context)
        for id in ids:
            ctx = context.copy()
            ctx['filters'] = [('pem_account_id', '=', id)]
            self.pool.get('poweremail.mailbox').send_all_mail(cr, uid, [], context=ctx)
        return True

    def get_payloads(self, parsed_mail):
        """
        Parse the Email with qreu's Email and return a dict with:
        - 'text': body_text
        - 'html': body_html
        - 'attachments': [attachments]
        """
        parts = parsed_mail.body_parts
        attachments = [
            (v['type'], v['name'], v['content'])
            for v in parsed_mail.attachments
        ]
        body_text = parts.get('plain', '')
        if not body_text:
            body_text = html2text(parts.get('html', ''))
        return {
            'text': body_text,
            'html': parts.get('html', ''),
            'attachments': attachments,
        }

    def decode_header_text(self, text):
        """ Decode internationalized headers RFC2822.
            To, CC, BCC, Subject fields can contain
            text slices with different encodes, like:
                =?iso-8859-1?Q?Enric_Mart=ED?= <enricmarti@company.com>,
                =?Windows-1252?Q?David_G=F3mez?= <david@company.com>
            Sometimes they include extra " character at the beginning/
            end of the contact name, like:
                "=?iso-8859-1?Q?Enric_Mart=ED?=" <enricmarti@company.com>
            and decode_header() does not work well, so we use regular
            expressions (?=   ? ?   ?=) to split the text slices
        """
        if not text:
            return text
        p = re.compile("(=\?.*?\?.\?.*?\?=)")
        text2 = ''
        try:
            for t2 in p.split(text):
                text2 += ''.join(
                            [s.decode(
                                      t or 'ascii'
                                    ) for (s, t) in decode_header(t2)]
                                ).encode('utf-8')
        except:
            return text
        return text2

poweremail_core_accounts()


class PoweremailSelectFolder(osv.osv_memory):
    _name = "poweremail.core_selfolder"
    _description = "Shows a list of IMAP folders"

    def makereadable(self, imap_folder):
        if imap_folder:
	    # We consider imap_folder may be in one of the following formats:
	    # A string like this: '(\HasChildren) "/" "INBOX"'
	    # Or a tuple like this: ('(\\HasNoChildren) "/" {18}', 'INBOX/contacts')
            if isinstance(imap_folder, tuple):
                return imap_folder[1]
            result = re.search(
                        r'(?:\([^\)]*\)\s\")(.)(?:\"\s)(?:\")?([^\"]*)(?:\")?',
                        imap_folder)
            seperator = result.groups()[0]
            folder_readable_name = ""
            splitname = result.groups()[1].split(seperator) #Not readable now
            #If a parent and child exists, format it as parent/child/grandchild
            if len(splitname) > 1:
                for i in range(0, len(splitname) - 1):
                    folder_readable_name = splitname[i] + '/'
                folder_readable_name = folder_readable_name + splitname[-1]
            else:
                folder_readable_name = result.groups()[1].split(seperator)[0]
            return folder_readable_name
        return False

    def _get_folders(self, cr, uid, context=None):
        if 'active_ids' in context.keys():
            pw_acc_obj = self.pool.get('poweremail.core_accounts')
            record = pw_acc_obj.browse(cr, uid, context['active_ids'][0], context)
            if record:
                folderlist = []
                serv = pw_acc_obj._get_imap_server(cr, uid, record)
                try:
                    for folders in serv.list()[1]:
                        folder_readable_name = self.makereadable(folders)
                        if isinstance(folders, tuple):
                            data = folders[0] + folders[1]
                        else:
                            data = folders
                        if data.find('Noselect') == -1: #If it is a selectable folder
                            if folder_readable_name:
                                folderlist.append(
                                                  (folder_readable_name,
                                                   folder_readable_name)
                                                  )
                        if folder_readable_name == 'INBOX':
                            self.inboxvalue = folder_readable_name
                except imaplib.IMAP4.error as error:
                    raise osv.except_osv(_("IMAP Server Folder Error"),
                                         _("An error occurred: %s") % error)
                except Exception as error:
                    raise osv.except_osv(_("IMAP Server Folder Error"),
                                         _("An error occurred: %s") % error)
            else:
                folderlist = [('invalid', 'Invalid')]
        else:
            folderlist = [('invalid', 'Invalid')]
        return folderlist

    _columns = {
        'name':fields.many2one(
                        'poweremail.core_accounts',
                        string='Email Account',
                        readonly=True),
        'folder':fields.selection(
                        _get_folders,
                        string="IMAP Folder"),
    }

    _defaults = {
        'name':lambda self, cr, uid, ctx: ctx['active_ids'][0],
        'folder': lambda self, cr, uid, ctx:self.inboxvalue
    }

    def sel_folder(self, cr, uid, ids, context=None):
        """
        TODO: Doc This
        """
        if self.read(cr, uid, ids, ['folder'], context)[0]['folder']:
            if not self.read(cr, uid, ids,
                             ['folder'], context)[0]['folder'] == 'invalid':
                self.pool.get(
                        'poweremail.core_accounts'
                            ).write(cr, uid, context['active_ids'][0],
                                    {
                                     'isfolder':self.read(cr, uid, ids,
                                                  ['folder'],
                                                  context)[0]['folder']
                                    })
                return {
                        'type':'ir.actions.act_window_close'
                        }
            else:
                raise osv.except_osv(
                                     _("Folder Error"),
                                     _("This is an invalid folder"))
        else:
            raise osv.except_osv(
                                 _("Folder Error"),
                                 _("Select a folder before you save record"))
PoweremailSelectFolder()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
