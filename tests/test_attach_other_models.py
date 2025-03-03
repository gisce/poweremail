# coding=utf-8

from destral.transaction import Transaction
from destral import testing
from mock import patch
from base64 import b64decode

class TestAttachOtherModels(testing.OOTestCase):
    """
    Test the attachment of other models to the email
    """

    def setUp(self):
        self.openerp.install_module('giscedata_facturacio')

    def _create_account(self, cursor, uid, extra_vals=None):
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

    def _create_template(self, cursor, uid, extra_vals=None):
        if extra_vals is None:
            extra_vals = {}

        model = extra_vals['model'] if 'model' in extra_vals else None
        conditions = extra_vals['conditions'] if 'conditions' in extra_vals else None

        if model and conditions:
            report_template_object_reference_value = "('{model}', {conditions})".format(
                model=model,
                conditions=conditions)
        else:
            report_template_object_reference_value = None


        imd_obj = self.openerp.pool.get('ir.model.data')
        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        acc_id = False
        if 'enforce_from_account' not in extra_vals:
            acc_id = self.create_account(cursor, uid)

        model_partner = imd_obj.get_object_reference(
            cursor, uid, 'base', 'model_res_partner'
        )[1] # Retunr ir.model id of res.partner

        # Agafem un report de demo
        report_id = imd_obj.get_object_reference(
            cursor, uid, 'base', 'report_test'
        )[1]

        vals = {
            'name': 'Test template',
            'object_name': model_partner,
            'enforce_from_account': acc_id,
            'template_language': 'mako',
            'def_to': 'Test to',
            'inline': True,
            'def_subject': 'Test subject',
            'def_cc': 'Test cc',
            'def_bcc': 'Test bcc',
            'def_body_text': 'Test body text',
            'def_priority': '2',
            'report_template': report_id,
            'report_template_object_reference': report_template_object_reference_value
        }

        if extra_vals:
            vals.update(extra_vals)

        tmpl_id = tmpl_obj.create(cursor, uid, vals)
        return tmpl_id

    @patch('poweremail.poweremail_template.poweremail_templates.create_report', return_value=("content_from_report_template_object_reference", "provapdf"))
    def test_generate_attachments_with_report_template_object_reference(self, extra_vals=None):
        """
        Test the generation of attachments with a report template object reference

        NOTE: In this case only will generate one attachment, because the conditions are too restrictive to return anything
        """
        with Transaction().start(self.database) as txn:
            uid = txn.user
            cursor = txn.cursor
            mailbox_obj = self.openerp.pool.get('poweremail.mailbox')
            pm_tmp_obj = self.openerp.pool.get('poweremail.templates')

            acc1_id = self._create_account(cursor, uid, extra_vals={'name': 'acc1', 'email_id': 'test1@example.com'})
            tmpl_id = self._create_template(cursor, uid, extra_vals={'enforce_from_account': acc1_id,
                                                                        'name': 'Test template 1',
                                                                        'model': 'giscedata.facturacio.factura',
                                                                        'conditions': [('invoice_id', '=', 1)]})

            mailbox_id = pm_tmp_obj.generate_mail(cursor, uid, tmpl_id, [1], context={'raise_exception': True})
            mail = mailbox_obj.simple_browse(cursor, uid, mailbox_id)
            for att in mail.pem_attachments_ids:
                self.assertEqual(b64decode(att.datas), 'content_from_report_template_object_reference') # datas is get from the 1r tuple value from create_report method, that in this case is mocked to avoid the real report generation

    @patch('poweremail.poweremail_template.poweremail_templates.create_report', return_value=("content_from_report_template_object_reference", "provapdf"))
    def test_generate_attachments_without_report_template_object_reference(self, mock_create_report , extra_vals=None):
        """
        Test the generation of attachments without a report template object reference
        """
        with Transaction().start(self.database) as txn:
            uid = txn.user
            cursor = txn.cursor
            pm_tmp_obj = self.openerp.pool.get('poweremail.templates')
            mailbox_obj = self.openerp.pool.get('poweremail.mailbox')

            acc1_id = self._create_account(cursor, uid, extra_vals={'name': 'acc1', 'email_id': 'test1@example.com'})
            tmpl_id = self._create_template(cursor, uid, extra_vals={'enforce_from_account': acc1_id,
                                                                        'name': 'Test template 1',
                                                                        'model': None,
                                                                        'conditions': None}) # Without report_template_object_reference

            with patch.object(pm_tmp_obj, '_generate_attach_reports') as mock_generate_attach_reports:
                mock_generate_attach_reports.return_value = None
                with patch.object(pm_tmp_obj._generate_attach_reports, 'get_value') as mock_get_value_from_generate_attach_reports: # Mock the get_value from the _generate_attach_reports method
                    mailbox_id = pm_tmp_obj.generate_mail(cursor, uid, tmpl_id, [1], context={'raise_exception': True})
                    mock_get_value_from_generate_attach_reports.assert_not_called()

                    mail = mailbox_obj.simple_browse(cursor, uid, mailbox_id)
                    for att in mail.pem_attachments_ids:
                        self.assertEqual(b64decode(att.datas), 'content_from_report_template_object_reference')

    @patch('poweremail.poweremail_template.poweremail_templates.create_report', return_value=("content_from_report_template_object_reference", "provapdf"))
    def test_generate_attachments_with_user(self, mock_create_report, extra_vals=None):
        """
        Test the generation of attachments with a user and invoice
        """
        with Transaction().start(self.database) as txn:
            uid = txn.user
            cursor = txn.cursor
            mailbox_obj = self.openerp.pool.get('poweremail.mailbox')
            pm_tmp_obj = self.openerp.pool.get('poweremail.templates')

            acc1_id = self._create_account(cursor, uid, extra_vals={'name': 'acc1', 'email_id': 'test1@example.com'})
            tmpl_id = self._create_template(cursor, uid, extra_vals={'enforce_from_account': acc1_id,
                                                                     'name': 'Test template 1',
                                                                     'model': 'account.invoice',
                                                                     'conditions': [('partner_id', '=', 1)]}) # Tiny partner

            mailbox_id = pm_tmp_obj.generate_mail(cursor, uid, tmpl_id, [1], context={'raise_exception': True})
            mail = mailbox_obj.simple_browse(cursor, uid, mailbox_id)

            for att in mail.pem_attachments_ids:
                self.assertEqual(b64decode(att.datas), 'content_from_report_template_object_reference')
