Authentication
==============

.. py:currentmodule:: evesrp.auth

Authentication in EVE-SRP was designed from the start to allow for multiple
different authentication systems and to make it easy to integrate it with an
existing authentication system.

As an exercise in how to write your own authentication plugin, let's write one
that doesn't rely on an external service. There are four classes to override
for your authentication plugin, :py:class:`User`, :py:class:`Group`,
:py:class:`AuthMethod` and :py:class:`AuthForm`.

Let's start with subclassing :py:class:`User`. This class is mapped to an SQL
table using SQLAlchemy's declarative extension (more specifically, the
Flask-SQLAlchemy plugin to Flask). The parent class automatically sets up the
table name and inheritance mapper arguments for you, so all you need to do is
provide the :py:attr:`id` attribute that links your class with the parent class
and an attribute to store the password hash. In the example, we're using the
pbkdf2 package to provide the password hashing. We also have a checking method
to make life easier for us later. ::

    from evesrp import db
    from evesrp.auth import User
    from pbkdf2 import pbkdf2_bin


    class LocalUser(User):
        id = db.Column(db.Integer, db.ForeignKey('user.id', primary_key=True))
        password = db.Column(db.LargeBinary(256), nullable=False)
        salt = db.Column(db.LargeBinary(256), nullable=False)

        def __init__(self, username, password):
            self.name = username
            self.salt = None
            self.password = pbkdf2_bin(password.encode('utf-8'), self.salt,
                    iterations=100000)

        def check_password(self, password):
            key = pbkdf2_bin(password.encode('utf-8'), self.salt,
                    iterations=100000)
            matched = 0
            for a, b in zip(self.password, key):
                matched |= ord(a) ^ ord(b)
            return matched == 0

        @classmethod
        def authmethod(cls):
            return LocalAuth

In addition, we override :py:meth:`User.authmethod` to tell which
authentication method class to use for the actual login process.

:py:class:`AuthMethod` subclasses have three and a half methods they can
subclass to customize themselves. The :py:meth:`AuthMethod.__init__` method is
passed an instance of the configuration dictionary to allow greater flexibility
in configuration. :py:meth:`AuthMethod.form` returns the :py:class:`AuthForm`
subclass that represents the necessary fields. :py:meth:`AuthMethod.login`
performs the actual login process. As part of this, it is passed an instance of
the class given by :py:meth:`AuthMethod.form` with the submitted data via the
``form`` argument. Finally, some login methods need a secondary view, for
example,
OpenID needs a destination to redirect to and process the arguments passed to
along with the redirect. The :py:meth:`AuthMethod.view` method is an optional
method AuthMethod subclasses can implement to process/present a secondary
view. It can be accessed at /login/<AuthMethod.__name__.lower()> and accepts
the GET and POST HTTP verbs. ::

    from evesrp.auth import AuthForm, AuthMethod
    from flask import redirect, url_for
    from flask.ext.wtf import Form
    from sqlalchemy.orm.exc import NoResultFound
    from wtforms.fields import StringField, PasswordField, SubmitField
    from wtforms.validators import InputRequired, EqualTo


    class LocalLoginForm(AuthForm):
        username = StringField('Username', validators=[InputRequired()])
        password = PasswordField('Password', validators=[InputRequired()])
        submit = SubmitField('Log In')


    class LocalCreateUserForm(Form):
        username = StringField('Username', validators=[InputRequired()])
        password = PasswordField('Password', validators=[InputRequired(),
                EqualTo('password_repeat', message='Passwords must match')])
        password_repeat = PasswordField(
                'Repeat Password', validators=[InputRequired()])
        submit = SubmitField('Log In')


    class LocalAuth(AuthMethod):
        def form(self):
            return LocalLoginForm()

        def login(self, form):
            # form has already been validated
            try:
                user = LocalUser.query.filter_by(name=form.username.data).one()
            except NoResultFound:
                flash("No user found with that username.", 'error')
                return redirect(url_for('login.login'))
            if user.check_password(form.password.data):
                self.login_user(user)
                redirect(request.args.get('next') or url_for('index'))
            else:
                flash("Incorrect password.", 'error')
                redirect(url_for('login.login'))

        def view(self):
            form = LocalCreateUserForm()
            if form.validate_on_submit():
                user = LocalUser(form.username.data, form.password.data)
                db.session.add(user)
                db.session.commit()
                self.login_user(user)
                return redirect(url_for('index'))
            return render_template('form.html', form=form)

API Documentation
*****************

.. py:module:: evesrp.auth

.. autoclass:: AuthMethod
    :exclude-members: __weakref__

.. autoclass:: User
    :exclude-members: individual_permissions, permissions, user_type

.. autoclass:: Group
    :exclude-members: group_type, permissions

.. autoclass:: Division
    :exclude-members: permissions

.. py:module:: evesrp.auth.models

.. autoclass:: Pilot
    :exclude-members: user_id

.. py:module:: evesrp.auth.testauth

.. autoclass:: TestAuth

.. autoclass:: TestAuthUser

.. autoclass:: TestAuthGroup

.. py:module:: evesrp.auth.bravecore

.. autoclass:: BraveCore

.. autoclass:: BraveCoreUser

.. autoclass:: BraveCoreGroup
