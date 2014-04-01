#!/usr/bin/env python
from evesrp import app
from evesrp.killmail import CRESTMail, ZKillmail, SQLShipNameMixin
import sqlite3

import config

SQLShipNameMixin.driver = sqlite3
SQLShipNameMixin.connect_args = 'rubicon.sqlite'

class SQLZKillmail(ZKillmail, SQLShipNameMixin): pass

app.config.from_object(config.Development)
app.config['USER_AGENT_EMAIL'] = 'paxswill@paxswill.com'
app.config['KILLMAIL_SOURCES'] = [CRESTMail, SQLZKillmail]

if __name__ == '__main__':
    app.run()
