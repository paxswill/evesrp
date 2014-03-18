#!/usr/bin/env python
from evesrp import app

import config

app.config.from_object(config.Config)
app.run()
