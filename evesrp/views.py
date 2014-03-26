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

from . import app, auth_methods, db, requests_session, killmail_sources
from .auth import SubmitRequestsPermission, ReviewRequestsPermission, \
        PayoutRequestsPermission, admin_permission
from .auth.models import User, Group, Division, Pilot
from .models import Request, Modifier, Action


@app.route('/')
@login_required
def index():
    return render_template('base.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    forms = OrderedDict()
    for auth_method in auth_methods:
        form = auth_method.form()
        forms[auth_method.name] = (form, auth_method)
    if request.method == 'POST':
        auth_tuple = forms.get(request.form['auth_method'], None)
        if auth_tuple is not None:
            form = auth_tuple[0]()
        else:
            abort(400)
        if form.validate():
            auth_method = auth_tuple[1]
            return auth_method.login(form)
    template_forms = []
    for key, value in forms.items():
        template_forms.append((key, value[0]()))
    print(template_forms)
    return render_template('login.html', forms=template_forms)


@app.route('/login/<string:auth_method>/', methods=['GET', 'POST'])
def auth_method_login(auth_method):
    method_map = dict(map(lambda m: (m.__class__.__name__.lower(), m)))
    return method_map[auth_method].view()


@app.route('/logout')
@login_required
def logout():
    logout_user()
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)
    identity_changed.send(app, identity=AnonymousIdentity())
    return redirect(url_for('index'))


@app.route('/division')
@login_required
@admin_permission.require()
def list_divisions():
    return render_template('divisions.html', divisions=Division.query.all())


class AddDivisionForm(Form):
    name = StringField('Division Name', validators=[InputRequired()])
    submit = SubmitField('Create Division')


@app.route('/division/add', methods=['GET', 'POST'])
@login_required
@admin_permission.require()
def add_division():
    form = AddDivisionForm()
    if form.validate_on_submit():
        division = Division(form.name.data)
        db.session.add(division)
        db.session.commit()
        return redirect(url_for('division_detail', division_id=division.id))
    return render_template('form.html', form=form)


@app.route('/division/<division_id>')
@login_required
@admin_permission.require()
def division_detail(division_id):
    division = Division.query.get_or_404(division_id)
    return render_template('division_detail.html', division=division)


@app.route('/division/<division_id>/<permission>')
@login_required
@admin_permission.require()
def division_permission(division_id, permission):
    division = Division.query.get_or_404(division_id)
    users = []
    for user in division.permissions[permission].individuals:
        user_dict = {
                'name': user.name,
                'id': user.id
                }
        users.append(user_dict)
    groups = []
    for group in division.permissions[permission].groups:
        group_dict = {
                'name': group.name,
                'id': group.id,
                'size': len(group.individuals)
                }
        groups.append(group_dict)
    return jsonify(name=division.name,
            groups=groups,
            users=users)


@app.route('/division/<division_id>/<permission>/add/', methods=['POST'])
@login_required
@admin_permission.require()
def division_add_entity(division_id, permission):
    division = Division.query.get_or_404(division_id)
    if request.form['entity_type'] == 'user':
        entity = User.query.filter_by(name=request.form['name']).first()
    elif request.form['entity_type'] == 'group':
        entity = Group.query.filter_by(name=request.form['name']).first()
    else:
        return abort(400)
    if entity is None:
        flash("Cannot find a {} named '{}'.".format(
            request.form['entity_type'], request.form['name']),
            category='error')
    else:
        division.permissions[permission].add(entity)
        db.session.commit()
    return redirect(url_for('division_detail', division_id=division_id))


@app.route('/division/<division_id>/<permission>/<entity>/<entity_id>/delete')
@login_required
@admin_permission.require()
def division_delete_entity(division_id, permission, entity, entity_id):
    division = Division.query.get_or_404(division_id)
    if entity == 'user':
        entity = User.query.get_or_404(entity_id)
    elif entity == 'group':
        entity = Group.query.get_or_404(entity_id)
    else:
        return abort(400)
    division.permissions[permission].remove(entity)
    db.session.commit()
    return redirect(url_for('division_detail', division_id=division_id))


class RequestListing(View):
    @property
    def template(self):
        return 'list_requests.html'

    def requests(self, division_id=None):
        raise NotImplementedError()

    def dispatch_request(self, division_id=None):
        return render_template(self.template,
                requests=self.requests(division_id))


