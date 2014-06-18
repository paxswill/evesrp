#!/usr/bin/env python

import os
import os.path
import argparse
import flask
from flask.ext import script

import evesrp

manager = script.Manager(evesrp.create_app)


class AbsolutePathAction(argparse.Action):
    """Custom argparse.Action that transforms path strings into absolute paths.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        current_absolute = os.path.abspath(os.getcwd())
        if isinstance(values, str):
            new_values = os.path.join(current_absolute, values)
        else:
            new_values = []
            for value in values:
                real_path = os.path.join(current_absolute, values)
                new_values.append(real_path)
        setattr(namespace, self.dest, new_values)


# Monkeypatch Flask-Script to consider my custom path action 'safe'
safe_actions = list(script.safe_actions)
safe_actions.append(AbsolutePathAction)
script.safe_actions = safe_actions


manager.add_option('-c', '--config', dest='config', required=True,
        action=AbsolutePathAction)


if __name__ == '__main__':
    manager.run()
