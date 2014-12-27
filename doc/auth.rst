**************
Authentication
**************

.. py:currentmodule:: evesrp.auth

Authentication in EVE-SRP was designed from the start to allow for multiple
different authentication systems and to make it easy to integrate it with an
existing authentication system.

As an exercise in how to write your own authentication plugin, let's write one
that doesn't rely on an external service. We'll need to subclass two classes
for this; :py:class:`AuthMethod` and :py:class:`~.User`

Let's start with subclassing :py:class:`~.User`. This class is mapped to an SQL
table using SQLAlchemy's declarative extension (more specifically, the
Flask-SQLAlchemy plugin for Flask). The parent class automatically sets up the
table name and inheritance mapper arguments for you, so all you need to do is
provide the :py:attr:`id` attribute that links your class with the parent class
and an attribute to store the password hash. In the example below, we're using
the ``simple-pbkdf2`` package to provide the password hashing. We also have a
checking method to make life easier for us later. ::

    import os
    from hashlib import sha512
    from evesrp import db
    from evesrp.auth.models import User
    from pbkdf2 import pbkdf2_bin


    class LocalUser(User):
        id = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True)
        password = db.Column(db.LargeBinary(24), nullable=False)
        salt = db.Column(db.LargeBinary(24), nullable=False)

        def __init__(self, name, password, authmethod, **kwargs):
            self.salt = os.urandom(24)
            self.password = pbkdf2_bin(password.encode('utf-8'), self.salt,
                    iterations=10000)
            super(LocalUser, self).__init__(name, authmethod, **kwargs)

        def check_password(self, password):
            key = pbkdf2_bin(password.encode('utf-8'), self.salt,
                    iterations=10000)
            matched = 0
            for a, b in zip(self.password, key):
                matched |= ord(a) ^ ord(b)
            return matched == 0

:py:class:`AuthMethod` subclasses have four methods they can implement to
customize thier behavior.

* :py:meth:`AuthMethod.form` returns a :py:class:`~.Form` subclass that
  represents the necessary fields.
* :py:meth:`AuthMethod.login` performs the actual login process. As part of
  this, it is passed an instance of the class given by
  :py:meth:`AuthMethod.form` with the submitted data via the ``form`` argument.
* For those authentication methods that requires a secondary view/route, the
  :py:meth:`AuthMethod.view` method can be implemented to handle requests made
  to ``login/safe_name`` where ``safe_name`` is the output of
  :py:attr:`AuthMethod.safe_name`\.
* Finally, the initializer should be overridden to provide a default name for
  your :py:class:`AuthMethod` other than ``Base Authentication``.
* Finally, the initializer can be overridden to handle specialized
  configurations.

With these in mind, let's implement our :py:class:`AuthMethod` subclass::

    from evesrp.auth import AuthMethod
    from flask import redirect, url_for, render_template, request
    from flask.ext.wtf import Form
    from sqlalchemy.orm.exc import NoResultFound
    from wtforms.fields import StringField, PasswordField, SubmitField
    from wtforms.validators import InputRequired, EqualTo


    class LocalLoginForm(Form):
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
            return LocalLoginForm

        def login(self, form):
            # form has already been validated, we just need to process it.
            try:
                user = LocalUser.query.filter_by(name=form.username.data).one()
            except NoResultFound:
                flash("No user found with that username.", 'error')
                return redirect(url_for('login.login'))
            if user.check_password(form.password.data):
                self.login_user(user)
                return redirect(request.args.get('next') or url_for('index'))
            else:
                flash("Incorrect password.", 'error')
                return redirect(url_for('login.login'))

        def view(self):
            form = LocalCreateUserForm()
            if form.validate_on_submit():
                user = LocalUser(form.username.data, form.password.data)
                db.session.add(user)
                db.session.commit()
                self.login_user(user)
                return redirect(url_for('index'))
            # form.html is a template included in Eve-SRP that renders all
            # elements of a form.
            return render_template('form.html', form=form)


That's all that's necessary for a very simple :py:class:`AuthMethod`. This
example cuts some corners, and isn't ready for production-level use, but
it serves as a quick example of what's necessary to write a custom
authentication method. Feel free to look at the sources for the included
:py:class:`AuthMethod`\s below to gather ideas on how to use more complicated
mechanisms.

Included Authentication Methods
===============================


.. py:module:: evesrp.auth.bravecore

Brave Core
----------

.. autoclass:: BraveCore
    :show-inheritance:

.. py:module:: evesrp.auth.testauth

TEST Legacy
-----------

.. autoclass:: TestAuth
    :show-inheritance:


.. py:module:: evesrp.auth.oauth

OAuth
-----

A number of external authentication services have an OAuth provider for
external applications to use with their API. To facilitate usage of thses
services, an :py:class:`OAuthMethod` class has been provided for easy
integration. Subclasses will need to implement the :py:meth:`~.get_user`\,
:py:meth:`~.get_pilots` and :py:meth:`~.get_groups` methods. Additionally,
implementations for :py:class:`JFLP's provider <evesrp.auth.j4oauth.J4OAuth>`
and :py:class:`TEST's provider <evesrp.auth.testoauth.TestOAuth>` have been
provided as a reference.

.. autoclass:: OAuthMethod

.. py:module:: evesrp.auth.j4oauth

J4OAuth
^^^^^^^

.. autoclass:: J4OAuth
    :show-inheritance:

.. py:module:: evesrp.auth.testoauth

TestOAuth
^^^^^^^^^

.. autoclass:: TestOAuth
    :show-inheritance:

Low-Level API
=============

.. py:module:: evesrp.auth

.. autoclass:: PermissionType

    .. py:attribute:: elevated

        Returns a :py:class:`frozenset` of the permissions above
        :py:attr:`submit`.

    .. py:attribute:: all

        Returns a :py:class:`frozenset` of all possible permission values.

.. autoclass:: AuthMethod
    :exclude-members: __weakref__

.. py:module:: evesrp.auth.models

.. autoclass:: Entity
    :exclude-members: type_

.. autoclass:: User
    :show-inheritance:

.. autoclass:: Pilot
    :exclude-members: user_id

.. autoclass:: APIKey

.. autoclass:: Note

.. autoclass:: Group
    :show-inheritance:

.. autoclass:: Permission
    :exclude-members: division_id, entity_id

.. autoclass:: Division

.. autoclass:: TransformerRef
    :exclude-members: prune_null_transformers, __init__