class SubmittedRequestListing(RequestListing):
    @property
    def template(self):
        return 'list_submit.html'

    def requests(self, division_id=None):
        if division_id is not None:
            division = Division.query.get_or_404(division_id)
            return filter(lambda r: r.division == division,
                    current_user.requests)
        else:
            return current_user.requests


submit_view = login_required(
        SubmittedRequestListing.as_view('list_submit_requests'))
app.add_url_rule('/submit/', view_func=submit_view)
app.add_url_rule('/submit/<int:division_id>', view_func=submit_view)


class PermissionRequestListing(RequestListing):
    def __init__(self, permissions, filter_func):
        self.permissions = permissions
        self.filter_func = filter_func

    def requests(self, division_id):
        if division_id is not None:
            division = Division.query.get_or_404(division_id)
            for permission in self.permissions:
                if division not in current_user.divisions[self.permission]:
                    abort(403)
            else:
                divisions = [division]
        else:
            divisions = []
            for permission in self.permissions:
                divisions.extend(current_user.divisions[permission])
        requests = OrderedDict()
        for division in divisions:
            filtered = filter(self.filter_func, division.requests)
            requests.update(map(lambda r: (r, object), filtered))
        return requests.keys()


def register_perm_request_listing(endpoint, path, permissions, filter_func):
    view = PermissionRequestListing.as_view(endpoint, permissions=permissions,
            filter_func=filter_func)
    view = login_required(view)
    app.add_url_rule(path, view_func=view)
    app.add_url_rule('{}/<int:division_id>'.format(path), view_func=view)


register_perm_request_listing('list_review_requests', '/review/', ('review',),
        (lambda r: not r.finalized))
register_perm_request_listing('list_approved_requests', '/pay/', ('pay',),
        (lambda r: r.status == 'approved'))
register_perm_request_listing('list_completed_requests', '/complete/',
        ('review', 'pay'), (lambda r: r.finalized))


class RequestForm(Form):
    url = URLField('Killmail URL', validators=[InputRequired(), URL()])
    details = TextAreaField('Details', validators=[InputRequired()])
    division = SelectField('Division', coerce=int)
    submit = SubmitField('Submit')


@app.route('/submit/request', methods=['GET', 'POST'])
@login_required
def submit_request():
    form = RequestForm()
    choices = []
    for division in current_user.divisions['submit']:
        choices.append((division.id, division.name))
    form.division.choices = choices
    if form.validate_on_submit():
        # validate killmail first
        for source in killmail_sources:
            try:
                mail = source(url=form.url.data)
            except ValueError as e:
                continue
            except LookupError:
                continue
            else:
                break
        else:
            flash("Killmail URL cannot be verified", 'error')
            return render_template('form.html', form=form)
        # Prevent submitting other people's killmails
        pilot = Pilot.query.get(mail.pilot_id)
        if not pilot or pilot not in current_user.pilots:
            flash("You can only submit killmails of characters you control",
                    'warning')
            return render_template('form.html', form=form)
        # Prevent duplicate killmails
        # The name 'request' is already used by Flask.
        # Hooray name collisions!
        srp_request = Request.query.get(mail.kill_id)
        if srp_request is None:
            division = Division.query.get(form.division.data)
            srp_request = Request(current_user, mail.url, form.details.data,
                    mail.kill_id, division)
            srp_request.ship_type = mail.ship
            srp_request.pilot = pilot
            db.session.add(srp_request)
            db.session.commit()
            return redirect(url_for('request_detail', request_id=srp_request.id))
        else:
            flash("This kill has already been submitted", 'warning')
            return redirect(url_for('request_detail',
                request_id=srp_request.id))
    return render_template('form.html', form=form)


class ModifierForm(Form):
    id_ = HiddenField(default='modifier')
    value = DecimalField('Value')
    # TODO: add a validator for the type
    type_ = HiddenField(validators=[AnyOf(('rel-bonus', 'rel-deduct',
            'abs-bonus', 'abs-deduct'))])
    note = TextAreaField('Reason')


class VoidModifierForm(Form):
    id_ = HiddenField(default='void')
    modifier_id = HiddenField()
    void = SubmitField(Markup('x'))

    def __init__(self, modifier=None, *args, **kwargs):
        if modifier is not None:
            self.modifier_id = modifier.id
        super(VoidModifierForm, self).__init__(*args, **kwargs)


