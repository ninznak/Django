import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.db import IntegrityError
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.oath import totp

from .abuse import reserve
from .checkout_service import create_order
from .management.commands.backup_database import write_backup
from .models import AbuseBucket, ContactSubmission, Order, OrderItem, Product
from .view_utils import deliver_contact_email
from .views.pages import _store_contact_submission


class SharedQuotaTests(TestCase):
    def test_cache_flush_cannot_reset_quota(self):
        self.assertTrue(reserve('example', 1, 60))
        cache.clear()
        self.assertFalse(reserve('example', 1, 60))

    def test_expiration_reopens_window_and_cleanup_preserves_live_rows(self):
        reserve('expired', 1, 60)
        AbuseBucket.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertTrue(reserve('expired', 1, 60))
        AbuseBucket.objects.create(key='old', hits=1, expires_at=timezone.now() - timedelta(seconds=1))
        call_command('cleanup_abuse', verbosity=0)
        self.assertEqual(AbuseBucket.objects.count(), 1)

    @override_settings(EMAIL_OUTBOUND_LIMIT=1, CONTACT_EMAIL_DEDUPE_SECONDS=0)
    def test_smtp_failure_still_consumes_quota(self):
        data = dict(name='Test', email='test@example.com', subject='Test', message='Hello')
        with mock.patch('core.view_utils.send_contact_email', side_effect=TimeoutError) as send:
            with self.assertRaises(TimeoutError):
                deliver_contact_email(data)
            self.assertFalse(deliver_contact_email(data))
            self.assertEqual(send.call_count, 1)

    @override_settings(CONTACT_FORM_TRY_EMAIL=False)
    def test_honeypot_and_cross_page_duplicate_do_not_write_messages(self):
        data = dict(contact_form='1', name='Test', email='test@example.com', subject='Hi', message='Hello')
        self.client.post(reverse('core:homepage'), {**data, 'website': 'spam.invalid'})
        self.assertFalse(ContactSubmission.objects.exists())
        self.client.post(reverse('core:homepage'), data)
        self.client.post(reverse('core:about'), data)
        self.assertEqual(ContactSubmission.objects.count(), 1)

    def test_failed_storage_does_not_poison_deduplication(self):
        data = dict(name='Test', email='test@example.com', subject='Hi', message='Hello')
        with mock.patch.object(ContactSubmission.objects, 'create', side_effect=IntegrityError):
            with self.assertRaises(IntegrityError):
                _store_contact_submission(data)
        self.assertFalse(AbuseBucket.objects.exists())
        self.assertIsNotNone(_store_contact_submission(data))


class CheckoutSecurityTests(TestCase):
    def prepare(self, client):
        product = Product.objects.filter(kind='shop', is_published=True, is_sold_out=False, is_placeholder=False).first()
        client.post(reverse('core:cart_api'), json.dumps({'action': 'add', 'product_id': product.pk}), content_type='application/json')
        page = client.get(reverse('core:checkout'))
        return dict(name='Test', email='buyer@example.com', country='Russia', city='Moscow',
                    pd_consent='on', license_ack='on', idempotency_key=page.context['checkout_idempotency_key'])

    @override_settings(CONTACT_FORM_TRY_EMAIL=False)
    def test_replay_is_session_bound_and_survives_ip_change_and_cache_clear(self):
        owner, stranger = Client(), Client()
        data = self.prepare(owner)
        owner.post(reverse('core:checkout'), data)
        order = Order.objects.get()
        self.prepare(stranger)
        denied = stranger.post(reverse('core:checkout'), data)
        self.assertEqual(denied.status_code, 400)
        self.assertNotIn(order.pk, stranger.session.get('confirmed_order_ids', []))
        cache.clear()
        retry = owner.post(reverse('core:checkout'), data, REMOTE_ADDR='192.0.2.3')
        self.assertEqual(retry.url, reverse('core:order_confirmation', args=[order.pk]))
        self.assertEqual(Order.objects.count(), 1)

    def test_item_failure_rolls_back_order(self):
        with mock.patch.object(OrderItem.objects, 'create', side_effect=IntegrityError):
            with self.assertRaises(IntegrityError):
                create_order(cleaned_data=dict(name='T', email='t@example.com', country='RU', city='M', pd_consent=True),
                             lines=[{'product': {'id': 1, 'title': 'Test', 'price_cents': 100}, 'qty': 1}],
                             total_cents=100, ip_address='127.0.0.1', checkout_fingerprint='a' * 64)
        self.assertFalse(Order.objects.exists())

    def test_database_unique_constraint_prevents_duplicate_checkout(self):
        kwargs = dict(cleaned_data=dict(name='T', email='t@example.com', country='RU', city='M', pd_consent=True),
                      lines=[], total_cents=0, ip_address='127.0.0.1', checkout_fingerprint='b' * 64)
        create_order(**kwargs)
        with self.assertRaises(IntegrityError):
            create_order(**kwargs)
        self.assertEqual(Order.objects.count(), 1)


