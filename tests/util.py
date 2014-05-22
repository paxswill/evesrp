from unittest import TestCase
from evesrp import create_app, db
from evesrp.auth import AuthMethod, AuthForm, User
from wtforms.fields import StringField
from sqlalchemy.orm.exc import NoResultFound
from flask import redirect, url_for, request, render_template


class TestApp(TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.app.config['SECRET_KEY'] = 'testing'
        self.app.config['USER_AGENT_EMAIL'] = 'testing@example.com'
        self.app.config['WTF_CSRF_ENABLED'] = False
        db.create_all(app=self.app)


class NullAuthForm(AuthForm):
    name = StringField()


class NullAuth(AuthMethod):
    """A bare-bones AuthMethod that does not do any password checking."""

    def login(self, form):
        """Log in a previously registered user."""
        try:
            user = User.query.filter_by(name=form.name.data,
                    authmethod=self.name).one()
        except NoResultFound:
            return redirect(url_for('login.login'))
        self.login_user(user)
        return redirect(request.args.get('next') or url_for('index'))

    def view(self):
        """Register a User."""
        form = NullAuthForm()
        if form.validate_on_submit():
            user = User.query.filter_by(name=form.name.data,
                    authmethod=self.name).first()
            if user is None:
                user = User(form.name.data, self.name)
                db.session.add(user)
                db.session.commit()
                self.login_user(user)
                return redirect(url_for('index'))
            else:
                abort(400)
        return render_template('form.html', form=form)

    def form(self):
        return NullAuthForm


class TestLogin(TestApp):

    def setUp(self):
        super(TestLogin, self).setUp()
        self.auth_methods = [
                NullAuth(name='Null Auth 1'),
                NullAuth(name='Null Auth 2'),
        ]
        self.app.config['AUTH_METHODS'] = self.auth_methods
        self.normal_name = 'Normal User'
        self.admin_name = 'Admin User'
        with self.app.test_request_context():
            db.session.add(User(self.normal_name, self.auth_methods[0].name))
            admin_user = User(self.admin_name, self.auth_methods[0].name)
            admin_user.admin = True
            db.session.add(admin_user)
            db.session.commit()

    def login(self, username=None):
        if username is None:
            username = self.normal_name
        client = self.app.test_client()
        data = {
            'name': username,
            'submit': 'true',
        }
        auth_method = self.auth_methods[0]
        data = {auth_method.safe_name + '-' + field: value for field, value in
                data.items()}
        client.post('/login/', follow_redirects=True, data=data)
        return client
