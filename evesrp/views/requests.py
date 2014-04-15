from collections import OrderedDict

from flask import render_template, abort, url_for, flash, Markup, request,\
    redirect, current_app
from flask.views import View
from flask.ext.login import login_required, current_user
from flask.ext.wtf import Form
from wtforms.fields import SelectField, SubmitField, TextAreaField, HiddenField
from wtforms.fields.html5 import URLField, DecimalField
from wtforms.validators import InputRequired, AnyOf, URL

from .. import db
from ..models import Request, Modifier, Action
from ..auth import SubmitRequestsPermission, ReviewRequestsPermission, \
        PayoutRequestsPermission, admin_permission
from ..auth.models import Division, Pilot


class RequestListing(View):
    """Abstract class for lists of :py:class:`~evesrp.models.Request`\s.
    """

    #: The template to use for listing requests
    template = 'list_requests.html'

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

    def dispatch_request(self, division_id=None):
        """Returns the response to requests.

        Part of the :py:class:`flask.views.View` interface.
        """
        return render_template(self.template,
                requests=self.requests(division_id))


class SubmittedRequestListing(RequestListing):
    """A requests listing with a button for submitting requests at the bottom.

    It will show all requests the current user has submitted. The button links
    to :py:func:`submit_request`.
    """

    template = 'list_submit.html'

    def requests(self, division_id=None):
        if division_id is not None:
            division = Division.query.get_or_404(division_id)
            return filter(lambda r: r.division == division,
                    current_user.requests)
        else:
            return current_user.requests


class PermissionRequestListing(RequestListing):
    """Show all requests that the current user has permissions to access.

    This is used for the various permission-specific views.
    """

    def __init__(self, permissions, filter_func):
        """Create a :py:class:`PermissionRequestListing` for the given
        permissions.

        The requests can be further filtered by providing a callable via
        ``filter_func``.

        :param tuple permissions: The permissions to filter by
        :param callable filter_func: A callable taking a request as an argument
            and returning ``True`` or ``False`` if it should be included.
        """
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


def register_perm_request_listing(app, endpoint, path, permissions,
        filter_func):
    """Utility function for creating :py:class:`PermissionRequestListing`
    views.

    :param app: The application to add the view to
    :type app: :py:class:`flask.Flask`
    :param str endpoint: The name of the view
    :param str path: The URL path for the view
    :param tuple permissions: Passed to
        :py:meth:`PermissionRequestListing.__init__`
    :param callable filter_func: Passed to
        :py:meth:`PermissionRequestListing.__init__`
    """
    view = PermissionRequestListing.as_view(endpoint, permissions=permissions,
            filter_func=filter_func)
    view = login_required(view)
    app.add_url_rule(path, view_func=view)
    app.add_url_rule('{}/<int:division_id>'.format(path), view_func=view)


class RequestForm(Form):
    url = URLField('Killmail URL', validators=[InputRequired(), URL()])
    details = TextAreaField('Details', validators=[InputRequired()])
    division = SelectField('Division', coerce=int)
    submit = SubmitField('Submit')


@login_required
def submit_request():
    """Submit a :py:class:`~.models.Request`\.

    Displayes a form for submitting a request and then processes the submitted
    information. Verifies that the user has the appropriate permissions to
    submit a request for the chosen division and that the killmail URL given is
    valid. Also enforces that the user submitting this requests controls the
    character from the killmail and prevents duplicate requests.
    """
    if not current_user.has_permission('submit'):
        abort(403)
    form = RequestForm()
    choices = []
    for division in current_user.divisions['submit']:
        choices.append((division.id, division.name))
    form.division.choices = choices
    if form.validate_on_submit():
        # validate killmail first
        for source in current_app.killmail_sources:
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
            srp_request = Request(current_user, form.details.data, division,
                    mail)
            srp_request.pilot = pilot
            db.session.add(srp_request)
            db.session.commit()
            return redirect(url_for('request_detail',
                request_id=srp_request.id))
        else:
            flash("This kill has already been submitted", 'warning')
            return redirect(url_for('request_detail',
                request_id=srp_request.id))
    return render_template('form.html', form=form)

submit_request.methods = ['GET', 'POST']


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

request_detail.methods = ['GET', 'POST']
