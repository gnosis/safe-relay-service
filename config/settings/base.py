"""
Base settings to build other settings files upon.
"""

import environ

ROOT_DIR = environ.Path(__file__) - 3  # (safe_relay_service/config/settings/base.py - 3 = safe-relay-service/)
APPS_DIR = ROOT_DIR.path('safe_relay_service')

env = environ.Env()

READ_DOT_ENV_FILE = env.bool('DJANGO_READ_DOT_ENV_FILE', default=False)
DOT_ENV_FILE = env('DJANGO_DOT_ENV_FILE', default=None)
if READ_DOT_ENV_FILE or DOT_ENV_FILE:
    DOT_ENV_FILE = DOT_ENV_FILE or '.env'
    # OS environment variables take precedence over variables from .env
    env.read_env(str(ROOT_DIR.path(DOT_ENV_FILE)))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool('DJANGO_DEBUG', False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = 'UTC'
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': env.db('DATABASE_URL'),
}
DATABASES['default']['ATOMIC_REQUESTS'] = True

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = 'config.urls'
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = 'config.wsgi.application'

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'django.contrib.humanize', # Handy template tags

]
THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'drf_yasg',
]
LOCAL_APPS = [
    'safe_relay_service.relay.apps.RelayConfig',
    'safe_relay_service.tokens.apps.TokensConfig',
    'safe_relay_service.gas_station.apps.GasStationConfig',
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = env('STATIC_ROOT', default=str(ROOT_DIR('staticfiles')))
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [
    str(APPS_DIR.path('static')),
]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR('media'))
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = '/media/'

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        'DIRS': [
            str(APPS_DIR.path('templates')),
        ],
        'OPTIONS': {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
            'debug': DEBUG,
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
            # https://docs.djangoproject.com/en/dev/ref/templates/api/#loader-types
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (
    str(APPS_DIR.path('fixtures')),
)

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env('DJANGO_EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL regex.
ADMIN_URL = r'^admin/'
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [
    ("""Gnosis""", 'dev@gnosis.pm'),
]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# Celery
# ------------------------------------------------------------------------------
INSTALLED_APPS += [
    'safe_relay_service.taskapp.celery.CeleryConfig',
    'django_celery_beat',
]
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-broker_url
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='django://')
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-result_backend
if CELERY_BROKER_URL == 'django://':
    CELERY_RESULT_BACKEND = 'redis://'
else:
    CELERY_RESULT_BACKEND = CELERY_BROKER_URL
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-accept_content
CELERY_ACCEPT_CONTENT = ['json']
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-task_serializer
CELERY_TASK_SERIALIZER = 'json'
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-result_serializer
CELERY_RESULT_SERIALIZER = 'json'
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-task_ignore_result
CELERY_TASK_IGNORE_RESULT = True

# Django REST Framework
# ------------------------------------------------------------------------------
REST_FRAMEWORK = {
    'PAGE_SIZE': 10,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.AllowAny',),
    'DEFAULT_RENDERER_CLASSES': (
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
    ),
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    'EXCEPTION_HANDLER': 'safe_relay_service.relay.views.custom_exception_handler',
}

# LOGGING
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#logging
# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins bon every HTTP 500 error when DEBUG=False.
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'ignore_check_url': {
            '()': 'safe_relay_service.relay.utils.IgnoreCheckUrl'
        }
    },
    'formatters': {
        'verbose': {
            'format': '%(asctime)s [%(levelname)s] [%(processName)s] %(message)s',
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        },
        'celery': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,  # If not it will be out for the root logger too
        },
        'celery.worker.strategy': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,  # If not it will be out for the root logger too
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True
        },
        'django.security.DisallowedHost': {
            'level': 'ERROR',
            'handlers': ['console', 'mail_admins'],
            'propagate': True
        },
        'django.server': {  # Gunicorn uses `gunicorn.access`
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': True,
            'filters': ['ignore_check_url'],
        },
    }
}

REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')

# Ethereum
# ------------------------------------------------------------------------------
ETH_HASH_PREFIX = env('ETH_HASH_PREFIX', default='GNO')
ETHEREUM_NODE_URL = env('ETHEREUM_NODE_URL', default=None)

GAS_STATION_NUMBER_BLOCKS = env('GAS_STATION_NUMBER_BLOCKS', default=300)

