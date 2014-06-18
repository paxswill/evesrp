#!/usr/bin/env python
from setuptools import setup
import re


with open('evesrp/__init__.py', 'r') as f:
    init_contents = ''
    for line in f:
        init_contents += line + '\n'
version = re.search(r'^__version__ *= *[\'"]([^\'"]*)[\'"]', init_contents,
        re.MULTILINE)
if version:
    version = version.group(1)
else:
    raise Exception("Unable to find __version__ in evesrp/__init__.py")


setup(
    name='EVE-SRP',
    version=version,
    description='EVE Ship Replacement Program Helper',
    author='Will Ross',
    author_email='paxswill@paxswill.com',
    url='https://github.com/evesrp',
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
            'migrate/alembic.ini',
            'migrate/script.py.mako',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Flask',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Topic :: Games/Entertainment'
    ],
    dependency_links=[
        'https://github.com/bravecollective/api/tarball/develop#egg=brave.api'
    ],
    install_requires=[
        'Flask==0.10.1',
        'Flask-Login==0.2.10',
        'Flask-Migrate==1.2.0',
        'Flask-Principal==0.4.0',
        'Flask-Script==2.0.5',
        'Flask-SQLAlchemy==1.0',
        'Flask-WTF==0.9.4',
        'SQLAlchemy==0.9.3',
        'WTForms==1.0.5',
        'requests==2.2.1',
        'ecdsa==0.11',
        'brave.api'
    ],
    entry_points={
        'console_scripts': [
            'evesrp = evesrp.util.manage:main',
        ],
    },
    zip_safe=False,
)
