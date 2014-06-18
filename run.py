#!/usr/bin/env python
import os
import os.path
from evesrp import create_app


config_path = os.path.join(os.path.abspath(os.getcwd()), 'config.py')
app = create_app(config_path)

with open('.env', 'r') as f:
    for line in f:
        key, value = line.split('=', 1)
        if value[-1] == '\n':
            value = value[:-1]
        app.config[key] = value

if __name__ == '__main__':
    app.extensions['sqlalchemy'].db.create_all(app=app)
    app.run()
