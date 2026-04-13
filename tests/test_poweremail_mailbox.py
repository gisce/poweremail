# coding=utf-8
import base64
import hmac
import hashlib

import six
if six.PY2:
    from mock import MagicMock, PropertyMock, patch, Mock
else:
    from unittest.mock import MagicMock, PropertyMock, patch, Mock
from destral import testing
from destral.transaction import Transaction


class TestPoweremailMailbox(testing.OOTestCase):

    def create_account(self, cursor, uid, extra_vals=None):
        acc_obj = self.openerp.pool.get('poweremail.core_accounts')
        imd_obj = self.openerp.pool.get('ir.model.data')

        acc_id = imd_obj.get_object_reference(cursor, uid, 'poweremail', 'info_energia_from_email')[1]

        if not extra_vals:
            return acc_id

        return acc_obj.copy(cursor, uid, acc_id, extra_vals)

    def create_false_account(self, cursor, uid, extra_vals=None):
        vals = {
            'smtpserver': '',
            'smtpport': 0,
        }
        if extra_vals:
            vals.update(extra_vals)
        return self.create_account(cursor, uid, extra_vals=vals)

    def create_template(self, cursor, uid, extra_vals=None):
        if extra_vals is None:
            extra_vals = {}

        imd_obj = self.openerp.pool.get('ir.model.data')
        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        acc_id = False
        if 'enforce_from_account' not in extra_vals:
            acc_id = self.create_account(cursor, uid)

        model_partner = imd_obj.get_object_reference(
            cursor, uid, 'base', 'model_res_partner'
        )[1]

        vals = {
            'name': 'Test template',
            'object_name': model_partner,
            'enforce_from_account': acc_id,
            'template_language': 'mako',
            'def_priority': '2'
        }
        if extra_vals:
            vals.update(extra_vals)

        tmpl_id = tmpl_obj.create(cursor, uid, vals)
        return tmpl_id

    def test_poweremail_n_mails_per_batch(self, extra_vals=None):
        self.openerp.install_module('base_extended')

        with Transaction().start(self.database) as txn:
            cursor = txn.cursor
            uid = txn.user
            mail_o = self.openerp.pool.get('poweremail.mailbox')
            varconf_o = self.openerp.pool.get('res.config')
            imd_obj = self.openerp.pool.get('ir.model.data')
            tmpl_id = self.create_template(cursor, uid)
            tmpl_obj = self.openerp.pool.get('poweremail.templates')

            partner_id = imd_obj.get_object_reference(
                cursor, uid, 'base', 'res_partner_asus'
            )[1]
            template = tmpl_obj.browse(cursor, uid, tmpl_id)
            for i in range(3):
                mail_id = tmpl_obj._generate_mailbox_item_from_template(
                    cursor, uid, template, partner_id
                )
                mail_wv = {'folder': 'outbox', 'state': 'na'}
                mail_o.write(cursor, uid, mail_id, mail_wv)

            varconf_o.set(cursor, uid, 'poweremail_n_mails_per_batch', 1)
            mails_per_enviar = mail_o._get_mails_to_send(cursor, uid)
            self.assertEqual(len(mails_per_enviar), 1)
            mails_per_enviar = mail_o._get_mails_to_send(cursor, uid, context={'limit': 2})
            self.assertEqual(len(mails_per_enviar), 2)

            varconf_o.set(cursor, uid, 'poweremail_n_mails_per_batch', 0)
            mails_per_enviar = mail_o._get_mails_to_send(cursor, uid)
            self.assertEqual(len(mails_per_enviar), 3)

    def test_poweremail_n_mails_per_batch_per_account(self, extra_vals=None):
        if extra_vals is None:
            extra_vals = {}
        self.openerp.install_module('base_extended')

        with Transaction().start(self.database) as txn:
            cursor = txn.cursor
            uid = txn.user
            mail_o = self.openerp.pool.get('poweremail.mailbox')
            varconf_o = self.openerp.pool.get('res.config')
            imd_obj = self.openerp.pool.get('ir.model.data')
            tmpl_obj = self.openerp.pool.get('poweremail.templates')

            acc1_id = self.create_account(cursor, uid, extra_vals={'name': 'acc1', 'email_id': 'test1@example.com'})
            acc2_id = self.create_account(cursor, uid, extra_vals={'name': 'acc2', 'email_id': 'test2@example.com'})
            acc3_id = self.create_account(cursor, uid, extra_vals={'name': 'acc3', 'email_id': 'test3@example.com'})

            tmpl1_id = self.create_template(cursor, uid, extra_vals={'enforce_from_account': acc1_id, 'name': 'Test template 1'})
            tmpl2_id = self.create_template(cursor, uid, extra_vals={'enforce_from_account': acc2_id, 'name': 'Test template 2'})
            tmpl3_id = self.create_template(cursor, uid, extra_vals={'enforce_from_account': acc3_id, 'name': 'Test template 3'})

            partner_id = imd_obj.get_object_reference(
                cursor, uid, 'base', 'res_partner_asus'
            )[1]
            mails_per_acc = {'acc1': set(), 'acc2': set(), 'acc3': set()}
            for tmpl_id in (tmpl1_id, tmpl2_id, tmpl3_id):
                template = tmpl_obj.browse(cursor, uid, tmpl_id)
                for i in range(3):
                    mail_id = tmpl_obj._generate_mailbox_item_from_template(
                        cursor, uid, template, partner_id
                    )
                    mail_wv = {'folder': 'outbox', 'state': 'na'}
                    mail_o.write(cursor, uid, mail_id, mail_wv)
                    mails_per_acc[template.enforce_from_account.name].add(mail_id)

            varconf_o.set(
                cursor, uid, 'poweremail_n_mails_per_batch_per_account',
                "{'acc1': 1, 'acc2': 2}"
            )
            mails_per_enviar = mail_o._get_mails_to_send(cursor, uid)
            self.assertEqual(len(mails_per_enviar), 6)  # 1 + 2 + 3
            self.assertEqual(len(set(mails_per_enviar) - mails_per_acc['acc1']), 5)
            self.assertEqual(len(set(mails_per_enviar) - mails_per_acc['acc2']), 4)
            self.assertEqual(len(set(mails_per_enviar) - mails_per_acc['acc3']), 3)
            mails_per_enviar = mail_o._get_mails_to_send(cursor, uid, context={'limit': 2})
            self.assertEqual(len(mails_per_enviar), 2)

            varconf_o.set(
                cursor, uid, 'poweremail_n_mails_per_batch_per_account',
                "{'acc1': 1, 'acc2': 1, 'acc3': 1}"
            )
            mails_per_enviar = mail_o._get_mails_to_send(cursor, uid)
            self.assertEqual(len(mails_per_enviar), 3)
            for acc, mails in mails_per_acc.items():
                self.assertEqual(len(set(mails_per_enviar) - mails), 2)

            varconf_o.set(
                cursor, uid, 'poweremail_n_mails_per_batch_per_account',
                "{}"
            )
            mails_per_enviar = mail_o._get_mails_to_send(cursor, uid)
            self.assertEqual(len(mails_per_enviar), 9)

    def generate_mail_with_attachments_no_report(self):
        with Transaction().start(self.database) as txn:
            uid = txn.user
            cursor = txn.cursor
            mailbox_obj = self.openerp.pool.get('poweremail.mailbox')
            pm_tmp_obj = self.openerp.pool.get('poweremail.templates')
            ir_attachment_obj = self.openerp.pool.get('ir.attachment')
            imd_obj = self.openerp.pool.get('ir.model.data')
            pw_account_obj = self.openerp.pool.get('poweremail.core_accounts')

            # Agafem un template de prova per posar a l'attachment
            template_id = imd_obj.get_object_reference(
                cursor, uid, 'poweremail', 'default_template_poweremail'
            )[1]

            # Hem de posar 'enforce_from_account' al template perque és required
            pw_account_id = pw_account_obj.create(cursor, uid, {
                'name': 'test',
                'user': 1,
                'email_id': 'test@email',
                'smtpserver': 'smtp.gmail.com',
                'smtpport': '587',
                'company': 'no',
                'state': 'approved',
            })

            # Escribim al template el que necessitem
            pm_tmp_obj.write(cursor, uid, template_id, {'enforce_from_account': pw_account_id})

            # Creem un attachment de prova
            ir_vals = {
                'name': 'filename_prova',
                'datas': base64.b64encode(b'attachment test content'),
                'datas_fname': 'filename_prova.txt',
                'res_model': 'poweremail.templates',
                'res_id': template_id,
            }
            attachment_id = ir_attachment_obj.create(cursor, uid, ir_vals)

            # Busquem els attachments que hi ha creats i hauriem de trobar el que acabem de crear
            attach_ids = ir_attachment_obj.search(cursor, uid, [])
            self.assertEqual(len(attach_ids), 1)
            self.assertIn(attachment_id, attach_ids)

            # Cridem el mètode per generar el mail a partir del template que té un attachment.
            # Ens hauria de crear un segon attachment al crear el poweremail.mailbox
            pm_tmp_obj.generate_mail(cursor, uid, template_id, [template_id])

            attach_ids = ir_attachment_obj.search(cursor, uid, [])
            self.assertEqual(len(attach_ids), 2)

    @patch('poweremail.poweremail_template.poweremail_templates.create_report')
    def generate_mail_with_attachments_and_report(self, mock_function):
        with Transaction().start(self.database) as txn:
            uid = txn.user
            cursor = txn.cursor
            mailbox_obj = self.openerp.pool.get('poweremail.mailbox')
            pm_tmp_obj = self.openerp.pool.get('poweremail.templates')
            ir_attachment_obj = self.openerp.pool.get('ir.attachment')
            imd_obj = self.openerp.pool.get('ir.model.data')
            pw_account_obj = self.openerp.pool.get('poweremail.core_accounts')

            mock_function.return_value = ("Result", "provapdf")

            # Agafem un template de prova per posar a l'attachment
            template_id = imd_obj.get_object_reference(
                cursor, uid, 'poweremail', 'default_template_poweremail'
            )[1]

            # Hem de posar 'enforce_from_account' al template perque és required
            pw_account_id = pw_account_obj.create(cursor, uid, {
                'name': 'test',
                'user': 1,
                'email_id': 'test@email',
                'smtpserver': 'smtp.gmail.com',
                'smtpport': '587',
                'company': 'no',
                'state': 'approved',
            })

            # Agafem un report de demo
            report_id = imd_obj.get_object_reference(
                cursor, uid, 'base', 'report_test'
            )[1]

            # Escribim el que necessitem al template
            template_vals = {
                'enforce_from_account': pw_account_id,
                'report_template': report_id
            }
            pm_tmp_obj.write(cursor, uid, template_id, template_vals)

            # Creem un attachment de prova
            ir_vals = {
                'name': 'filename_prova',
                'datas': base64.b64encode(b'attachment test content'),
                'datas_fname': 'filename_prova.txt',
                'res_model': 'poweremail.templates',
                'res_id': template_id,
            }
            attachment_id = ir_attachment_obj.create(cursor, uid, ir_vals)

            # Busquem els attachments que hi ha creats i hauriem de trobar el que acabem de crear
            attach_ids = ir_attachment_obj.search(cursor, uid, [])
            self.assertEqual(len(attach_ids), 1)
            self.assertIn(attachment_id, attach_ids)

            # Cridem el mètode per generar el mail a partir del template que té un attachment i un report.
            # Ens hauria de crear un segon attachment al crear el poweremail.mailbox
            # I també ens hauria de crear un tercer attachment que és el report
            pm_tmp_obj.generate_mail(cursor, uid, template_id, [template_id])

            attach_ids = ir_attachment_obj.search(cursor, uid, [])
            self.assertEqual(len(attach_ids), 3)

    @patch('poweremail.poweremail_template.poweremail_templates.create_report')
    def generate_mail_with_report_no_attachments(self, mock_function):
        with Transaction().start(self.database) as txn:
            uid = txn.user
            cursor = txn.cursor
            mailbox_obj = self.openerp.pool.get('poweremail.mailbox')
            pm_tmp_obj = self.openerp.pool.get('poweremail.templates')
            ir_attachment_obj = self.openerp.pool.get('ir.attachment')
            imd_obj = self.openerp.pool.get('ir.model.data')
            pw_account_obj = self.openerp.pool.get('poweremail.core_accounts')

            mock_function.return_value = ("Result", "provapdf")

            # Agafem un template de prova per posar a l'attachment
            template_id = imd_obj.get_object_reference(
                cursor, uid, 'poweremail', 'default_template_poweremail'
            )[1]

            # Hem de posar 'enforce_from_account' al template perque és required
            pw_account_id = pw_account_obj.create(cursor, uid, {
                'name': 'test',
                'user': 1,
                'email_id': 'test@email',
                'smtpserver': 'smtp.gmail.com',
                'smtpport': '587',
                'company': 'no',
                'state': 'approved',
            })

            # Agafem un report de demo
            report_id = imd_obj.get_object_reference(
                cursor, uid, 'base', 'report_test'
            )[1]

            # Escribim el que necessitem al template
            template_vals = {
                'enforce_from_account': pw_account_id,
                'report_template': report_id
            }
            pm_tmp_obj.write(cursor, uid, template_id, template_vals)

            # Busquem els attachments que hi ha creats i no n'hi hauria d'haver cap
            attach_ids = ir_attachment_obj.search(cursor, uid, [])
            self.assertEqual(len(attach_ids), 0)

            # Cridem el mètode per generar el mail a partir del template que té no té attachments però té un report.
            # Ens hauria de crear un attachment que és el report
            pm_tmp_obj.generate_mail(cursor, uid, template_id, [template_id])

            attach_ids = ir_attachment_obj.search(cursor, uid, [])
            self.assertEqual(len(attach_ids), 1)

    @patch('poweremail.poweremail_template.poweremail_templates.create_report')
    def generate_mail_with_attachments_and_report_multi_users(self, mock_function):
        with Transaction().start(self.database) as txn:
            uid = txn.user
            cursor = txn.cursor
            mailbox_obj = self.openerp.pool.get('poweremail.mailbox')
            pm_tmp_obj = self.openerp.pool.get('poweremail.templates')
            ir_attachment_obj = self.openerp.pool.get('ir.attachment')
            imd_obj = self.openerp.pool.get('ir.model.data')
            pw_account_obj = self.openerp.pool.get('poweremail.core_accounts')

            mock_function.return_value = ("Result", "provapdf")

            # Agafem un template de prova per posar a l'attachment
            template_id = imd_obj.get_object_reference(
                cursor, uid, 'poweremail', 'default_template_poweremail'
            )[1]

            # Hem de posar 'enforce_from_account' al template perque és required
            pw_account_id = pw_account_obj.create(cursor, uid, {
                'name': 'test',
                'user': 1,
                'email_id': 'test@email',
                'smtpserver': 'smtp.gmail.com',
                'smtpport': '587',
                'company': 'no',
                'state': 'approved',
            })

            # Agafem un report de demo
            report_id = imd_obj.get_object_reference(
                cursor, uid, 'base', 'report_test'
            )[1]

            # Escribim el que necessitem als templates
            template_vals = {
                'enforce_from_account': pw_account_id,
                'report_template': report_id
            }
            pm_tmp_obj.write(cursor, uid, template_id, template_vals)


            # Creem dos attachments de prova
            ir_vals = {
                'name': 'filename_prova_1',
                'datas': base64.b64encode(b'attachment test content'),
                'datas_fname': 'filename_prova.txt',
                'res_model': 'poweremail.templates',
                'res_id': template_id,
            }
            attachment_id = ir_attachment_obj.create(cursor, uid, ir_vals)

            ir_vals_2 = {
                'name': 'filename_prova_2',
                'datas': base64.b64encode(b'attachment test content'),
                'datas_fname': 'filename_prova.txt',
                'res_model': 'poweremail.templates',
                'res_id': template_id,
            }
            attachment_id_2 = ir_attachment_obj.create(cursor, uid, ir_vals_2)

            # Busquem els attachments que hi ha creats i hauriem de trobar els que acabem de crear
            attach_ids = ir_attachment_obj.search(cursor, uid, [])
            self.assertEqual(len(attach_ids), 2)
            self.assertIn(attachment_id, attach_ids)
            self.assertIn(attachment_id_2, attach_ids)

            # Cridem el mètode per generar el mail a partir dels templates que tenen un attachment i un report.
            # Ens hauria de crear un segon attachment al crear el poweremail.mailbox
            # I també ens hauria de crear un tercer attachment que és el report
            pm_tmp_obj.generate_mail(cursor, uid, template_id, [template_id])

            attach_ids = ir_attachment_obj.search(cursor, uid, [])
            self.assertEqual(len(attach_ids), 5)

    @patch('poweremail.poweremail_send_wizard.poweremail_send_wizard.add_template_attachments')
    @patch('poweremail.poweremail_send_wizard.poweremail_send_wizard.add_attachment_documents')
    @patch('poweremail.poweremail_send_wizard.poweremail_send_wizard.process_extra_attachment_in_template')
    @patch('poweremail.poweremail_send_wizard.poweremail_send_wizard.create_report_attachment')
    @patch('poweremail.poweremail_send_wizard.poweremail_send_wizard.create_mail')
    def test_save_to_mailbox(self, mock_function, mock_function_2, mock_function_3, mock_function_4, mock_function_5):
        with Transaction().start(self.database) as txn:
            uid = txn.user
            cursor = txn.cursor
            mailbox_obj = self.openerp.pool.get('poweremail.mailbox')
            pm_tmp_obj = self.openerp.pool.get('poweremail.templates')
            ir_attachment_obj = self.openerp.pool.get('ir.attachment')
            imd_obj = self.openerp.pool.get('ir.model.data')
            pw_account_obj = self.openerp.pool.get('poweremail.core_accounts')
            send_wizard_obj = self.openerp.pool.get('poweremail.send.wizard')

            # Dummy value for an invoice id
            fact_id = 6
            # Agafem un template de prova per posar a l'attachment
            template_id = imd_obj.get_object_reference(
                cursor, uid, 'poweremail', 'default_template_poweremail'
            )[1]

            # Creem un wizard 'poweremail_send_wizard'
            body_text = "<!doctype html>" \
                        "<html>" \
                        "<head></head>" \
                        "<body>" \
                        "Querid@ Agrolait,<br/>" \
                        "<br/>" \
                        "El importe de su factura de electricidad que comprende el periodo del <B>2021/06/01</B> al <B>2021/06/30</B> es de <B> 14.54€</B>.<br/>" \
                        "<br/>" \
                        "Por favor, encuentre adjunta la factura en formato PDF.<br/>" \
                        "<br/>" \
                        "<br/>" \
                        "Atentamente,<br/>" \
                        "<br/>" \
                        "Tiny sprl" \
                        "</body>" \
                        "</html>"

            wizard_vals = {
                'rel_model_ref': fact_id,
                'requested': 1,
                'from': 1,
                'attachment_ids': [],
                'body_text': body_text,
                'cc' : False,
                'body_html': False,
                'bcc': False,
                'priority': '1',
                'to': 'aorellana@gisce.net',
                'state': 'single',
                'ref_template': template_id,
                'single_email': 0,
                'rel_model': 301,
                'signature': 0,
                'report': False,
                'subject': 'Factura electricidad False',
                'generated': False,
                'full_success': False,
            }

            # Creem un mailbox
            wizard_id = send_wizard_obj.create(cursor, uid, wizard_vals)

            # Hem de posar 'enforce_from_account' al template perque és required
            pw_account_id = pw_account_obj.create(cursor, uid, {
                'name': 'test',
                'user': 1,
                'email_id': 'test@email',
                'smtpserver': 'smtp.gmail.com',
                'smtpport': '587',
                'company': 'no',
                'state': 'approved',
            })

            # Agafem un report de demo
            report_id = imd_obj.get_object_reference(
                cursor, uid, 'base', 'report_test'
            )[1]

            # Escribim el que necessitem als templates
            template_vals = {
                'enforce_from_account': pw_account_id,
                'report_template': report_id
            }
            pm_tmp_obj.write(cursor, uid, template_id, template_vals)

            # Creem un attachments de prova
            ir_vals = {
                'name': 'filename_prova_1',
                'datas': base64.b64encode(b'attachment test content'),
                'datas_fname': 'filename_prova.txt',
                'res_model': 'poweremail.templates',
                'res_id': template_id,
            }
            attachment_id = ir_attachment_obj.create(cursor, uid, ir_vals)

            mail_vals = {
                'pem_from': 'test@email',
                'pem_to': 'aorellana@gisce.net',
                'pem_cc': False,
                'pem_bcc': False,
                'pem_subject': 'Factura electricidad False',
                'pem_body_text': body_text,
                'pem_body_html': False,
                'pem_account_id': 1,
                'priority': '1',
                'state': 'na',
                'mail_type': 'multipart/alternative'
            }

            mail_id = mailbox_obj.create(cursor, uid, mail_vals)

            attach_vals = {
                'name': 'Factura electricidad False(adjunto correo electrónico)',
                'datas': "datas_test",
                'datas_fname': "False.pdf",
                'description': body_text,
                'res_model': 'poweremail.mailbox',
                'res_id': mail_id
            }
            attachment_report_id = ir_attachment_obj.create(cursor, uid, attach_vals)

            mock_function.return_value = mail_id
            mock_function_2.return_value = attachment_report_id
            mock_function_3.return_value = []
            mock_function_4.return_value = []
            mock_function_5.return_value = [attachment_id]

            context = {}
            context['template_id'] = template_id
            context['lang'] = False
            context['src_rec_id'] = fact_id
            context['tz'] = False
            context['src_rec_ids'] = [fact_id]
            context['active_ids'] = [fact_id]
            context['type'] = 'out_invoice'
            context['template_id'] = template_id
            context['active_id'] = fact_id

            mail_ids = send_wizard_obj.save_to_mailbox(cursor, uid, [wizard_id], context=context)
            mail_created_vals = mailbox_obj.read(cursor, uid, mail_ids[0], [])
            self.assertEqual(len(mail_created_vals['pem_attachments_ids']), 2)
            self.assertIn(attachment_report_id, mail_created_vals['pem_attachments_ids'])
            self.assertIn(attachment_id, mail_created_vals['pem_attachments_ids'])

    def test_save_to_mailbox_inlining(self):
        with Transaction().start(self.database) as txn:
            uid = txn.user
            cursor = txn.cursor
            mailbox_obj = self.openerp.pool.get('poweremail.mailbox')
            pm_tmp_obj = self.openerp.pool.get('poweremail.templates')
            imd_obj = self.openerp.pool.get('ir.model.data')
            pw_account_obj = self.openerp.pool.get('poweremail.core_accounts')
            send_wizard_obj = self.openerp.pool.get('poweremail.send.wizard')

            # Dummy value for an invoice id
            fact_id = 6
            # Agafem un template de prova per posar a l'attachment
            template_id = imd_obj.get_object_reference(
                cursor, uid, 'poweremail', 'default_template_poweremail'
            )[1]

            # Creem un wizard 'poweremail_send_wizard'
            body_text = """
<html>
<style type="text/css">
h1 { border:1px solid black }
p { color:red;}
</style>
<h1 style="font-weight:bolder">Peter</h1>
<p>Hej</p>
</html>
            """

            wizard_vals = {
                'rel_model_ref': fact_id,
                'requested': 1,
                'from': 1,
                'attachment_ids': [],
                'body_text': body_text,
                'cc': False,
                'body_html': False,
                'bcc': False,
                'priority': '1',
                'to': 'example@example.org',
                'state': 'single',
                'ref_template': template_id,
                'single_email': 0,
                'rel_model': 301,
                'signature': False,
                'report': False,
                'subject': 'Factura electricidad False',
                'generated': False,
                'full_success': False,
            }

            # Creem un mailbox
            wizard_id = send_wizard_obj.create(cursor, uid, wizard_vals)

            pw_account_id = pw_account_obj.create(cursor, uid, {
                'name': 'test',
                'user': 1,
                'email_id': 'test@email',
                'smtpserver': 'smtp.gmail.com',
                'smtpport': '587',
                'company': 'no',
                'state': 'approved',
            })

            # Escribim el que necessitem als templates
            template_vals = {
                'enforce_from_account': pw_account_id,
                'inline': True
            }
            pm_tmp_obj.write(cursor, uid, template_id, template_vals)

            mail_vals = {
                'pem_from': 'test@email',
                'pem_to': 'example@example.org',
                'pem_cc': False,
                'pem_bcc': False,
                'pem_subject': 'Factura electricidad False',
                'pem_body_text': body_text,
                'pem_body_html': False,
                'pem_account_id': 1,
                'priority': '1',
                'state': 'na',
            }

            mailbox_obj.create(cursor, uid, mail_vals)

            context = {}
            context['template_id'] = template_id
            context['lang'] = False
            context['src_rec_id'] = fact_id
            context['tz'] = False
            context['src_rec_ids'] = [fact_id]
            context['active_ids'] = [fact_id]
            context['type'] = 'out_invoice'
            context['active_id'] = fact_id

            inlined_html = '<html>\n<head></head>\n<body>\n<h1 style="border:1px solid black; font-weight:bolder">Peter</h1>\n<p style="color:red">Hej</p>\n</body>\n</html>\n'

            mail_ids = send_wizard_obj.save_to_mailbox(cursor, uid, [wizard_id], context=context)
            pem_body_text = mailbox_obj.read(cursor, uid, mail_ids[0], ['pem_body_text'])['pem_body_text']
            self.assertEqual(pem_body_text, inlined_html)

    @patch('poweremail.poweremail_mailbox.netsvc.Logger')
    @patch('poweremail.poweremail_core.poweremail_core_accounts.send_mail')
    def test_send_this_mail_exception_logs_error(self, mock_send_mail, mock_logger):
        """Test that when send_this_mail raises an exception, the error is logged"""
        with Transaction().start(self.database) as txn:
            cursor = txn.cursor
            uid = txn.user
            mailbox_obj = self.openerp.pool.get('poweremail.mailbox')
            
            # Create an account
            acc_id = self.create_account(cursor, uid)
            
            # Create a mail in outbox
            mail_vals = {
                'pem_from': 'test@example.com',
                'pem_to': 'recipient@example.com',
                'pem_subject': 'Test email',
                'pem_body_text': 'Test body',
                'pem_account_id': acc_id,
                'folder': 'outbox',
                'state': 'na',
            }
            mail_id = mailbox_obj.create(cursor, uid, mail_vals)
            
            # Mock send_mail to raise an exception
            mock_send_mail.side_effect = Exception("Connection refused")
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance
            
            # Send the mail
            mailbox_obj.send_this_mail(cursor, uid, [mail_id])
            
            # Verify that the logger was called with the error
            mock_logger_instance.notifyChannel.assert_called_once()
            call_args = mock_logger_instance.notifyChannel.call_args
            self.assertIn("Power Email", call_args[0])
            self.assertIn("Connection refused", str(call_args[0]))
            
            # Verify the mail was moved to error folder
            mail = mailbox_obj.read(cursor, uid, mail_id, ['folder', 'history'])
            self.assertEqual(mail['folder'], 'error')
            
            # Verify error is in history
            self.assertIn('Traceback', mail['history'])

    @patch('poweremail.poweremail_core.poweremail_core_accounts.send_mail')
    def test_send_this_mail_failure_historises_error(self, mock_send_mail):
        """Test that when send_mail returns an error message, it's historised"""
        with Transaction().start(self.database) as txn:
            cursor = txn.cursor
            uid = txn.user
            mailbox_obj = self.openerp.pool.get('poweremail.mailbox')
            
            # Create an account
            acc_id = self.create_account(cursor, uid)
            
            # Create a mail in outbox
            mail_vals = {
                'pem_from': 'test@example.com',
                'pem_to': 'recipient@example.com',
                'pem_subject': 'Test email',
                'pem_body_text': 'Test body',
                'pem_account_id': acc_id,
                'folder': 'outbox',
                'state': 'na',
            }
            mail_id = mailbox_obj.create(cursor, uid, mail_vals)
            
            # Mock send_mail to return an error message (not True)
            error_message = "SMTP authentication failed"
            mock_send_mail.return_value = error_message
            
            # Send the mail
            mailbox_obj.send_this_mail(cursor, uid, [mail_id])
            
            # Verify the mail was moved to error folder
            mail = mailbox_obj.read(cursor, uid, mail_id, ['folder', 'history', 'state'])
            self.assertEqual(mail['folder'], 'error')
            self.assertEqual(mail['state'], 'na')
            
            # Verify error message is in history
            self.assertIn(error_message, mail['history'])

    @patch('poweremail.poweremail_core.poweremail_core_accounts.send_mail')
    def test_send_this_mail_success_moves_to_sent(self, mock_send_mail):
        """Test that when send_mail succeeds, the mail is moved to sent folder"""
        with Transaction().start(self.database) as txn:
            cursor = txn.cursor
            uid = txn.user
            mailbox_obj = self.openerp.pool.get('poweremail.mailbox')
            
            # Create an account
            acc_id = self.create_account(cursor, uid)
            
            # Create a mail in outbox
            mail_vals = {
                'pem_from': 'test@example.com',
                'pem_to': 'recipient@example.com',
                'pem_subject': 'Test email',
                'pem_body_text': 'Test body',
                'pem_account_id': acc_id,
                'folder': 'outbox',
                'state': 'na',
            }
            mail_id = mailbox_obj.create(cursor, uid, mail_vals)
            
            # Mock send_mail to return True (success)
            mock_send_mail.return_value = True
            
            # Send the mail
            mailbox_obj.send_this_mail(cursor, uid, [mail_id])
            
            # Verify the mail was moved to sent folder
            mail = mailbox_obj.read(cursor, uid, mail_id, ['folder', 'history', 'state'])
            self.assertEqual(mail['folder'], 'sent')
            self.assertEqual(mail['state'], 'na')
            
            # Verify success message is in history
            self.assertIn('Email sent successfully', mail['history'])

    def test_send_this_mail_no_recipient_error(self):
        """Test that when there's no recipient, an appropriate error is logged"""
        with Transaction().start(self.database) as txn:
            cursor = txn.cursor
            uid = txn.user
            mailbox_obj = self.openerp.pool.get('poweremail.mailbox')
            
            # Create an account
            acc_id = self.create_account(cursor, uid)
            
            # Create a mail without recipient
            mail_vals = {
                'pem_from': 'test@example.com',
                'pem_to': '',  # Empty recipient
                'pem_subject': 'Test email',
                'pem_body_text': 'Test body',
                'pem_account_id': acc_id,
                'folder': 'outbox',
                'state': 'na',
            }
            mail_id = mailbox_obj.create(cursor, uid, mail_vals)
            
            # Send the mail
            mailbox_obj.send_this_mail(cursor, uid, [mail_id])
            
            # Verify the mail was moved to error folder
            mail = mailbox_obj.read(cursor, uid, mail_id, ['folder', 'history', 'state'])
            self.assertEqual(mail['folder'], 'error')
            
            # Verify error message is in history
            self.assertIn('No recipient', mail['history'])
    
    def test_check_poweremail_get_sender(self):
        # Aquest test el que farà serà comprovar la funcionalitat del get_sender
        # El problema que tenim ara mateix és que a l'hora de fer el get_sender,
        # aquest mira de crear un Sender o un SMTPSender.
        with Transaction().start(self.database) as txn:
            cursor = txn.cursor
            uid = txn.user
            core_obj = self.pool.get('poweremail.core_accounts')

            acc1_id = self.create_false_account(
                cursor, uid, extra_vals={
                    'name': 'acc1',
                    'email_id': 'test1@example.com',
                    'smtpssl': False,
                    'smtptls': False,
                }
            )

            context = {'lang': 'en_US'}
            with patch('smtplib.SMTP.login', new=self.fake_login):
                with patch('smtplib.SMTP.close', new=self.fake_close):
                    core_obj.send_mail(cursor, uid, [acc1_id], {
                            'To': 'nvillarroya@gisce.net',
                            'CC': '',
                            'BCC': '',
                            'FROM': 'nvillarroya@gisce.net'
                        },
                        "Prova", {
                            'text': "Això és una prova",
                            'html': ''
                        },
                        context=context
                    )

    def _to_bytes(self, value, encoding='utf-8'):
        if value is None:
            return b''
        if isinstance(value, bytes):
            return value
        return value.encode(encoding)

    def fake_login(self, user, password):
        challenge = b"PDE3MjgzOTEwMjMuNDU2N0BtYWlsLmV4YW1wbGUuY29tPg=="
        challenge = base64.b64decode(challenge)
        response = (
                self._to_bytes(user) + b" " +
                hmac.new(
                    self._to_bytes(password),
                    challenge,
                    hashlib.md5
                ).hexdigest().encode('ascii')
        )
        encoded = base64.b64encode(response)
        if six.PY3:
            encoded = encoded.decode('ascii')
        return encoded

    def fake_close(self):
        pass