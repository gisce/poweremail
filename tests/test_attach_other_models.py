# coding=utf-8

from destral.transaction import Transaction
from destral import testing
from mock import patch
from base64 import b64decode
import netsvc
from mock import ANY

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

        imd_obj = self.openerp.pool.get('ir.model.data')
        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        acc_id = False
        if 'enforce_from_account' not in extra_vals:
            acc_id = self._create_account(cursor, uid)

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
            'report_template_object_reference': extra_vals['report_template_object_reference'] if 'report_template_object_reference' in extra_vals else '',
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
                                                                        'report_template_object_reference': 'object.invoice_id',
                                                                        })

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
                                                                     'report_template_object_reference': 'object.invoice_id',
                                                                     })

            mailbox_id = pm_tmp_obj.generate_mail(cursor, uid, tmpl_id, [1], context={'raise_exception': True})
            mail = mailbox_obj.simple_browse(cursor, uid, mailbox_id)

            for att in mail.pem_attachments_ids:
                self.assertEqual(b64decode(att.datas), 'content_from_report_template_object_reference')

    @patch('poweremail.poweremail_template.poweremail_templates.create_report', return_value=("content_main", "pdf"))
    def test_main_report_only(self, mock_create_report):
        """Test that main report is generated correctly when no object reference."""
        with Transaction().start(self.database) as txn:
            cursor = txn.cursor
            uid = txn.user
            tmpl_id = self._create_template(cursor, uid)
            tmpl_obj = self.openerp.pool.get('poweremail.templates')

            res = tmpl_obj.get_dynamic_attachment(cursor, uid, tmpl_obj.simple_browse(cursor, uid, tmpl_id, context={}), [1], context={})
            self.assertEqual(len(res), 1)
            self.assertEqual(b64decode(res[0]['file']), b'content_main')
            self.assertEqual(res[0]['extension'], 'pdf')

@patch('poweremail.poweremail_template.poweremail_templates._get_records_from_report_template_object_reference')
@patch('poweremail.poweremail_template.poweremail_templates.create_report',
       return_value=("content_from_report_reference", "pdf"))
def test_multiple_reference_records(self, mock_create_report, mock_get_refs):
    """Test that multiple referenced records generate multiple attachments."""
    mock_get_refs.return_value = {'model': 'account.invoice', 'record_ids': [1, 2, 3]}

    with Transaction().start(self.database) as txn:
        cursor = txn.cursor
        uid = txn.user
        tmpl_id = self._create_template(cursor, uid, {
            'report_template_object_reference': 'object.invoice_ids'
        })
        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        tmpl = tmpl_obj.simple_browse(cursor, uid, tmpl_id, context={})

        res = tmpl_obj.get_dynamic_attachment(cursor, uid, tmpl, [1], context={})
        self.assertGreaterEqual(len(res), 2)  # 1 main + 1 extra or more
        mock_create_report.assert_called()

@patch('poweremail.poweremail_template.LOGGER')
@patch('poweremail.poweremail_template.poweremail_templates.create_report',
       return_value=("content_main", "pdf"))
def test_reference_expression_without_object(self, mock_create_report, mock_logger):
    """Ensure expressions without 'object' are handled gracefully."""
    with Transaction().start(self.database) as txn:
        cursor = txn.cursor
        uid = txn.user
        tmpl_id = self._create_template(cursor, uid, {
            'report_template_object_reference': 'invoice_id'
        })
        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        tmpl = tmpl_obj.simple_browse(cursor, uid, tmpl_id, context={})

        res = tmpl_obj.get_dynamic_attachment(cursor, uid, tmpl, [1], context={})
        self.assertEqual(len(res), 1)
        mock_logger.notifyChannel.assert_any_call(
            'Power Email', netsvc.LOG_ERROR,
            ANY
        )

@patch('poweremail.poweremail_template.poweremail_templates._get_records_from_report_template_object_reference',
       return_value={'model': 'account.invoice', 'record_ids': []})
@patch('poweremail.poweremail_template.poweremail_templates.create_report',
       return_value=("content_main", "pdf"))
def test_reference_evaluates_to_empty(self, mock_create_report, mock_get_refs):
    """Ensure when reference returns empty list, only main report is generated."""
    with Transaction().start(self.database) as txn:
        cursor = txn.cursor
        uid = txn.user
        tmpl_id = self._create_template(cursor, uid, {
            'report_template_object_reference': 'object.invoice_ids'
        })
        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        tmpl = tmpl_obj.simple_browse(cursor, uid, tmpl_id, context={})

        res = tmpl_obj.get_dynamic_attachment(cursor, uid, tmpl, [1], context={})
        self.assertEqual(len(res), 1)
        self.assertEqual(b64decode(res[0]['file']), b'content_main')

def test_get_records_from_reference_many2one(self):
    """Test helper method evaluates a Many2one reference correctly."""
    with Transaction().start(self.database) as txn:
        cursor = txn.cursor
        uid = txn.user
        tmpl_id = self._create_template(cursor, uid, {
            'report_template_object_reference': 'object.invoice_id'
        })
        tmpl_obj = self.openerp.pool.get('poweremail.templates')
        tmpl = tmpl_obj.simple_browse(cursor, uid, tmpl_id, context={})

        res = tmpl_obj._get_records_from_report_template_object_reference(cursor, uid, tmpl, [1])
        self.assertIn('model', res)
        self.assertIn('record_ids', res)
        self.assertIsInstance(res['record_ids'], list)
