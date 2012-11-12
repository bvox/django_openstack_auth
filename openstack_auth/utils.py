import datetime

import django
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import middleware
from django.core import exceptions

try:
    import pytz
except ImportError:
    # Handle elsewhere
    pytz = None

def _now():
    """
    Returns an aware or naive datetime.datetime, depending on
    settings.KEYSTONE_TIMEZONE. Adaptation from Django 1.4 util.
    """
    if settings.KEYSTONE_TIMEZONE:
        # timeit shows that datetime.now(tz=utc) is 24% slower
        zone = pytz.timezone(settings.KEYSTONE_TIMEZONE)
        return datetime.datetime.now().replace(tzinfo=zone)
    else:
        return datetime.datetime.now()


def _parse_datetime(value, fmt=None):
    if not fmt:
        fmt = settings.KEYSTONE_DATETIME_FMT
    result = datetime.datetime.strptime(value, fmt)
    if settings.KEYSTONE_TIMEZONE:
        # timeit shows that datetime.now(tz=utc) is 24% slower
        zone = pytz.timezone(settings.KEYSTONE_TIMEZONE)
        return result.replace(tzinfo=zone)
    return result


def _check_compat(error=None):
    messages = []
    if error:
        messages.append(error)
    for setting in ('KEYSTONE_TIMEZONE', 'KEYSTONE_DATETIME_FMT'):
        try:
            getattr(settings, setting)
        except AttributeError:
            messages.append('You must define %s on your settings'
                            % setting)
    if messages:
        raise exceptions.ImproperlyConfigured(
            'In order to get Django 1.3 backwards compatibility you need:\n%s'
            % '\n'.join(messages))


if django.get_version() >= '1.4':
    from django.utils import timezone
    from django.utils.dateparse import parse_datetime
    NOW = timezone.now
else:
    # We are under Django < 1.4
    error = 'pytz must be installed' if not pytz else False
    _check_compat(error)
    parse_datetime = _parse_datetime
    # Djngo 1.3.1 doesn't define it
    settings.USE_TZ = False
    NOW = _now


"""
We need the request object to get the user, so we'll slightly modify the
existing django.contrib.auth.get_user method. To do so we update the
auth middleware to point to our overridden method.

Calling the "patch_middleware_get_user" method somewhere like our urls.py
file takes care of hooking it in appropriately.
"""


def middleware_get_user(request):
    if not hasattr(request, '_cached_user'):
        request._cached_user = get_user(request)
    return request._cached_user


def get_user(request):
    try:
        user_id = request.session[auth.SESSION_KEY]
        backend_path = request.session[auth.BACKEND_SESSION_KEY]
        backend = auth.load_backend(backend_path)
        backend.request = request
        user = backend.get_user(user_id) or AnonymousUser()
    except KeyError:
        user = AnonymousUser()
    return user


def patch_middleware_get_user():
    middleware.get_user = middleware_get_user
    auth.get_user = get_user


""" End Monkey-Patching. """


def check_token_expiration(token):
    """ Timezone-aware checking of the auth token's expiration timestamp.

    Returns ``True`` if the token has not yet expired, otherwise ``False``.
    """
    expiration = parse_datetime(token.expires)
    if settings.USE_TZ and timezone.is_naive(expiration):
        # Presumes that the Keystone is using UTC.
        expiration = timezone.make_aware(expiration, timezone.utc)
    # In case we get an unparseable expiration timestamp, return False
    # so you can't have a "forever" token just by breaking the expires param.
    if expiration:
        return expiration > NOW()
    else:
        return False


def mockdecorator():
    '''Mocks decorators just returning decorated object.'''
    return lambda func: func
