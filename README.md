[![Build Status](https://travis-ci.org/paxswill/evesrp.svg?branch=tests)](https://travis-ci.org/paxswill/evesrp)

So, this is still in-progress, and I'm putting off writing a real readme until
it's closer to a real release. IN the mean time, here're some
[screenshots][screens]

[screens]: http://imgur.com/a/3IEQC

## Dependencies

In addition to the dependencies listed in setup.py/requirements.txt, EVE-SRP
requires that these utilities be available for development:

* UglifyJS2

* LESS

Most of these are Node.js packages available from NPM:

    npm install -g uglify-js less

## Deploying

EVE-SRP is registered on PyPI, so you can install it (in a virtualenv!) like
this:

    pip install EVE-SRP

You will also need the appropriate adapter for your database of choice. For
example, I use PostgreSQL, and use the psycopg2 adapter:

    pip install psycopg2

From there, you just need to create an instance of the app and run it. The
example below uses Flask's built-in webserver.

    from evesrp import create_app
    
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'engine://connect/args'
    app.config['USER_AGENT_EMAIL'] = 'email@example.com'
    # Need to add generic AuthMethod, probably OpenID based
    app.config['AUTH_METHODS'] = [TestAuth(), ]
    app.config['SECRET_KEY'] = 'random string'
    
    if __name__ == '__main__':
        app.extensions['sqlalchemy'].db.create_all(app=app)
        app.run()
