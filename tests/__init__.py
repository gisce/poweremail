# coding=utf-8
from destral import testing


class TestPoweremailTemplates(testing.OOTestCaseWithCursor):

    def create_account(self):
        acc_obj = self.openerp.pool.get('poweremail.core_accounts')
        cursor = self.cursor
        uid = self.uid

        acc_id = acc_obj.create(cursor, uid, {
            'name': 'Test account',
            'user': self.uid,
            'email_id': 'test@example.com',
            'smtpserver': 'smtp.example.com',
            'smtpport': 587,
            'smtpuname': 'test',
            'smtppass': 'test',
            'company': 'yes'
        })
        return acc_id

    def create_template(self):

        imd_obj = self.openerp.pool.get('ir.model.data')
        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        cursor = self.cursor
        uid = self.uid
        acc_id = self.create_account()

        model_partner = imd_obj.get_object_reference(
            cursor, uid, 'base', 'model_res_partner'
        )[1]

        tmpl_id = tmpl_obj.create(cursor, uid, {
            'name': 'Test template',
            'object_name': model_partner,
            'enforce_from_account': acc_id,
            'template_language': 'mako',
            'def_priority': '2'
        })
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