class PayoutForm(Form):
    id_ = HiddenField(default='payout')
    value = DecimalField('M ISK', validators=[InputRequired()])


class ActionForm(Form):
    id_ = HiddenField(default='action')
    note = TextAreaField('Note')
    type_ = HiddenField(default='comment', validators=[AnyOf(('rejected',
            'evaluating', 'approved', 'incomplete', 'paid', 'comment'))])


@app.route('/request/<int:request_id>', methods=['GET', 'POST'])
@login_required
def request_detail(request_id):
    srp_request = Request.query.get(request_id)
    if request.method == 'POST':
        submit_perm = SubmitRequestsPermission(srp_request)
        review_perm = ReviewRequestsPermission(srp_request)
        pay_perm = PayoutRequestsPermission(srp_request)
        if request.form['id_'] == 'modifier':
            form = ModifierForm()
        elif request.form['id_'] == 'payout':
            form = PayoutForm()
        elif request.form['id_'] == 'action':
            form = ActionForm()
        elif request.form['id_'] == 'void':
            form = VoidModifierForm()
        else:
            abort(400)
        if form.validate():
            if srp_request.status == 'evaluating':
                if form.id_.data == 'modifier':
                    if review_perm.can():
                        mod = Modifier(srp_request, current_user, form.note.data)
                        if form.type_.data == 'rel-bonus':
                            mod.type_ = 'percentage'
                            mod.value = form.value.data
                        elif form.type_.data == 'rel-deduct':
                            mod.type_ = 'percentage'
                            mod.value = form.value.data * -1
                        elif form.type_.data == 'abs-bonus':
                            mod.type_ = 'absolute'
                            mod.value = form.value.data
                        elif form.type_.data == 'abs-deduct':
                            mod.type_ = 'absolute'
                            mod.value = form.value.data * -1
                        db.session.add(mod)
                        db.session.commit()
                    else:
                        flash("Insufficient permissions.", 'error')
                elif form.id_.data == 'payout':
                    if review_perm.can():
                        srp_request.base_payout = form.value.data
                        db.session.commit()
                    else:
                        flash("Insufficient permissions.", 'error')
                elif form.id_.data == 'void':
                    if review_perm.can():
                        modifier = Modifier.query.get(
                                int(form.modifier_id.data))
                        modifier.void(current_user)
                        db.session.commit()
                    else:
                        flash("Insufficient permissions.", 'error')
            if form.id_.data == 'action':
                type_ = form.type_.data
                invalid = False
                if srp_request.status == 'evaluating':
                    if type_ not in ('approved', 'rejected', 'incomplete',
                            'comment'):
                        flash("Cannot go from Evaluating to Paid", 'error')
                        invalid = True
                    elif type_ != 'comment' and not review_perm.can():
                        flash("You are not a reviewer.", 'error')
                        invalid = True
                elif srp_request.status in ('incomplete', 'rejected'):
                    if type_ not in ('evaluating', 'comment'):
                        flash("Can only change to Evaluating.", 'error')
                        invalid = True
                    elif type_ != 'comment' and not review_perm.can():
                        flash("You are not a reviewer.", 'error')
                        invalid = True
                elif srp_request.status == 'approved':
                    if type_ not in ('paid', 'evaluating', 'comment'):
                        flash("Can only set to Evaluating or Paid.", 'error')
                        invalid = True
                    elif type_ == 'paid' and not pay_perm.can():
                        flash("You are not a payer.", 'error')
                        invalid = True
                    elif type_ == 'evaluating' and not review_perm.can():
                        flash("You are not a reviewer.", 'error')
                        invalid = True
                elif srp_request.status == 'paid':
                    if type_ not in ('comment', 'approved', 'evaluating'):
                        flash("""Can only move to Approved or Evaluating from
                                Paid.""", 'error')
                        invalid = True
                    elif type_ != 'comment' and not pay_perm.can():
                        flash("You are not a payer.", 'error')
                        invalid = True
                if not invalid:
                    action = Action(srp_request, current_user,
                            form.note.data)
                    action.type_ = type_
                    db.session.commit()
        else:
            # TODO: Actual error handling, probably using flash()
            print(form.errors)
    return render_template('request_detail.html', request=srp_request,
            modifier_form=ModifierForm(formdata=None),
            payout_form=PayoutForm(formdata=None),
            action_form=ActionForm(formdata=None),
            void_form=VoidModifierForm(formdata=None))
