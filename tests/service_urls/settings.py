SECRET_KEY = 'secret'

DATABASES = {
    'default': 'sqlite://:memory:',
    'postgresql': 'postgres://uf07k1i6d8ia0v:@:5435/d8r82722r2kuvn',
    'mysql': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'd8r82722r2kuvn',
        'HOST': 'ec2-107-21-253-135.compute-1.amazonaws.com',
        'USER': 'uf07k1i6d8ia0v',
        'PASSWORD': 'wegauwhgeuioweg',
        'PORT': 3306,
    },
}

CACHES = {
    'default': 'memory://',
    'dummy': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    },
    'memcached': 'memcached://1.2.3.4:1567,1.2.3.5:1568',
}

EMAIL_BACKEND = 'smtps://user:passwd@localhost:465'
