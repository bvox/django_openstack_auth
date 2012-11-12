import datetime

import django
from django import test
from django.conf import settings
from django.core.urlresolvers import reverse

from keystoneclient import exceptions as keystone_exceptions
from keystoneclient.v2_0 import client

import mox

from .data import generate_test_data
from openstack_auth import utils


class OpenStackAuthTests(test.TestCase):
    def setUp(self):
        super(OpenStackAuthTests, self).setUp()
        self.mox = mox.Mox()
        self.data = generate_test_data()
        endpoint = settings.OPENSTACK_KEYSTONE_URL
        self.keystone_client = client.Client(endpoint=endpoint)
        self.keystone_client.service_catalog = self.data.service_catalog

    def tearDown(self):
        self.mox.UnsetStubs()
        self.mox.VerifyAll()

    def test_login(self):
        tenants = [self.data.tenant_one, self.data.tenant_two]
        user = self.data.user
        sc = self.data.service_catalog

        form_data = {'region': settings.OPENSTACK_KEYSTONE_URL,
                     'password': user.password,
                     'username': user.name}

        self.mox.StubOutWithMock(client, "Client")
        self.mox.StubOutWithMock(self.keystone_client.tenants, "list")
        self.mox.StubOutWithMock(self.keystone_client.tokens, "authenticate")

        client.Client(auth_url=settings.OPENSTACK_KEYSTONE_URL,
                      password=user.password,
                      username=user.name,
                      tenant_id=None).AndReturn(self.keystone_client)
        self.keystone_client.tenants.list().AndReturn(tenants)
        self.keystone_client.tokens.authenticate(tenant_id=tenants[1].id,
                                                 token=sc.get_token()['id'],
                                                 username=user.name) \
                            .AndReturn(self.data.scoped_token)

        self.mox.ReplayAll()

        url = reverse('login')

        # GET the page to set the test cookie.
        response = self.client.get(url, form_data)
        self.assertEqual(response.status_code, 200)

        # POST to the page to log in.
        response = self.client.post(url, form_data)
        self.assertRedirects(response, settings.LOGIN_REDIRECT_URL)

    def test_no_tenants(self):
        user = self.data.user

        form_data = {'region': settings.OPENSTACK_KEYSTONE_URL,
                     'password': user.password,
                     'username': user.name}

        self.mox.StubOutWithMock(client, "Client")
        self.mox.StubOutWithMock(self.keystone_client.tenants, "list")

        client.Client(auth_url=settings.OPENSTACK_KEYSTONE_URL,
                      password=user.password,
                      username=user.name,
                      tenant_id=None).AndReturn(self.keystone_client)
        self.keystone_client.tenants.list().AndReturn([])

        self.mox.ReplayAll()

        url = reverse('login')

        # GET the page to set the test cookie.
        response = self.client.get(url, form_data)
        self.assertEqual(response.status_code, 200)

        # POST to the page to log in.
        response = self.client.post(url, form_data)
        self.assertTemplateUsed(response, 'auth/login.html')
        self.assertContains(response,
                            'You are not authorized for any projects.')

    def test_invalid_credentials(self):
        user = self.data.user

        form_data = {'region': settings.OPENSTACK_KEYSTONE_URL,
                     'password': "invalid",
                     'username': user.name}

        self.mox.StubOutWithMock(client, "Client")

        exc = keystone_exceptions.Unauthorized(401)
        client.Client(auth_url=settings.OPENSTACK_KEYSTONE_URL,
                      password="invalid",
                      username=user.name,
                      tenant_id=None).AndRaise(exc)

        self.mox.ReplayAll()

        url = reverse('login')

        # GET the page to set the test cookie.
        response = self.client.get(url, form_data)
        self.assertEqual(response.status_code, 200)

        # POST to the page to log in.
        response = self.client.post(url, form_data)
        self.assertTemplateUsed(response, 'auth/login.html')
        self.assertContains(response, "Invalid user name or password.")

    def test_exception(self):
        user = self.data.user

        form_data = {'region': settings.OPENSTACK_KEYSTONE_URL,
                     'password': user.password,
                     'username': user.name}

        self.mox.StubOutWithMock(client, "Client")

        exc = keystone_exceptions.ClientException(500)
        client.Client(auth_url=settings.OPENSTACK_KEYSTONE_URL,
                      password=user.password,
                      username=user.name,
                      tenant_id=None).AndRaise(exc)

        self.mox.ReplayAll()

        url = reverse('login')

        # GET the page to set the test cookie.
        response = self.client.get(url, form_data)
        self.assertEqual(response.status_code, 200)

        # POST to the page to log in.
        response = self.client.post(url, form_data)

        self.assertTemplateUsed(response, 'auth/login.html')
        self.assertContains(response,
                            ("An error occurred authenticating. Please try "
                             "again later."))

    def test_switch(self):
        tenant = self.data.tenant_two
        tenants = [self.data.tenant_one, self.data.tenant_two]
        user = self.data.user
        scoped = self.data.scoped_token
        sc = self.data.service_catalog

        form_data = {'region': settings.OPENSTACK_KEYSTONE_URL,
                     'username': user.name,
                     'password': user.password}

        self.mox.StubOutWithMock(client, "Client")
        self.mox.StubOutWithMock(self.keystone_client.tenants, "list")
        self.mox.StubOutWithMock(self.keystone_client.tokens, "authenticate")

        client.Client(auth_url=settings.OPENSTACK_KEYSTONE_URL,
                      password=user.password,
                      username=user.name,
                      tenant_id=None).AndReturn(self.keystone_client)
        self.keystone_client.tenants.list().AndReturn(tenants)
        self.keystone_client.tokens.authenticate(tenant_id=tenants[1].id,
                                                 token=sc.get_token()['id'],
                                                 username=user.name) \
                            .AndReturn(scoped)

        client.Client(endpoint=settings.OPENSTACK_KEYSTONE_URL) \
                .AndReturn(self.keystone_client)

        self.keystone_client.tokens.authenticate(tenant_id=tenant.id,
                                                 token=sc.get_token()['id']) \
                            .AndReturn(scoped)

        self.mox.ReplayAll()

        url = reverse('login')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(url, form_data)
        self.assertRedirects(response, settings.LOGIN_REDIRECT_URL)

        url = reverse('switch_tenants', args=[tenant.id])

        scoped.tenant['id'] = self.data.tenant_two._info
        sc.catalog['token']['id'] = self.data.tenant_two.id

        form_data['tenant_id'] = tenant.id
        response = self.client.get(url, form_data)

        self.assertRedirects(response, settings.LOGIN_REDIRECT_URL)
        self.assertEqual(self.client.session['tenant_id'],
                         scoped.tenant['id'])


