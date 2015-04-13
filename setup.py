#!/usr/bin/env python
from setuptools import setup
import re
import sys


with open('evesrp/__init__.py', 'r') as f:
    init_contents = ''
    for line in f:
        init_contents += line + '\n'
version = re.search(r'^__version__ *= *u?[\'"]([^\'"]*)[\'"]', init_contents,
        re.MULTILINE)
if version:
    version = version.group(1)
else:
    raise Exception(u"Unable to find __version__ in evesrp/__init__.py")


test_requirements = [
    'beautifulsoup>=4.3.2',
    'coverage>=3.7.1',
    'httmock>=1.2.2',
]
# unittest.mock was added in 3.3, but is available as a backport as the 'mock'
# package on PyPI.
if sys.version_info.major < 3 or sys.version_info.minor < 3:
    test_requirements.append('mock>=1.0.1')


setup(
    name=u'EVE-SRP',
    version=version,
    description=u'EVE Ship Replacement Program Helper',
    author=u'Will Ross',
    author_email=u'paxswill@paxswill.com',
    url=u'https://github.com/paxswill/evesrp',
    packages=[
        'evesrp',
        'evesrp.auth',
        'evesrp.views',
        'evesrp.util',
        'evesrp.migrate',
        'evesrp.migrate.versions',
    ],
    package_data={
        'evesrp': [
            'static/favicon.ico',
            'static/evesso.png',
            'static/css/*.css',
            'static/css/*.css.map',
            'static/js/evesrp.min.js',
            'static/js/evesrp.min.js.map',
            'static/ZeroClipboard.swf',
            'templates/*.html',
            'templates/*.xml',
            'migrate/alembic.ini',
            'migrate/script.py.mako',
        ],
    },
    classifiers=[
        u'Development Status :: 4 - Beta',
        u'Framework :: Flask',
        u'License :: OSI Approved :: BSD License',
        u'Programming Language :: Python :: 3',
        u'Programming Language :: Python :: 2',
        u'Topic :: Games/Entertainment',
    ],
    install_requires=[
        'Flask>=0.10.1',
        'Flask-Login>=0.2.11',
        'Flask-Migrate>=1.2.0',
        'Flask-Script==2.0.5',
        'Flask-SQLAlchemy==2.0',
        'Flask-WTF==0.10.2',
        'SQLAlchemy>=0.9.7',
        'Werkzeug>=0.9.4',
        'WTForms>=2.0.0',
        'alembic>=0.6.5',
        'requests==2.2.1',
        'six==1.7.3',
        'iso8601>=0.1.5',
    ],
    test_suite='tests',
    test_require=test_requirements,
    entry_points={
        'console_scripts': [
            'evesrp = evesrp.util.manage:main',
        ],
    },
    extras_require={
        'BraveCore': [
            'braveapi==0.1',
            'ecdsa==0.11',
        ],
        'OAuth': [
            'Flask-OAuthlib>=0.7.0',
        ],
    },
    zip_safe=False,
)