class AuthProtectionTests(TestCase):
    @override_settings(AUTH_POST_LIMIT=1)
    def test_admin_login_is_throttled(self):
        url = reverse('admin:login')
        self.assertEqual(self.client.post(url, {'username': 'missing', 'password': 'invalid'}).status_code, 200)
        response = self.client.post(url, {'username': 'missing', 'password': 'invalid'})
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)

    @override_settings(AUTH_POST_LIMIT=1)
    def test_password_reset_throttles_even_invalid_forms(self):
        url = reverse('core:password_reset')
        self.client.post(url, {'email': 'invalid'})
        self.assertEqual(self.client.post(url, {'email': 'invalid'}).status_code, 429)

    @override_settings(ADMIN_OTP_REQUIRED=True)
    def test_admin_requires_otp_even_after_normal_login(self):
        user = get_user_model().objects.create_superuser('otp-user', 'otp@example.com', 'TestPassword123!')
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 302)
        self.client.logout()
        device = TOTPDevice.objects.create(user=user, name='test')
        response = self.client.post(reverse('admin:login'), dict(
            username=user.username, password='TestPassword123!', otp_device=device.persistent_id,
            otp_token=str(totp(device.bin_key)).zfill(6), next=reverse('admin:index')))
        self.assertEqual(response.status_code, 302, response.context['form'].errors if response.context else '')
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)


class BackupTests(SimpleTestCase):
    def test_sqlite_backup_includes_wal_data(self):
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory) / 'live database.sqlite3'
            dst = Path(directory) / 'backup.sqlite3'
            with closing(sqlite3.connect(src)) as db:
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('CREATE TABLE example (value TEXT)')
                db.execute("INSERT INTO example VALUES ('saved')")
                db.commit()
                write_backup({'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(src)}, dst)
                with closing(sqlite3.connect(dst)) as backup:
                    self.assertEqual(backup.execute('SELECT value FROM example').fetchone(), ('saved',))

    def test_postgres_uses_effective_settings_without_secret_in_command(self):
        config = dict(ENGINE='django.db.backends.postgresql', NAME='custom-db', USER='custom-user', PASSWORD='private-test', HOST='db.internal', PORT='5433')
        with mock.patch('core.management.commands.backup_database.subprocess.run') as run:
            write_backup(config, '/backup/file.dump')
        args, kwargs = run.call_args
        self.assertIn('custom-db', args[0])
        self.assertNotIn('private-test', args[0])
        self.assertEqual(kwargs['env']['PGHOST'], 'db.internal')
        self.assertEqual(kwargs['env']['PGPASSWORD'], 'private-test')


class MultiProcessQuotaTests(SimpleTestCase):
    def test_separate_processes_share_one_atomic_budget(self):
        setup = '''import os,sys
os.environ['DJANGO_SETTINGS_MODULE']='creativesphere.settings'
from django.conf import settings
settings.DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':sys.argv[1], 'OPTIONS':{'timeout':20}}}
import django
django.setup()
from core.models import AbuseBucket
from core.abuse import reserve
'''
        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / 'quota.sqlite3')
            subprocess.run([sys.executable, '-c', setup + '\nfrom django.db import connection\nwith connection.schema_editor() as editor: editor.create_model(AbuseBucket)', database], check=True, capture_output=True)
            workers = [subprocess.Popen([sys.executable, '-c', setup + '\nprint(sum(reserve("parallel", 5, 60) for _ in range(8)))', database], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(3)]
            admitted = 0
            for worker in workers:
                out, err = worker.communicate(timeout=45)
                self.assertEqual(worker.returncode, 0, err)
                admitted += int(out.strip())
            self.assertEqual(admitted, 5)