class DjangoCompatTets(test.TestCase):
    def setUp(self):
        setattr(utils, 'datetime', datetime)
        self.mox = mox.Mox()

    def tearDown(self):
        self.mox.UnsetStubs()
        self.mox.VerifyAll()

    def test_version_check(self):
        self.mox.StubOutWithMock(django, 'get_version')
        django.get_version().AndReturn('1.3')
        self.mox.ReplayAll()

        utils_compat = reload(utils)

        self.assertEqual(utils_compat.NOW, utils._now)
        self.assertEqual(utils_compat.parse_datetime, utils._parse_datetime)

    def test_parse_ok(self):
        now = utils._now()
        nowstr = datetime.datetime.strftime(now,
                                            settings.KEYSTONE_DATETIME_FMT)

        self.assertEqual(now, utils._parse_datetime(nowstr))

    def test_parse_bad_formats(self):
        now = utils._now()
        nowstr = datetime.datetime.strftime(now,
                                            settings.KEYSTONE_DATETIME_FMT)

        with self.settings(KEYSTONE_DATETIME_FMT='%Y-%m-%dT%H:%M:%S'):
            self.assertRaises(ValueError, utils._parse_datetime, nowstr)

    def test_timezone_ok(self):
        with self.settings(KEYSTONE_TIMEZONE='utc'):
            now = utils._now()
            fmt = '%Y-%m-%dT%H:%M:%S.%fZ%Z'
            nowstr = datetime.datetime.strftime(now, fmt)
            self.assertEqual(now, utils._parse_datetime(nowstr, fmt))

    def test_timezone_error(self):
        with self.settings(KEYSTONE_TIMEZONE='utc'):
            now_aware = utils._now()

        fmt = '%Y-%m-%dT%H:%M:%S.%f'
        nowstr = datetime.datetime.strftime(now_aware, fmt)
        now_naive = utils._parse_datetime(nowstr, fmt)
        self.assertRaises(TypeError, lambda: now_aware > now_naive)
