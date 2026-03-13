# coding=utf-8
import base64
import mock
from destral import testing
from destral.transaction import Transaction
from datetime import datetime, timedelta


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

    def create_mailbox(self, template_id, date_mail):
        cursor = self.cursor
        uid = self.uid

        mailbox_obj = self.openerp.pool.get('poweremail.mailbox')
        imd_obj = self.openerp.pool.get('ir.model.data')

        pm_account = imd_obj.get_object_reference(
            cursor, uid, 'poweremail', 'info_energia_from_email'
        )[1]

        return mailbox_obj.create(cursor, uid, {
            'pem_account_id': pm_account,
            'pem_subject': 'Prova',
            'template_id': template_id,
            'date_mail': date_mail,
        })

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

    def test_inliner_from_template_send_wizard(self):
        imd_obj = self.openerp.pool.get('ir.model.data')
        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        send_obj = self.openerp.pool.get('poweremail.send.wizard')

        cursor = self.cursor
        uid = self.uid

        partner_id = imd_obj.get_object_reference(
            cursor, uid, 'base', 'res_partner_asus'
        )[1]
        tmpl_id = self.create_template()

        example_html = """
<html>
<style type="text/css">
h1 { border:1px solid black }
p { color:red;}
</style>
<h1 style="font-weight:bolder">Peter</h1>
<p>Hej</p>
</html>
        """

        write_vals = {
            'def_body_text': example_html,
            'inline': True
        }

        tmpl_obj.write(cursor, uid, tmpl_id, write_vals)

        wiz_id = send_obj.create(cursor, uid, {}, context={
            'active_id': partner_id,
            'active_ids': [partner_id],
            'src_rec_ids': [partner_id],
            'src_model': 'res.partner',
            'template_id': tmpl_id
        })

        wiz = send_obj.browse(cursor, uid, wiz_id)

        inlined_html = '<html>\n<head></head>\n<body>\n<h1 style="border:1px solid black; font-weight:bolder">Peter</h1>\n<p style="color:red">Hej</p>\n</body>\n</html>\n'

        self.assertEqual(wiz.body_text, inlined_html)

    def test_no_inliner_from_template_send_wizard(self):
        imd_obj = self.openerp.pool.get('ir.model.data')
        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        send_obj = self.openerp.pool.get('poweremail.send.wizard')

        cursor = self.cursor
        uid = self.uid

        partner_id = imd_obj.get_object_reference(
            cursor, uid, 'base', 'res_partner_asus'
        )[1]
        tmpl_id = self.create_template()

        example_html = """
<html>
<style type="text/css">
h1 { border:1px solid black }
p { color:red;}
</style>
<h1 style="font-weight:bolder">Peter</h1>
<p>Hej</p>
</html>
        """

        write_vals = {
            'def_body_text': example_html,
            'inline': False
        }

        tmpl_obj.write(cursor, uid, tmpl_id, write_vals)

        wiz_id = send_obj.create(cursor, uid, {}, context={
            'active_id': partner_id,
            'active_ids': [partner_id],
            'src_rec_ids': [partner_id],
            'src_model': 'res.partner',
            'template_id': tmpl_id
        })

        wiz = send_obj.browse(cursor, uid, wiz_id)

        self.assertEqual(wiz.body_text, example_html)

    def test_no_inliner_from_template(self):
        imd_obj = self.openerp.pool.get('ir.model.data')
        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        mailbox_obj = self.openerp.pool.get('poweremail.mailbox')

        cursor = self.cursor
        uid = self.uid

        partner_id = imd_obj.get_object_reference(
            cursor, uid, 'base', 'res_partner_asus'
        )[1]
        tmpl_id = self.create_template()

        example_html = """
<html>
<style type="text/css">
h1 { border:1px solid black }
p { color:red;}
</style>
<h1 style="font-weight:bolder">Peter</h1>
<p>Hej</p>
</html>
        """

        write_vals = {
            'def_body_text': example_html,
            'inline': False
        }

        tmpl_obj.write(cursor, uid, tmpl_id, write_vals)

        mail_id = tmpl_obj.generate_mail_sync(cursor, uid, tmpl_id, [partner_id])
        pem_body_text = mailbox_obj.read(cursor, uid, mail_id, ['pem_body_text'])['pem_body_text']

        self.assertEqual(pem_body_text, example_html)

    def test_inliner_from_template(self):
        imd_obj = self.openerp.pool.get('ir.model.data')
        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        mailbox_obj = self.openerp.pool.get('poweremail.mailbox')

        cursor = self.cursor
        uid = self.uid

        partner_id = imd_obj.get_object_reference(
            cursor, uid, 'base', 'res_partner_asus'
        )[1]
        tmpl_id = self.create_template()

        example_html = """
<html>
<style type="text/css">
h1 { border:1px solid black }
p { color:red;}
</style>
<h1 style="font-weight:bolder">Peter</h1>
<p>Hej</p>
</html>
        """

        write_vals = {
            'def_body_text': example_html,
            'inline': True
        }

        tmpl_obj.write(cursor, uid, tmpl_id, write_vals)
        mail_id = tmpl_obj.generate_mail_sync(cursor, uid, tmpl_id, [partner_id])
        pem_body_text = mailbox_obj.read(cursor, uid, mail_id, ['pem_body_text'])['pem_body_text']

        inlined_html = '<html>\n<head></head>\n<body>\n<h1 style="border:1px solid black; font-weight:bolder">Peter</h1>\n<p style="color:red">Hej</p>\n</body>\n</html>\n'

        self.assertEqual(pem_body_text, inlined_html)

    def test_remove_action_reference(self):
        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        cursor = self.cursor
        uid = self.uid
        tmpl_id = self.create_template()
        template = tmpl_obj.browse(cursor, uid, tmpl_id)
        template.create_action_reference({})
        template = tmpl_obj.browse(cursor, uid, tmpl_id)
        self.assertTrue(template.ref_ir_act_window)
        self.assertTrue(template.ref_ir_value)
        template = tmpl_obj.browse(cursor, uid, tmpl_id)

        template.remove_action_reference({})
        self.assertFalse(template.ref_ir_act_window)
        self.assertFalse(template.ref_ir_value)

    def test_send_stats_without_interval(self):
        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        cursor = self.cursor
        uid = self.uid

        tmpl_id = self.create_template()

        old_date = (datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d %H:%M:%S')
        new_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')

        self.create_mailbox(tmpl_id, old_date)
        self.create_mailbox(tmpl_id, new_date)

        template = tmpl_obj.read(cursor, uid, tmpl_id, ['send_count', 'last_send_date'])

        self.assertEqual(template['send_count'], 2)
        self.assertEqual(template['last_send_date'], new_date)

    def test_send_stats_with_interval(self):
        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        cursor = self.cursor
        uid = self.uid

        tmpl_id = self.create_template({
            'stats_interval': 7,
        })

        old_date = (datetime.now() - timedelta(days=20)).strftime('%Y-%m-%d %H:%M:%S')
        in_range_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')

        self.create_mailbox(tmpl_id, old_date)
        self.create_mailbox(tmpl_id, in_range_date)

        template = tmpl_obj.read(cursor, uid, tmpl_id, ['send_count', 'last_send_date'])

        self.assertEqual(template['send_count'], 1)
        self.assertEqual(template['last_send_date'], in_range_date)
