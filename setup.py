# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from setuptools import find_packages
from setuptools import setup

data_patterns = [
    'templates/**.html',
    'static/**.jpg',
    'static/**.css',
    'static/**.js',
    'static/**.map',
    'static/**.txt',
    'static/**.eot',
    'static/**.svg',
    'static/**.ttf',
    'static/**.woff',
]

docs_patterns = [
    'docs/**.rst',
    'docs/**.py',
    'docs/**.css',
]

setup(
    name='relengapi',
    version='2.1.1',
    description='The code behind https://api.pub.build.mozilla.org',
    author='Dustin J. Mitchell',
    author_email='dustin@mozilla.com',
    url='https://api.pub.build.mozilla.org',
    install_requires=[
        "Flask",
        "Flask-Login>=0.2.11",
        "Flask-Browserid",
        "Sphinx>=1.3",
        "SQLAlchemy>=0.9.4",
        "Celery>=3.1.16",  # see https://github.com/mozilla/build-relengapi/issues/145
        "argparse",
        "requests",
        "wrapt",
        "blinker",  # required to use flask signals
        "pytz",
        "wsme",
        "croniter",
        "python-dateutil",
        "simplejson",
        "boto",
        "python-memcached",
        "elasticache-auto-discovery",
        "IPy",
        "furl",
        "redo",
        "relengapi>=0.3",
        # Temporary freeze until https://github.com/bhearsum/bzrest/pull/3 is fixed
        "bzrest==0.9",
    ],
    extras_require={
        'test': [
            'nose',
            'mock',
            'coverage',
            'pep8',
            'mockldap',
            'pyflakes',
            'moto>=0.4.1',
            'mockcache',
        ],
        # extras required only for LDAP authorization support
        'ldap': [
            'python-ldap',
        ],
    },
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    namespace_packages=['relengapi', 'relengapi.blueprints'],
    package_data={  # NOTE: these files must *also* be specified in MANIFEST.in
        'relengapi': docs_patterns,
        'relengapi.blueprints.base': data_patterns,
        'relengapi.blueprints.auth': data_patterns,
        'relengapi.blueprints.tokenauth': data_patterns,
        'relengapi.blueprints.docs': data_patterns + [
            'base/**.rst',
            'base/_static/**',
            'base/conf.py',
        ],
    },
    entry_points={
        "relengapi.blueprints": [
            'base = relengapi.blueprints.base:bp',
            'auth = relengapi.blueprints.auth:bp',
            'tokenauth = relengapi.blueprints.tokenauth:bp',
            'docs = relengapi.blueprints.docs:bp',
            'badpenny = relengapi.blueprints.badpenny:bp',
            'tooltool = relengapi.blueprints.tooltool:bp',
            'clobberer = relengapi.blueprints.clobberer:bp',
            'mapper = relengapi.blueprints.mapper:bp',
            'slaveloan = relengapi.blueprints.slaveloan:bp',
        ],
        "console_scripts": [
            'relengapi = relengapi.lib.subcommands:main',
        ],
    },
    license='MPL2',
)
