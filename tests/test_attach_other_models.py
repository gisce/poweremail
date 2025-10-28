# coding=utf-8

from destral.transaction import Transaction
from destral import testing
from mock import patch
from base64 import b64decode

class TestAttachOtherModels(testing.OOTestCase):
    """
    Test the attachment of other models to the email
    """

    @classmethod
    def setUpClass(cls):
        """
        Prepara les dades demo en una transacció temporal.
        No modifica la base de dades persistent.
        """
        super(TestAttachOtherModels, cls).setUpClass()
        with Transaction().start(cls.database) as txn:
            cursor = txn.cursor
            uid = txn.user
            cls.imd_obj = cls.openerp.pool.get('ir.model.data')
            cls.pm_tmp_obj = cls.openerp.pool.get('poweremail.templates')
            cls.partner_obj = cls.openerp.pool.get('res.partner')

            # Guardem referències necessàries
            cls.acc1_id = cls.imd_obj.get_object_reference(
                cursor, uid, 'poweremail', 'info_energia_from_email'
            )[1]

            cls.tmpl_id = cls.imd_obj.get_object_reference(
                cursor, uid, 'poweremail', 'default_template_poweremail_2'
            )[1]

            cls.object_name_ref = cls.imd_obj.get_object_reference(
                cursor, uid, 'base', 'model_res_partner'
            )[1]

            cls.report_id = cls.imd_obj.get_object_reference(
                cursor, uid, 'base', 'report_test'
            )[1]

            cls.partner_ids = cls.partner_obj.search(cursor, uid, [], context={}, limit=1)

    def setUp(self):
        """
        Cada test obre la seva transacció però fa servir les dades creades a setUpClass
        """
        super(TestAttachOtherModels, self).setUp()
        self.txn = Transaction().start(self.database)
        self.cursor = self.txn.cursor
        self.uid = self.txn.user

        self.mailbox_obj = self.openerp.pool.get('poweremail.mailbox')
        self.partner_obj = self.openerp.pool.get('res.partner')
        self.acc_obj = self.openerp.pool.get('poweremail.core_accounts')

        # Prepare demo data references
        self.acc_obj.write(
            self.cursor, self.uid, [self.acc1_id], {'email_id': 'test@example.com'}, context={}
        )
        self.pm_tmp_obj.write(
            self.cursor, self.uid, [self.tmpl_id],
            {'lang': 'en_US', 'object_name': self.object_name_ref,
             'report_template': self.report_id,
             'enforce_from_account': self.acc1_id,
             'template_language': 'mako',
             'def_to': 'Test to',
             'inline': True,
             'def_subject': 'Test subject',
             'def_cc': 'Test cc',
             'def_bcc': 'Test bcc',
             'def_body_text': 'Test body text',
             'def_priority': '2',
             }, context={}
        )

    def tearDown(self):
        super(TestAttachOtherModels, self).tearDown()

    @patch('poweremail.poweremail_template.poweremail_templates.create_report', return_value=("content_from_report_template_object_reference", "provapdf"))
    def test_generate_attachments_with_report_template_object_reference(self, extra_vals=None):
        """
        Test the generation of attachments with a report template object reference

        NOTE: In this case only will generate one attachment, because the conditions are too restrictive to return anything
        """
        mailbox_id = self.pm_tmp_obj.generate_mail(self.cursor, self.uid, self.tmpl_id, [self.partner_ids[0]], context={'raise_exception': True})
        mail = self.mailbox_obj.simple_browse(self.cursor, self.uid, mailbox_id)
        for att in mail.pem_attachments_ids:
            self.assertEqual(b64decode(att.datas), 'content_from_report_template_object_reference') # datas is get from the 1r tuple value from create_report method, that in this case is mocked to avoid the real report generation

    @patch('poweremail.poweremail_template.poweremail_templates.create_report', return_value=("content_from_report_template_object_reference", "provapdf"))
    def test_generate_attachments_without_report_template_object_reference(self, mock_create_report , extra_vals=None):
        """
        Test the generation of attachments without a report template object reference
        """
        self.pm_tmp_obj.write(
            self.cursor, self.uid, [self.tmpl_id], {'report_template_object_reference': False}
        )
        with patch.object(self.pm_tmp_obj, '_generate_attach_reports') as mock_generate_attach_reports:
            mock_generate_attach_reports.return_value = None
            with patch.object(self.pm_tmp_obj._generate_attach_reports, 'get_value') as mock_get_value_from_generate_attach_reports: # Mock the get_value from the _generate_attach_reports method
                mailbox_id = self.pm_tmp_obj.generate_mail(self.cursor, self.uid, self.tmpl_id, [self.partner_ids[0]], context={'raise_exception': True})
                mock_get_value_from_generate_attach_reports.assert_not_called()

                mail = self.mailbox_obj.simple_browse(self.cursor, self.uid, mailbox_id)
                for att in mail.pem_attachments_ids:
                    self.assertEqual(b64decode(att.datas), 'content_from_report_template_object_reference')

    @patch('poweremail.poweremail_template.poweremail_templates.create_report', return_value=("content_main", "pdf"))
    def test_main_report_only(self, mock_create_report):
        """Test that main report is generated correctly when no object reference."""
        res = self.pm_tmp_obj.get_dynamic_attachment(self.cursor, self.uid, self.pm_tmp_obj.simple_browse(self.cursor, self.uid, self.tmpl_id, context={}), [1], context={})
        self.assertEqual(b64decode(res['file']), b'content_main')
        self.assertEqual(res['extension'], 'pdf')


    @patch('poweremail.poweremail_template.LOGGER')
    @patch('poweremail.poweremail_template.poweremail_templates.create_report',
           return_value=("content_main", "pdf"))
    def test_reference_expression_without_object(self, mock_create_report, mock_logger):
        """Ensure expressions without 'object' are handled gracefully."""
        self.pm_tmp_obj.write(
            self.cursor, self.uid, [self.tmpl_id], {'report_template_object_reference': 'user.menu_id'}  # Invalid reference, no 'object'
        )
        tmpl = self.pm_tmp_obj.simple_browse(self.cursor, self.uid, self.tmpl_id, context={})

        res = self.pm_tmp_obj.get_dynamic_attachment(self.cursor, self.uid, tmpl, [1], context={})
        self.assertIn('error', res)
        self.assertEqual(res['error'], "Error generating report from reference expression: warning -- Error\n\nThe expression in 'Reference of the report' field must contain the 'object' variable.")

    @patch('poweremail.poweremail_template.poweremail_templates._get_records_from_report_template_object_reference',
           return_value={'model': 'account.invoice', 'record_ids': []})
    @patch('poweremail.poweremail_template.poweremail_templates.create_report',
           return_value=("content_main", "pdf"))
    def test_reference_evaluates_to_empty(self, mock_create_report, mock_get_refs):
        """Ensure when reference returns empty list, only main report is generated."""
        tmpl = self.pm_tmp_obj.simple_browse(self.cursor, self.uid, self.tmpl_id, context={})
        res = self.pm_tmp_obj.get_dynamic_attachment(self.cursor, self.uid, tmpl, [1], context={})
        self.assertEqual(b64decode(res['file']), b'content_main')
        self.assertEqual(res['extension'], 'pdf')

    def test_get_records_from_reference_one2many(self):
        """Test helper method evaluates a one2many reference correctly."""
        self.pm_tmp_obj.write(
            self.cursor, self.uid, [self.tmpl_id], {'report_template_object_reference': 'object.address'}  # Invalid reference, no 'object'
        )
        tmpl = self.pm_tmp_obj.simple_browse(self.cursor, self.uid, self.tmpl_id, context={})
        res = self.pm_tmp_obj._get_records_from_report_template_object_reference(self.cursor, self.uid, tmpl, [1])
        self.assertIn('model', res)
        self.assertIn('record_ids', res)
        self.assertIsInstance(res['record_ids'], list)

    @patch('poweremail.poweremail_template.poweremail_templates.create_report', return_value=("content_from_report_template_object_reference", "provapdf"))
    def test_reference_uses_same_report_template(self, mock_create_report):
        """Ensure referenced records still use the template's own report."""
        tmpl = self.pm_tmp_obj.simple_browse(self.cursor, self.uid, self.tmpl_id, context={})
        self.pm_tmp_obj.get_dynamic_attachment(self.cursor, self.uid, tmpl, [1], context={})
        mock_create_report.assert_called_once()
        args, kwargs = mock_create_report.call_args
        self.assertEqual(args[2].report_template.id, tmpl.report_template.id)

    @patch('poweremail.poweremail_template.LOGGER')
    @patch('poweremail.poweremail_template.poweremail_templates.create_report',
           return_value=("content_main", "pdf"))
    def test_generate_mail_with_folder_error_in_case_of_invalid_reference(self, mock_create_report, mock_logger):
        """Check that a mail is created even if the reference expression is invalid but with folder 'error'."""
        self.pm_tmp_obj.write(
            self.cursor, self.uid, [self.tmpl_id], {'report_template_object_reference': 'user.menu_id'}  # Invalid reference, no 'object'
        )
        tmpl = self.pm_tmp_obj.simple_browse(self.cursor, self.uid, self.tmpl_id, context={})

        res = self.pm_tmp_obj.get_dynamic_attachment(self.cursor, self.uid, tmpl, [1], context={})
        self.assertIn('error', res)
        self.assertEqual(res['error'], "Error generating report from reference expression: warning -- Error\n\nThe expression in 'Reference of the report' field must contain the 'object' variable.")

        # Generate mail to check error folder creation
        self.pm_tmp_obj.generate_mail_sync(
            self.cursor, self.uid, self.tmpl_id, [self.partner_ids[0]], context={'raise_exception': True}
        )
        error_mail_created_id = self.mailbox_obj.search(
            self.cursor, self.uid, [('folder', '=', 'error'), ('template_id', '=', self.tmpl_id)]
        )
        self.assertTrue(error_mail_created_id)
