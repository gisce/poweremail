# coding=utf-8
import base64
import mock
from destral import testing
from destral.transaction import Transaction


class TestPoweremailTemplates(testing.OOTestCaseWithCursor):

    def create_account(self, extra_vals=None):
        acc_obj = self.openerp.pool.get('poweremail.core_accounts')
        cursor = self.cursor
        uid = self.uid

        vals = {
            'name': 'Test account',
            'user': self.uid,
            'email_id': 'test@example.com',
            'smtpserver': 'smtp.example.com',
            'smtpport': 587,
            'smtpuname': 'test',
            'smtppass': 'test',
            'company': 'yes'
        }
        if extra_vals:
            vals.update(extra_vals)

        acc_id = acc_obj.create(cursor, uid, vals)
        return acc_id

    def create_template(self, extra_vals=None):

        imd_obj = self.openerp.pool.get('ir.model.data')
        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        cursor = self.cursor
        uid = self.uid
        acc_id = self.create_account()

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

    def test_creating_email_gets_default_priority(self):

        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        mail_obj = self.openerp.pool.get('poweremail.mailbox')
        imd_obj = self.openerp.pool.get('ir.model.data')

        cursor = self.cursor
        uid = self.uid
        partner_id = imd_obj.get_object_reference(
            cursor, uid, 'base', 'res_partner_asus'
        )[1]

        tmpl_id = self.create_template()

        template = tmpl_obj.browse(cursor, uid, tmpl_id)

        mailbox_id = tmpl_obj._generate_mailbox_item_from_template(
            cursor, uid, template, partner_id
        )

        mail = mail_obj.browse(cursor, uid, mailbox_id)
        self.assertEqual(mail.priority, '2')

    def test_send_wizards_gets_default_priority_from_template(self):
        imd_obj = self.openerp.pool.get('ir.model.data')
        send_obj = self.openerp.pool.get('poweremail.send.wizard')

        cursor = self.cursor
        uid = self.uid
        partner_id = imd_obj.get_object_reference(
            cursor, uid, 'base', 'res_partner_asus'
        )[1]

        tmpl_id = self.create_template()

        wiz_id = send_obj.create(cursor, uid, {}, context={
            'active_id': partner_id,
            'active_ids': [partner_id],
            'src_rec_ids': [partner_id],
            'src_model': 'res.partner',
            'template_id': tmpl_id
        })
        wiz = send_obj.browse(cursor, uid, wiz_id)
        self.assertEqual(wiz.priority, '2')


class TestPoweremailMailbox(testing.OOTestCase):

    def create_account(self, cursor, uid, extra_vals=None):
        acc_obj = self.openerp.pool.get('poweremail.core_accounts')

        vals = {
            'name': 'Test account',
            'user': uid,
            'email_id': 'test@example.com',
            'smtpserver': 'smtp.example.com',
            'smtpport': 587,
            'smtpuname': 'test',
            'smtppass': 'test',
            'company': 'yes'
        }
        if extra_vals:
            vals.update(extra_vals)

        acc_id = acc_obj.create(cursor, uid, vals)
        return acc_id

    def create_template(self, cursor, uid, extra_vals=None):

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

    @mock.patch('poweremail.poweremail_template.poweremail_templates.create_report')
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

    @mock.patch('poweremail.poweremail_template.poweremail_templates.create_report')
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

    @mock.patch('poweremail.poweremail_template.poweremail_templates.create_report')
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

            # Agafem dos templates de prova per posar a l'attachment
            template_id = imd_obj.get_object_reference(
                cursor, uid, 'poweremail', 'default_template_poweremail'
            )[1]

            template_id_2 = imd_obj.get_object_reference(
                cursor, uid, 'poweremail', 'default_template_poweremail_2'
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

            pw_account_id_2 = pw_account_obj.create(cursor, uid, {
                'name': 'test_2',
                'user': 3,
                'email_id': 'test_2@email',
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

            template_vals_2 = {
                'enforce_from_account': pw_account_id_2,
                'report_template': report_id
            }
            pm_tmp_obj.write(cursor, uid, template_id, template_vals_2)

            # Creem dos attachments de prova
            ir_vals = {
                'name': 'filename_prova',
                'datas': base64.b64encode(b'attachment test content'),
                'datas_fname': 'filename_prova.txt',
                'res_model': 'poweremail.templates',
                'res_id': template_id,
            }
            attachment_id = ir_attachment_obj.create(cursor, uid, ir_vals)

            ir_vals_2 = {
                'name': 'filename_prova',
                'datas': base64.b64encode(b'attachment test content'),
                'datas_fname': 'filename_prova.txt',
                'res_model': 'poweremail.templates',
                'res_id': template_id_2,
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
            pm_tmp_obj.generate_mail(cursor, uid, template_id, [template_id, template_id_2])

            attach_ids = ir_attachment_obj.search(cursor, uid, [])
            self.assertEqual(len(attach_ids), 6)