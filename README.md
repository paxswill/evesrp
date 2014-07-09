[![Build Status](https://travis-ci.org/paxswill/evesrp.svg?branch=master)](https://travis-ci.org/paxswill/evesrp)

So, this is still in-progress, and I'm putting off writing a real readme until
it's closer to a real release. IN the mean time, here're some
[screenshots][screens]

[screens]: http://imgur.com/a/3IEQC


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

You will also need the appropriate adapter for your database of choice. For
example, I use PostgreSQL, and use the psycopg2 adapter:

    pip install psycopg2

You then need to set up the database for your application. Continuing the
example with Postgres, creating the database might look something like this:

    psql -c 'CREATE DATABASE evesrp;'

Now you need to create the configuration file. This will tell EVE-SRP how to
connect to the database, how users should log in, and other things like that.
Here's an example that will authenticate using [Brave's Core][core] that you
can build off of.

    from evesrp import Transformer
    from evesrp.auth.bravecore import BraveCore
    
    # The database connection URI. Consult the SQLAlchemy documentation for
    # more details.
    SQLALCHEMY_DATABASE_URI = 'engine://connect/args'
    
    # The secret key used to sign session cookies. Example of how to generate:
    # import os
    # os.urandom(24)
    SECRET_KEY = b'random string'
    
    # The contact email used in the user agent when accessing external APIs
    SRP_USER_AGENT_EMAIL = u'email@example.com'
    
    # Sets mechanisms users can log in.
    # Put usernames in an arrary given to the admins argument to grant
    # site-admin privileges to special users (like for initial setup).
    SRP_AUTH_METHODS = [
        BraveCore(
            private_key,
            public_key,
            identifier,
            admins=['admin_username',]),
    ]
    
    # Customize the site's title/branding
    SRP_SITE_NAME = u'Some SRP Program'

With this, you can then create the database tables for the app using the
management command. This command is installed as part of installing the EVE-SRP
package.

    evesrp -c /path/to/config.py db create

The final step is setting up the WSGI part of the app. For a super simple
solution, you can use the server built into Flask:

    from evesrp import create_app
    
    app = create_app('/path/to/config.py')
    
    if __name__ == '__main__':
        app.run()

Name the file as `wsgi.py` and you can then run it with

    python wsgi.py

Using Heroku, you can use the same `wsgi.py` file with a Procfile
like this:

    web: gunicorn wsgi:app

For a standalone Nginx+Gunicorn setup with Nginx listening on a Unix domain
socket, your gunicorn command might looks something like this:

    gunicorn --bind unix:/path/to/socket wsgi:app

For more information on how to serve a Python app using Gunicorn, check out the
[Gunicorn documentation][gunicorn-docs].

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
[gunicorn-docs]: http://docs.gunicorn.org/en/latest/index.html
[sqla-db-support]: http://docs.sqlalchemy.org/en/rel_0_9/core/engines.html#supported-databases
[psycopg2]:http://initd.org/psycopg/
