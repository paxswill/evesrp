#!/usr/bin/env python
from evesrp import create_app
from evesrp.killmail import CRESTMail, ShipURLMixin
import evesrp.auth.testauth
from flask.ext.heroku import Heroku
from os import environ as env
from binascii import unhexlify


skel_url = 'https://wiki.eveonline.com/en/wiki/{name}'

class EOWikiCREST(CRESTMail, ShipURLMixin(skel_url)): pass


app = create_app()
heroku = Heroku(app)
app.config['SECRET_KEY'] = unhexlify(env['SECRET_KEY'])
app.config['USER_AGENT_EMAIL'] = 'paxswill@paxswill.com'
app.config['AUTH_METHODS'] = ['evesrp.auth.testauth.TestAuth']
app.config['CORE_AUTH_PRIVATE_KEY'] = env.get('CORE_PRIVATE_KEY')
app.config['CORE_AUTH_PUBLIC_KEY'] = env.get('CORE_PUBLIC_KEY')
app.config['CORE_AUTH_IDENTIFIER'] = env.get('CORE_IDENTIFIER')
app.config['KILLMAIL_SOURCES'] = [EOWikiCREST]

if __name__ == '__main__':
    app.extensions['sqlalchemy'].db.create_all(app=app)
    app.run()
