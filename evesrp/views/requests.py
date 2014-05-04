from collections import OrderedDict
from itertools import groupby

from flask import render_template, abort, url_for, flash, Markup, request,\
    redirect, current_app, Blueprint
from flask.views import View
from flask.ext.login import login_required, current_user
from flask.ext.wtf import Form
from wtforms.fields import SelectField, SubmitField, TextAreaField, HiddenField
from wtforms.fields.html5 import URLField, DecimalField
from wtforms.validators import InputRequired, AnyOf, URL, ValidationError,\
        StopValidation

from .. import db
from ..models import Request, Modifier, Action
from ..auth import SubmitRequestsPermission, ReviewRequestsPermission, \
        PayoutRequestsPermission, admin_permission
from ..auth.models import Division, Pilot, Permission, User, Group


blueprint = Blueprint('requests', __name__)


class RequestListing(View):
    """Abstract class for lists of :py:class:`~evesrp.models.Request`\s.
    """

    #: The template to use for listing requests
    template = 'list_requests.html'

    decorators = [login_required]

    def requests(self, division_id=None):
        """Returns a list :py:class:`~.Request`\s belonging to
        the specified :py:class:`~.Division`, or all divisions if
        ``None``. Must be implemented by subclasses, as this is an abstract
        method.

        :param int division_id: ID number of a :py:class:`~.Division`, or
            ``None``.
        :returns: :py:class:`~.models.Request`\s
        :rtype: iterable
        """
        raise NotImplementedError()

    def dispatch_request(self, division_id=None, page=1):
        """Returns the response to requests.

        Part of the :py:class:`flask.views.View` interface.
        """
        pager = self.requests(division_id).paginate(page, per_page=20)
        return render_template(self.template,
                pager=pager)

    @property
    def _load_options(self):
        """Returns a sequence of
        :py:class:`~sqlalchemy.orm.strategy_options.Load` objects specifying
        which attributes to load (or really any load options necessary).
        """
        return (
                db.Load(Request).load_only('id', 'pilot_id', 'division_id',
                    'system', 'ship_type', 'status', 'timestamp',
                    'base_payout'),
                db.Load(Division).joinedload('name'),
                db.Load(Pilot).joinedload('name'),
        )


class SubmittedRequestListing(RequestListing):
    """A requests listing with a button for submitting requests at the bottom.

    It will show all requests the current user has submitted. The button links
    to :py:func:`submit_request`.
    """

    template = 'list_submit.html'

    def requests(self, division_id=None):
        requests = Request.query\
                .join(User)\
                .filter(User.id==current_user.id)\
                .options(*self._load_options)
        if division_id is not None:
            requests = requests.filter(Request.division_id==division_id)
        requests = requests.order_by(Request.timestamp.desc())
        return requests


class PermissionRequestListing(RequestListing):
    """Show all requests that the current user has permissions to access.

    This is used for the various permission-specific views.
    """

    def __init__(self, permissions, statuses):
        """Create a :py:class:`PermissionRequestListing` for the given
        permissions and statuses.

        :param tuple permissions: The permissions to filter by
        :param tuple statuses: A tuple of valid statuses for requests to be in
        """
        self.permissions = permissions
        self.statuses = statuses

    def requests(self, division_id=None):
        user_perms = db.session.query(Permission.id.label('permission_id'),
                Permission.division_id.label('division_id'),
                Permission.permission.label('permission'))\
                .filter(Permission.entity==current_user)
        group_perms = db.session.query(Permission.id.label('permission_id'),
                Permission.division_id.label('division_id'),
                Permission.permission.label('permission'))\
                .join(Group)\
                .filter(Group.users.contains(current_user))
        perms = user_perms.union(group_perms)\
                .filter(Permission.permission.in_(self.permissions))
        if division_id is not None:
            perms = perms.filter(Permission.division_id==division_id)
        perms = perms.subquery()
        requests = Request.query\
                .join(perms, Request.division_id==perms.c.division_id)\
                .filter(Request.status.in_(self.statuses))\
                .order_by(Request.timestamp.desc())\
                .options(*self._load_options)
        return requests


def register_perm_request_listing(app, endpoint, path, permissions, statuses):
    """Utility function for creating :py:class:`PermissionRequestListing`
    views.

    :param app: The application to add the view to
    :type app: :py:class:`flask.Flask`
    :param str endpoint: The name of the view
    :param str path: The URL path for the view
    :param tuple permissions: Passed to
        :py:meth:`PermissionRequestListing.__init__`
    :param callable statuses: Passed to
        :py:meth:`PermissionRequestListing.__init__`
    """
    view = PermissionRequestListing.as_view(endpoint, permissions=permissions,
            statuses=statuses)
    app.add_url_rule(path, view_func=view)
    app.add_url_rule('{}<int:page>/'.format(path), view_func=view)
    app.add_url_rule('{}<int:page>/<int:division_id>'.format(path),
            view_func=view)


@blueprint.record
def register_class_views(state):
    """Register class based views onto the requests blueprint."""
    submit_view = SubmittedRequestListing.as_view('list_submit_requests')
    state.add_url_rule('/submit/', view_func=submit_view)
    state.add_url_rule('/submit/<int:page>/', view_func=submit_view)
    state.add_url_rule('/submit/<int:page>/<int:division_id>', view_func=submit_view)
    register_perm_request_listing(state, 'list_review_requests',
            '/review/', ('review',), ('evaluating', 'incomplete', 'approved'))
    register_perm_request_listing(state, 'list_approved_requests',
            '/pay/', ('pay',), ('approved',))
    register_perm_request_listing(state, 'list_completed_requests',
            '/complete/', ('review', 'pay'), ('rejected', 'paid'))


