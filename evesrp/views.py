from collections import OrderedDict
from urllib.parse import urlparse
import re

from flask import render_template, redirect, url_for, request, abort, jsonify,\
        flash, Markup, session
from flask.ext.login import login_user, login_required, logout_user, \
        current_user
from flask.ext.wtf import Form
from flask.ext.principal import identity_changed, AnonymousIdentity
from wtforms.fields import StringField, PasswordField, SelectField, \
        SubmitField, TextAreaField, HiddenField
from wtforms.fields.html5 import URLField, DecimalField
from wtforms.widgets import HiddenInput
from wtforms.validators import InputRequired, ValidationError, AnyOf

from . import app, auth_methods, db, requests_session
from .auth import SubmitRequestsPermission, ReviewRequestsPermission, \
        PayoutRequestsPermission
from .auth.models import User, Group, Division
from .models import Request, Modifier, Action

@app.route('/')
@login_required
def index():
    return render_template('base.html')


class SelectValueField(SelectField):
    def _value(self):
        return self.default if self.default is not None else ''


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
def list_divisions():
    return render_template('divisions.html', divisions=Division.query.all())


class AddDivisionForm(Form):
    name = StringField('Division Name', validators=[InputRequired()])
    submit = SubmitField('Create Division')


@app.route('/division/add', methods=['GET', 'POST'])
@login_required
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
def division_detail(division_id):
    division = Division.query.get_or_404(division_id)
    return render_template('division_detail.html', division=division)


@app.route('/division/<division_id>/<permission>')
@login_required
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


@app.route('/submit')
@login_required
def list_submit_requests():
    requests = current_user.requests
    return render_template('list_submit.html', requests=requests)


zkb_regex = re.compile(r'/detail/(?P<kill_id>\d+)/')


def zkb_validator(domain='zkillboard.com'):
    def _validator(form, field):
        parsed = urlparse(field.data, scheme='https', allow_fragments=False)
        if parsed.netloc == '':
            # silly people, not copy-pasting the whole url
            parsed = urlparse('//' + field.data, scheme='https',
                    allow_fragments=False)
        if parsed.netloc != domain:
            print('raising domain')
            raise ValidationError("Killmail must be from {}.".format(domain))
        if not zkb_regex.match(parsed.path):
            print('raising path')
            raise ValidationError("Killmail URL must be to a zKillboard kill.")

    return _validator


crest_regex = re.compile(r'/killmails/(?P<kill_id>\d+)/[0-9a-f]+/')


def crest_validator(form, field):
    parsed = urlparse(field.data)
    if parsed.netloc != 'public-crest.eveonline.com' or \
            crest_regex.match(parsed.path):
        print('raising crest')
        raise ValidationError(
                "Must be a CREST killmail directly from the game.")


class OneOfValidator(object):
    def __init__(self, *args, message=''):
        self.validators = args
        self.message = message

    def __call__(self, form, field):
        exceptions = []
        for validator in self.validators:
            try:
                validator(form, field)
            except ValidationError as e:
                exceptions.append(e)
            else:
                return None


class RequestForm(Form):
    url = URLField('Killmail URL', validators=[OneOfValidator(
            crest_validator, zkb_validator())])
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
        # request is already used by Flask. Hooray name collisions!
        srp_request = Request(current_user, form.url.data, form.details.data)
        srp_request.division = Division.query.get(form.division.data)
        # TODO Refactor url branching to be properly configurable
        parsed_url = urlparse(form.url.data)
        if parsed_url.netloc == 'zkillboard.com':
            match = zkb_regex.match(parsed_url.path)
            kill_id = match.group('kill_id')
            srp_request.id = kill_id
            resp = requests_session.get(
                    'https://zkillboard.com/api/killID/{}'.format(kill_id))
            # TODO: actual error checking of the response
            # zKillboard wraps json in an array
            json = resp.json()[0]
            srp_request.pilot = json['victim']['characterName']
            srp_request.ship_type = json['victim']['shipTypeID']
        db.session.add(srp_request)
        db.session.commit()
        return redirect(url_for('request_detail', request_id=srp_request.id))
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
