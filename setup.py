#!/usr/bin/env python
from setuptools import setup
import re


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
            'static/css/*.css',
            'static/css/*.css.map',
            'static/js/evesrp.min.js',
            'static/js/evesrp.min.js.map',
            'static/fonts/fontawesome-webfont.*',
            'static/ZeroClipboard.swf',
            'templates/*.html',
            'templates/*.xml',
            'migrate/alembic.ini',
            'migrate/script.py.mako',
        ],
    },
    classifiers=[
        u'Development Status :: 3 - Alpha',
        u'Framework :: Flask',
        u'License :: OSI Approved :: BSD License',
        u'Programming Language :: Python :: 3',
        u'Topic :: Games/Entertainment',
    ],
    dependency_links=[
        u'https://github.com/bravecollective/api/tarball/develop#egg=brave.api'
    ],
    install_requires=[
        'Flask==0.10.1',
        'Flask-Login==0.2.10',
        'Flask-Migrate==1.2.0',
        'Flask-Script==2.0.5',
        'Flask-SQLAlchemy==1.0',
        'Flask-WTF==0.9.4',
        'SQLAlchemy==0.9.3',
        'WTForms==1.0.5',
        'requests==2.2.1',
        'ecdsa==0.11',
        'six==1.7.3',
        'brave.api',
    ],
    entry_points={
        'console_scripts': [
            'evesrp = evesrp.util.manage:main',
        ],
    },
    zip_safe=False,
)
