from collections import OrderedDict
from urllib.parse import urlparse
import re

from flask import render_template, redirect, url_for, request, abort, jsonify,\
        flash, Markup, session
from flask.views import View
from flask.ext.login import login_user, login_required, logout_user, \
        current_user
from flask.ext.wtf import Form
from flask.ext.principal import identity_changed, AnonymousIdentity
from sqlalchemy.orm.exc import NoResultFound
from wtforms.fields import StringField, PasswordField, SelectField, \
        SubmitField, TextAreaField, HiddenField
from wtforms.fields.html5 import URLField, DecimalField
from wtforms.widgets import HiddenInput
from wtforms.validators import InputRequired, ValidationError, AnyOf, URL

from .. import app, auth_methods, db, requests_session, killmail_sources
from ..auth import SubmitRequestsPermission, ReviewRequestsPermission, \
        PayoutRequestsPermission, admin_permission
from ..auth.models import User, Group, Division, Pilot
from ..models import Request, Modifier, Action


@app.route('/')
@login_required
def index():
    return render_template('base.html')
