import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.test import Client
from django.conf import settings
settings.ALLOWED_HOSTS.append('testserver')
c = Client()
resp = c.post('/password-reset/', {'email':'s88710036@gmail.com'})
print('status_code:', resp.status_code)
print('redirect:', resp.get('Location'))
print('content snippet:', resp.content[:1000])
