#!/usr/bin/env python
from evesrp import app
from evesrp.killmail import CRESTMail, ZKillmail, SQLShipMixin

import config

class SQLZKillmail(ZKillmail, SQLShipMixin('sqlite:///rubicon.sqlite')): pass

app.config.from_object(config.Development)
app.config['USER_AGENT_EMAIL'] = 'paxswill@paxswill.com'
app.config['KILLMAIL_SOURCES'] = [CRESTMail, SQLZKillmail]

if __name__ == '__main__':
    app.run()
