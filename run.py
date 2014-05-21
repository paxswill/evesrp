#!/usr/bin/env python
from heroku import app, configure_app

config = {}
with open('.env', 'r') as f:
    for line in f:
        key, value = line.split('=', 1)
        if value[-1] == '\n':
            value = value[:-1]
        config[key] = value

configure_app(app, config)

if __name__ == '__main__':
    app.extensions['sqlalchemy'].db.create_all(app=app)
    app.run()
