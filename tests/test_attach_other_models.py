# coding=utf-8

from destral.transaction import Transaction
from destral import testing
from mock import patch
from base64 import b64decode
from osv.osv import except_osv

class TestAttachOtherModels(testing.OOTestCase):
    """
    Test the attachment of other models to the email
    """

    def setUp(self):
        super(TestAttachOtherModels, self).setUp()
        self.txn = Transaction().start(self.database)
        self.cursor = self.txn.cursor
        self.uid = self.txn.user
        pool = self.openerp.pool

        # Objectes comuns
        self.partner_obj = pool.get('res.partner')
        self.pm_tmp_obj = pool.get('poweremail.templates')
        self.acc_obj = pool.get('poweremail.core_accounts')
        self.mailbox_obj = pool.get('poweremail.mailbox')
        self.ir_model_obj = pool.get('ir.model')
        self.report_obj = pool.get('ir.actions.report.xml')

        # Crear partner nou
        self.partner_id = self.partner_obj.create(self.cursor, self.uid, {
            'name': 'Test Partner',
            'email': 'partner@test.com',
        })

        # Crear compte d'email nou
        self.account_id = self.acc_obj.create(self.cursor, self.uid, {
            'name': 'Test account',
            'user': self.uid,
            'email_id': 'test_account@test.com',
            'smtpserver': 'smtp.test.com',
            'smtpport': 25,
            'company': 'no',
        })

        # Crear model i report dummy
        model_partner_id = self.ir_model_obj.search(
            self.cursor, self.uid, [('model', '=', 'res.partner')]
        )[0]

        self.report_id = self.report_obj.create(self.cursor, self.uid, {
            'name': 'Fake Report',
            'model': 'res.partner',
            'report_name': 'fake.report.partner',
            'report_type': 'pdf',
        })

        # Crear plantilla nova
        self.template_id = self.pm_tmp_obj.create(self.cursor, self.uid, {
            'name': 'Template Test',
            'object_name': model_partner_id,
            'lang': 'en_US',
            'report_template': self.report_id,
            'enforce_from_account': self.account_id,
            'template_language': 'mako',
            'def_to': 'object.email',
            'inline': True,
            'def_subject': 'Test subject',
            'def_body_text': 'Test body text',
            'def_priority': '2',
        })

    @patch('poweremail.poweremail_template.PY3', True)
    @patch('poweremail.poweremail_template.poweremail_templates.create_report',
           return_value=("OK_REPORT_PY3", "pdf"))
    def test_happy_path_python3_encoding(self, mock_create_report):
        """
        Ensure that in Python 3, the report string is encoded before base64.
        This tests the PY3 branch added in the patch.
        """
        # Set the report template object reference
        self.pm_tmp_obj.write(
            self.cursor, self.uid, [self.template_id],
            {'report_template_object_reference': 'object.id'}
        )

        tmpl = self.pm_tmp_obj.simple_browse(self.cursor, self.uid, self.template_id)

        # Get dynamic attachment
        res = self.pm_tmp_obj.get_dynamic_attachment(
            self.cursor, self.uid, tmpl, [self.partner_id]
        )

        # Assert that 'file' exists and is correctly base64-encoded
        self.assertIn('file', res)
        self.assertEqual(b64decode(res['file']), b'OK_REPORT_PY3')
        self.assertEqual(res['extension'], 'pdf')

        # Generate mail to ensure full happy path works
        mailbox_id = self.pm_tmp_obj.generate_mail(
            self.cursor, self.uid, self.template_id, [self.partner_id],
            context={'raise_exception': True}
        )
        mail = self.mailbox_obj.simple_browse(self.cursor, self.uid, mailbox_id)
        self.assertNotEqual(mail.folder, 'error')

    @patch('poweremail.poweremail_template.poweremail_templates.create_report',
           return_value=("OK_REPORT", "pdf"))
    def test_happy_path_with_valid_reference(self, mock_create_report):
        """Ensure normal flow works when the reference expression returns a
        valid ID."""
        self.pm_tmp_obj.write(
            self.cursor, self.uid, [self.template_id],
            {'report_template_object_reference': 'object.id'}
        )

        tmpl = self.pm_tmp_obj.simple_browse(self.cursor, self.uid, self.template_id)
        res = self.pm_tmp_obj.get_dynamic_attachment(
            self.cursor, self.uid, tmpl, [self.partner_id]
        )

        self.assertIn('file', res)
        self.assertEqual(b64decode(res['file']), b'OK_REPORT')
        self.assertEqual(res['extension'], 'pdf')

        mailbox_id = self.pm_tmp_obj.generate_mail(
            self.cursor, self.uid, self.template_id, [self.partner_id],
            context={'raise_exception': True}
        )
        mail = self.mailbox_obj.simple_browse(self.cursor, self.uid, mailbox_id)
        self.assertNotEqual(mail.folder, 'error')

    def test_reference_returns_record_instead_of_id(self):
        """Ensure exception is raised if expression returns a record instead
        of an ID."""
        self.pm_tmp_obj.write(
            self.cursor, self.uid, [self.template_id],
            {'report_template_object_reference': 'object'}
        )
        tmpl = self.pm_tmp_obj.simple_browse(self.cursor, self.uid,
                                             self.template_id)
        with self.assertRaises(except_osv) as error:
            self.pm_tmp_obj._get_records_from_report_template_object_reference(
                self.cursor, self.uid, tmpl, [self.partner_id]
            )

        self.assertIn(
            u"The expression in 'Reference of the report' field returned an empty value or a value that is not an integer ID.",
            error.exception.value
        )

    @patch('poweremail.poweremail_template.poweremail_templates.create_report',
           return_value=("content_main", "pdf"))
    def test_main_report_only(self, mock_create_report):
        """Test that main report is generated correctly when no object
        reference."""
        tmpl = self.pm_tmp_obj.simple_browse(self.cursor, self.uid, self.template_id)
        res = self.pm_tmp_obj.get_dynamic_attachment(self.cursor, self.uid, tmpl, [self.partner_id])
        self.assertEqual(b64decode(res['file']), b'content_main')
        self.assertEqual(res['extension'], 'pdf')

    @patch('poweremail.poweremail_template.poweremail_templates.create_report')
    def test_create_report_from_report_template_object_reference_reference_with_non_records_ids(
            self, mock_create_report):
        """Ensure exception is raised if expression returns non-record IDs."""
        self.pm_tmp_obj.write(
            self.cursor, self.uid, [self.template_id],
            {'report_template_object_reference': 'object.name'}
        )
        tmpl = self.pm_tmp_obj.simple_browse(self.cursor, self.uid,
                                             self.template_id)
        with self.assertRaises(except_osv) as error:
            self.pm_tmp_obj.get_dynamic_attachment(self.cursor, self.uid, tmpl,
                                                   [self.partner_id])

        self.assertIn(
            u"The expression in 'Reference of the report' field returned an empty value or a value that is not an integer ID.",
            error.exception.value
        )

    def test_reference_expression_without_object(self):
        """Ensure expressions without 'object' raise an exception."""
        self.pm_tmp_obj.write(
            self.cursor, self.uid, [self.template_id],
            {'report_template_object_reference': 'user.menu_id'}
        )
        tmpl = self.pm_tmp_obj.simple_browse(self.cursor, self.uid, self.template_id)
        with self.assertRaises(except_osv) as error:
            self.pm_tmp_obj.get_dynamic_attachment(self.cursor, self.uid, tmpl, [self.partner_id])

        self.assertIn(
            u"The expression in 'Reference of the report' field must contain the 'object' variable.",
            error.exception.value
        )

    def test_reference_evaluates_to_empty(self):
        """Ensure expression with empty result raises an exception."""
        self.pm_tmp_obj.write(
            self.cursor, self.uid, [self.template_id],
            {'report_template_object_reference': 'object.child_ids'}
        )
        tmpl = self.pm_tmp_obj.simple_browse(self.cursor, self.uid,
                                             self.template_id)
        with self.assertRaises(except_osv) as error:
            self.pm_tmp_obj.get_dynamic_attachment(self.cursor, self.uid, tmpl,
                                                   [self.partner_id])

        self.assertIn(
            u"The expression in 'Reference of the report' field returned an empty value or a value that is not an integer ID.",
            error.exception.value
        )

    @patch(
        'poweremail.poweremail_template.poweremail_templates._get_records_from_report_template_object_reference',
        return_value=[]
    )
    @patch('poweremail.poweremail_template.poweremail_templates.create_report')
    def test_create_report_from_report_template_object_reference_no_reference(
            self, mock_get_records, mock_create_report):
        """Ensure exception is raised if no records found from reference."""
        self.pm_tmp_obj.write(
            self.cursor, self.uid, [self.template_id],
            {'report_template_object_reference': 'object.id'}
        )
        tmpl = self.pm_tmp_obj.simple_browse(self.cursor, self.uid,
                                             self.template_id)
        with self.assertRaises(except_osv) as error:
            self.pm_tmp_obj.create_report_from_report_template_object_reference_reference(
                self.cursor, self.uid, tmpl, [self.partner_id]
            )

        self.assertIn(
            u"No records found evaluating the expression in 'Reference of the report' field.",
            error.exception.value
        )

    @patch('poweremail.poweremail_template.poweremail_templates.create_report',
           return_value=("content_from_report_template_object_reference",
                         "pdf"))
    def test_reference_uses_same_report_template(self, mock_create_report):
        """Ensure referenced records use the same template report."""
        tmpl = self.pm_tmp_obj.simple_browse(self.cursor, self.uid, self.template_id)
        self.pm_tmp_obj.get_dynamic_attachment(self.cursor, self.uid, tmpl, [self.partner_id])
        mock_create_report.assert_called_once()
        args, kwargs = mock_create_report.call_args
        self.assertEqual(args[2].report_template.id, tmpl.report_template.id)