# Safe
# ------------------------------------------------------------------------------
SAFE_FUNDER_PRIVATE_KEY = env('SAFE_FUNDER_PRIVATE_KEY', default=None)
# Maximum ether (no wei) for a single transaction (security limit)
SAFE_FUNDER_MAX_ETH = env.int('SAFE_FUNDER_MAX_ETH', default=0.1)
SAFE_FUNDING_CONFIRMATIONS = env.int('SAFE_FUNDING_CONFIRMATIONS', default=0)  # Set to at least 3
# Master Copy Address of Safe Contract
SAFE_CONTRACT_ADDRESS = env('SAFE_CONTRACT_ADDRESS', default='0x34CfAC646f301356fAa8B21e94227e3583Fe3F5F')
SAFE_V1_0_0_CONTRACT_ADDRESS = env('SAFE_V1_0_0_CONTRACT_ADDRESS', default='0xb6029EA3B2c51D09a50B53CA8012FeEB05bDa35A')
SAFE_V0_0_1_CONTRACT_ADDRESS = env('SAFE_V0_0_1_CONTRACT_ADDRESS', default='0x8942595A2dC5181Df0465AF0D7be08c8f23C93af')
SAFE_VALID_CONTRACT_ADDRESSES = set(env.list('SAFE_VALID_CONTRACT_ADDRESSES',
                                             default=['0xaE32496491b53841efb51829d6f886387708F99B',
                                                      '0xb6029EA3B2c51D09a50B53CA8012FeEB05bDa35A',
                                                      '0x8942595A2dC5181Df0465AF0D7be08c8f23C93af',
                                                      '0xAC6072986E985aaBE7804695EC2d8970Cf7541A2'])
                                    ) | {SAFE_CONTRACT_ADDRESS,
                                         SAFE_V1_0_0_CONTRACT_ADDRESS,
                                         SAFE_V0_0_1_CONTRACT_ADDRESS}
SAFE_PROXY_FACTORY_ADDRESS = env('SAFE_PROXY_FACTORY_ADDRESS', default='0x76E2cFc1F5Fa8F6a5b3fC4c8F4788F0116861F9B')
SAFE_PROXY_FACTORY_V1_0_0_ADDRESS = env('SAFE_PROXY_FACTORY_V1_0_0_ADDRESS',
                                        default='0x12302fE9c02ff50939BaAaaf415fc226C078613C')
SAFE_DEFAULT_CALLBACK_HANDLER = env('SAFE_DEFAULT_CALLBACK_HANDLER',
                                    default='0xd5D82B6aDDc9027B22dCA772Aa68D5d74cdBdF44')

# If FIXED_GAS_PRICE is None, GasStation will be used
FIXED_GAS_PRICE = env.int('FIXED_GAS_PRICE', default=None)
SAFE_TX_SENDER_PRIVATE_KEY = env('SAFE_TX_SENDER_PRIVATE_KEY', default=None)

SAFE_CHECK_DEPLOYER_FUNDED_DELAY = env.int('SAFE_CHECK_DEPLOYER_FUNDED_DELAY', default=1 * 30)
SAFE_CHECK_DEPLOYER_FUNDED_RETRIES = env.int('SAFE_CHECK_DEPLOYER_FUNDED_RETRIES', default=10)
SAFE_FIXED_CREATION_COST = env.int('SAFE_FIXED_CREATION_COST', default=None)
SAFE_ACCOUNTS_BALANCE_WARNING = env.int('SAFE_ACCOUNTS_BALANCE_WARNING', default=200000000000000000)  # 0.2 Eth
SAFE_TX_NOT_MINED_ALERT_MINUTES = env('SAFE_TX_NOT_MINED_ALERT_MINUTES', default=10)

NOTIFICATION_SERVICE_URI = env('NOTIFICATION_SERVICE_URI', default=None)
NOTIFICATION_SERVICE_PASS = env('NOTIFICATION_SERVICE_PASS', default=None)

TOKEN_LOGO_BASE_URI = env('TOKEN_LOGO_BASE_URI', default='https://gnosis-safe-token-logos.s3.amazonaws.com/')
TOKEN_LOGO_EXTENSION = env('TOKEN_LOGO_EXTENSION', default='.png')

# Notifications
SLACK_API_WEBHOOK = env('SLACK_API_WEBHOOK', default=None)

# Infura
INFURA_NODE_URL = env('INFURA_NODE_URL', default=None)
INFURA_RELAY_SENDER_PRIVATE_KEY = env('INFURA_RELAY_SENDER_PRIVATE_KEY', default=SAFE_TX_SENDER_PRIVATE_KEY)