class ValidKillmail(URL):
    def __init__(self, mail_class, **kwargs):
        self.mail_class = mail_class
        super(ValidKillmail, self).__init__(**kwargs)

    def __call__(self, form, field):
        super(ValidKillmail, self).__call__(form, field)
        try:
            mail = self.mail_class(field.data)
        except ValueError as e:
            raise ValidationError(str(e)) from e
        except LookupError as e:
            raise ValidationError(str(e)) from e
        else:
            if mail.verified:
                form.killmail = mail
                raise StopValidation


def get_killmail_validators():
    """Delay accessing current_app until in a request context."""
    validators = [ValidKillmail(s) for s in current_app.killmail_sources]
    validators.append(InputRequired())
    return validators


class RequestForm(Form):
    url = URLField('Killmail URL')
    details = TextAreaField('Details', validators=[InputRequired()])
    division = SelectField('Division', coerce=int)
    submit = SubmitField('Submit')

    def validate_url(form, field):
        failures = set()
        for v in get_killmail_validators():
            try:
                v(form, field)
            except ValidationError as e:
                failures.add(str(e))
            else:
                continue
        else:
            raise ValidationError([str(e) for e in failures])


@blueprint.route('/add/', methods=['GET', 'POST'])
@login_required
def submit_request():
    """Submit a :py:class:`~.models.Request`\.

    Displays a form for submitting a request and then processes the submitted
    information. Verifies that the user has the appropriate permissions to
    submit a request for the chosen division and that the killmail URL given is
    valid. Also enforces that the user submitting this requests controls the
    character from the killmail and prevents duplicate requests.
    """
    if not current_user.has_permission('submit'):
        abort(403)
    form = RequestForm()
    # Create a list of divisions this user can submit to
    submit_perms = current_user.permissions\
            .filter_by(permission='submit')\
            .subquery()
    divisions = db.session.query(Division).join(submit_perms)
    # Remove duplicates and sort divisions by name
    keyfunc = lambda d: d.name
    divisions = sorted(divisions, key=keyfunc)
    choices = []
    for name, group in groupby(divisions, keyfunc):
        choices.append((next(group).id, name))
    form.division.choices = choices
    if form.validate_on_submit():
        mail = form.killmail
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
            srp_request = Request(current_user, form.details.data, division,
                    mail)
            srp_request.pilot = pilot
            db.session.add(srp_request)
            db.session.commit()
            return redirect(url_for('.request_detail',
                request_id=srp_request.id))
        else:
            flash("This kill has already been submitted", 'warning')
            return redirect(url_for('.request_detail',
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


@blueprint.route('/<int:request_id>/', methods=['GET', 'POST'])
@login_required
def request_detail(request_id):
    """Renders the detail page for a :py:class:`~.models.Request`\.

    This function is currently used for `all` request detail views, including
    the reviewers and payers as well as the submitting user. It also enforces a
    the evaluation workflow, which can be seen in the diagram below. In
    addition, the payout amount can only be changed (either directly or through
    modifiers) while the request is in the 'evaluating' state.

    :param int request_id: the ID of the request

    .. digraph:: request_workflow

        rankdir="LR";

        sub [label="submitted", shape=plaintext];

        node [style="dashed, filled"];

        eval [label="evaluating", fillcolor="#fcf8e3"];
        rej [label="rejected", style="solid, filled", fillcolor="#f2dede"];
        app [label="approved", fillcolor="#d9edf7"];
        inc [label="incomplete", fillcolor="#f2dede"];
        paid [label="paid", style="solid, filled", fillcolor="#dff0d8"];

        sub -> eval;
        eval -> rej [label="R"];
        eval -> app [label="R"];
        eval -> inc [label="R"];
        rej -> eval [label="R"];
        inc -> eval [label="R, S"];
        inc -> rej [label="R"];
        app -> paid [label="P"];
        app -> eval [label="R"];
        paid -> eval [label="P"];
        paid -> app [label="P"];

    R means a reviewer can make that change, S means the submitter can make
    that change, and P means payers can make that change. Solid borders are
    terminal states.
    """
    srp_request = Request.query.get(request_id)
    review_perm = ReviewRequestsPermission(srp_request)
    pay_perm = PayoutRequestsPermission(srp_request)
    if request.method == 'POST':
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
                # For serious, look at the diagram in the documentation before
                # tinkering around in here.
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
                elif srp_request.status == 'incomplete':
                    if type_ not in ('evaluating', 'rejected', 'comment'):
                        flash("Can only reject or re-evaluate.", 'error')
                        invalid = True
                    elif type_ == 'evaluating' and not (review_perm.can() or
                            srp_request.submitter == current_user):
                        flash(("You must be a reviewer or own this request to"
                               "re-evaluate."), 'error')
                        invalid = True
                    elif type_ == 'rejected' and not review_perm.can():
                        flash("You are not a reviewer.", 'error')
                        invalid = True
                elif srp_request.status == 'rejected':
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
    # Different templates are used for different roles
    if review_perm.can():
        template = 'request_review.html'
    elif pay_perm.can():
        template = 'request_detail.html'
    elif current_user == srp_request.submitter:
        template = 'request_detail.html'
    else:
        abort(403)
    return render_template(template, srp_request=srp_request,
            modifier_form=ModifierForm(formdata=None),
            payout_form=PayoutForm(formdata=None),
            action_form=ActionForm(formdata=None),
            void_form=VoidModifierForm(formdata=None))
