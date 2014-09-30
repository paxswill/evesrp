#!/usr/bin/env python
import os.path
from evesrp import create_app


app = create_app(instance_path=os.path.abspath(os.path.dirname(__file__)))


if __name__ == '__main__':
    app.run()
