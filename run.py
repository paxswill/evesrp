#!/usr/bin/env python
from heroku import app
from binascii import unhexlify

with open('.env', 'r') as f:
    for line in f:
        key, value = line.split('=', 1)
        # remove quoting and trailing newlines
        value = value.strip('"')
        value = value.rstrip('"')
        value = value.rstrip()
        # Trim newline
        value = value[:-1]
        if key == 'SECRET_KEY':
            app.config['SECRET_KEY'] = unhexlify(value)
        elif key == 'DATABASE_URL':
            app.config['SQLALCHEMY_DATABASE_URI'] = value
        elif key == 'DEBUG':
            app.debug = True

if __name__ == '__main__':
    app.extensions['sqlalchemy'].db.create_all(app=app)
    app.run()
