Authentication in EVE-SRP
=========================

Authentication in EVE-SRP was designed from the start to allow for multiple
different authentication systems and to make it easy to integrate it with an
existing authentication system.

As an exercise in how to write your own authentication plugin, let's write one
that doesn't rely on an external service. There are four classes to override
for your authentication plugin, :py:class:`User`, :py:class:`Group`,
:py:class:`AuthPlugin` and :py:class:`AuthForm`.

Let's start with subclassing :py:class:`User`. This class is mapped to an SQL
table using SQLAlchemy's declarative extension (more specifically, the
Flask-SQLAlchemy plugin to Flask). The parent class automatically sets up the
table name and inheritance mapper arguments for you, so all you need to do is
provide the :py:attr:`id` attribute that links your class with the parent class
and an attribute to store the password hash.::

    from evesrp.auth import User


    class LocalUser(User):
        id = db.Column(db.Integer, db.ForeignKey('user.id', primary_key=True)
        password = db.Column(db.String(256), nullable=False)

        @classmethod
        def authmethod(cls):
            return LocalAuth

In addition, we override :py:meth:`User.authmethod` to tell which authentication
method class to use for the actual login process.

:py:class:`AuthMethod` subclasses have three and a half methods they can
subclass to customize themselves. The :py:meth:`AuthMethod.__init__` method is passed an
instance of the configuration dictionary to allow greater flexibility in
configuration. :py:meth:`AuthMethod.form` returns the :py:class:`AuthForm` subclass that
represents the necessary fields. :py:meth:`AuthMethod.login` is performs the actual
login process. As part of this, it is passed an instance of the class given by
:py:meth:`AuthMethod.form` with the submitted data via the form argument. Finally, some
login methods need a secondary view, for example, OpenID needs a destination to
redirect to and process the arguments passed to along with the redirect. The
:py:meth:`AuthMethod.view` method is an optional method for AuthMethod subclasses to
implement. It can be accessed at /login/<AuthMethod.__name__.lower()> and
accepts the GET and POST HTTP verbs.
