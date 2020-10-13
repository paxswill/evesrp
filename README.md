## Project Status
I've been winning at Eve for a few years now (translation for non-players:
"winning Eve" means not playing), and haven't been working on this in that time
either. If anyone would like to continue development themselves, I'd be more than
happy to transfer this repo into an organization and point people there.

[![Build Status](https://travis-ci.org/paxswill/evesrp.svg?branch=master)](https://travis-ci.org/paxswill/evesrp)
[![Documentation Status](https://readthedocs.org/projects/eve-srp/badge/?version=master)](https://readthedocs.org/projects/eve-srp/?badge=master)
[![Coverage Status](https://coveralls.io/repos/paxswill/evesrp/badge.svg?branch=master&service=github)](https://coveralls.io/github/paxswill/evesrp?branch=master)

So, this is still in-progress, and I'm putting off writing a real readme until
it's closer to a real release. IN the mean time, here're some
[screenshots][screens]

[screens]: http://imgur.com/a/3IEQC

## Acknowledgements

In addition to the libraries this project uses, I need to thank the Eve
alliances Test Alliance Please Ignore and Brave. This app was originally
written as a replacement for Test's old SRP app, but Brave ended up needing
one before we were ready to deploy it for Test. Brave's early IT team and
alliance members were great "beta" testers, making suggestions that improved
the app in a myriad of ways.

A very large thank you to [Galaxy Android][galaxy-android] as well for alerting
me to a security vulnerability that was fixed in v0.12.12.

[galaxy-android]: https://evewho.com/character/92317068
## Developing

### Dependencies

In addition to the dependencies listed in setup.py/requirements.txt, EVE-SRP
depends on a Javascript packages. A couple of them are Node.js command line
utilities (UglifyJS2, LESS), but the majority are used as part of the user
interface. To install all development dependencies at once you can use the
`build-deps` make target:

    make build-deps

This will install all of the Python and Javascript dependencies needed for
developing EVE-SRP.
After you've installed the dependencies, you'll need to generate the CSS and
Javascript sources.

    make all

If the Javascript minimization is causing a problem, you can disable it by
defining the `DEBUG` variable for make.

    DEBUG="true" make all

To run the development server, you can use the included `evesrp` command line
utility. I recommend installing the project in editable mode to get access to
it.

    ./setup.py develop
    evesrp -c config.py runserver

## Deploying

If all you want to do is run EVE-SRP, you can skip the steps above and install
it from PyPI (in a virtualenv!) like this:

    pip install EVE-SRP

If you're planning on using either the Brave Core or one of the OAuth-based
authentication mechanisms, you'll need to install either of those options like
so:

    pip install EVE-SRP[BraveCore]

or

    pip install EVE-SRP[OAuth,BraveCore]

Quick Side Note: If your system has an older version of pip (<6.0) or
setuptools (<8.0) you will need to update them.

You will also need the appropriate adapter for your database of choice. For
example, I use PostgreSQL, and use the psycopg2 adapter:

    pip install psycopg2

You then need to set up the database for your application. Continuing the
example with Postgres, creating the database might look something like this:

    psql -c 'CREATE DATABASE evesrp;'

Now you need to create the configuration file. This will tell EVE-SRP how to
connect to the database, how users should log in, and other things like that.
There's an example of an instance folder using [Brave's Core][core] and
Test's OAuth provider for authentication with customized killmail processing
in the 'examples' folder in the repository ([browsable][examples] through
GitHub).

With an instance folder set up like the example, you can then create the
database tables for the app using the management command. This command is
installed as part of installing the EVE-SRP package.

    evesrp -i /path/to/instance/folder/ db create

The final step is setting up the WSGI part of the app. For a super simple
solution, you can use the server built into Flask. The `run.py` file in the
'examples' folder is setup to work like this. This server is **not** meant for
production use, and is only good for verifying that things work.

Using Heroku, you can use the same `run.py` file with a Procfile
like this:

    web: gunicorn run:app

For a standalone Nginx+uWSGI setup with Nginx listening on a Unix domain
socket, your uwsgi command might looks something like this:

    uwsgi -s /path/to/uwsgi.sock -H /path/to/virtualenv -w run:app

For more information on how to serve a Python app using Gunicorn, check out 
Flask's documentation on [deployment][flask-deploy].

### Dependencies

EVE-SRP requires Python 2.7 or >=3.3 and a database (with connector) that is
supported by [SQLAlchemy][sqla-db-support]. EVE-SRP is typically developed
against PostgreSQL with the [psycopg2][psycopg2] adapter. It is also tested
regularly with the following database adapters:

* [pg8000](https://pypi.python.org/pypi/pg8000/)
* [CyMySQL](https://pypi.python.org/pypi/cymysql)
* [PyMySQL](https://pypi.python.org/pypi/PyMySQL)
* [MySQL-Python](https://pypi.python.org/pypi/MySQL-python) (Python 2.7 only)

[core]: https://github.com/bravecollective/core
[examples]: https://github.com/paxswill/evesrp/tree/master/example
[flask-deploy]: http://flask.pocoo.org/docs/0.10/deploying/
[sqla-db-support]: http://docs.sqlalchemy.org/en/rel_0_9/core/engines.html#supported-databases
[psycopg2]:http://initd.org/psycopg/
