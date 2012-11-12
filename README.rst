=====================
Django OpenStack Auth
=====================

Django OpenStack Auth is a pluggable Django authentication backend that
works with Django's ``contrib.auth`` framework to authenticate a user against
OpenStack's Keystone Identity API.

The current version is designed to work with the Keystone V2 API.

You can `view the documentation`_ on Read The Docs.

.. _view the documentation: http://django-openstack-auth.readthedocs.org/en/latest/

Installation
============

Installing is quick and easy:

#. Run ``pip install django_openstack_auth``.

#. Add ``openstack_auth`` to ``settings.INSTALLED_APPS``.

#. Add ``'keystone_auth.backend.KeystoneBackend'`` to your
   ``settings.AUTHENTICATION_BACKENDS``, e.g.::

        AUTHENTICATION_BACKENDS = ('keystone_auth.backend.KeystoneBackend',)

#. Configure your API endpoint(s) in ``settings.py``::

        OPENSTACK_KEYSTONE_URL = "http://example.com:5000/v2.0"

#. Include ``'keystone_auth.urls'`` somewhere in your ``urls.py`` file.

#. Use it as you would any other Django auth backend.

Django 1.3.1 compatibility
--------------------------

In case you need Django 1.3.1+ then you need some extra steps:

#. Install pytz

#. Add to your settings::

    KEYSTONE_TIMEZONE = None
    KEYSTONE_DATETIME_FMT = '%Y-%m-%dT%H:%M:%S.%f'

   Where the first setting is Keystone token's time zone (None in case they are,
   time zone aware) and the latter is the format string for parsing the tokens.

Running The Tests
=================

Download the repository and run::

    python setup.py test
