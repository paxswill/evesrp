from __future__ import absolute_import
from collections import OrderedDict, defaultdict
import re

import babel
from flask import render_template, abort, url_for, flash, Markup, request,\
    redirect, current_app, Blueprint, Markup, json, make_response
from flask.views import View
from flask.ext.babel import gettext, lazy_gettext, get_locale
from flask.ext.login import login_required, current_user
from flask.ext.sqlalchemy import Pagination
from flask.ext.wtf import Form
import iso8601
import six
from six.moves import map
from wtforms.fields import SelectField, SubmitField, TextAreaField, HiddenField
from wtforms.fields.html5 import URLField, DecimalField
from wtforms.validators import InputRequired, AnyOf, URL, ValidationError,\
    StopValidation

from .. import db
from ..models import Request, Modifier, Action, ActionType, ActionError,\
        ModifierError, AbsoluteModifier, RelativeModifier
from ..util import xmlify, jsonify, classproperty, PrettyDecimal, varies,\
        ensure_unicode, parse_datetime
from ..auth import PermissionType
from ..auth.models import Division, Pilot, Permission, User, Group, Note,\
    APIKey, users_groups


if six.PY3:
    unicode = str


blueprint = Blueprint('requests', __name__)


class RequestListing(View):
    """Abstract class for lists of :py:class:`~evesrp.models.Request`\s.

    Subclasses will be able to respond to both normal HTML requests as well as
    to API requests with JSON.
    """

    #: The template to use for listing requests
    template = 'requests_list.html'

    #: Decorators to apply to the view functions
    decorators = [login_required, varies('Accept', 'X-Requested-With')]

    # TRANS: The default title for a page with atable listing SRP requests.
    title = lazy_gettext(u'Requests')

    @staticmethod
    def parse_filter(filter_string):
        filters = {}
        # Fail early for empty filters
        if filter_string is None or filter_string == '':
            return filters
        split_filters = filter_string.split('/')
        # Trim empty beginnings and/or ends
        if split_filters[0] == '':
            split_filters = split_filters[1:]
        if split_filters[-1] == '':
            split_filters = split_filters[:-1]
        # Check for unpaired filters
        if len(split_filters) % 2 != 0:
            # FIXME: uneven length of filters
            return filters
        for i in range(0, len(split_filters), 2):
            attr = split_filters[i].lower()
            values = split_filters[i + 1]
            # Use sets for deduplicating
            filters.setdefault(attr, set())
            # Details are special filter types, and may contain commas. They
            # are allowed to be specified multiple times.
            if attr == 'details':
                filters[attr].add(values)
            elif attr == 'page':
                try:
                    filters['page'] = int(values)
                except TypeError:
                    # TRANS: Warning message shown if something other than a
                    # TRANS: single number was given as a page number (like a
                    # TRANS: letter, word, or multiple numbers).
                    flash(gettext(
                            u"Invalid value for page number: %(num)d.",
                                num=values),
                            u'warning')
                    current_app.logget.warn(
                            "Invalid value of page number: {}".format(values))
            elif attr == 'sort':
                filters['sort'] = values.lower()
            elif attr == 'status':
                actions = set()
                if ',' in values:
                    values = values.split(',')
                else:
                    values = [values]
                for action in values:
                    actions.add(ActionType.from_string(action))
                filters[attr] = actions
            elif ',' in values:
                values = values.split(',')
                filters[attr].update(values)
            else:
                filters[attr].add(values)
        return filters

    @staticmethod
    def unparse_filter(filters):
        attrs = sorted(six.iterkeys(filters))
        filter_strings = []
        for attr in attrs:
            if attr == 'details':
                for details in sorted(filters[attr]):
                    filter_strings.append('details/' + details)
            elif attr == 'page':
                filter_strings.append('page/{}'.format(filters['page']))
            elif attr == 'sort':
                filter_strings.append('sort/{}'.format(filters['sort']))
            elif attr == 'status':
                values = [a.name for a in filters[attr]]
                values = sorted(values)
                filter_strings.append(attr + '/' + ','.join(values))
            else:
                values = sorted(filters[attr])
                filter_strings.append(attr + '/' + ','.join(values))
        return '/'.join(filter_strings)

    def requests(self, filters):
        """Returns a list :py:class:`~.Request`\s belonging to
        the specified :py:class:`~.Division`, or all divisions if
        ``None``.

        :returns: :py:class:`~.models.Request`\s
        :rtype: iterable
        """
        # Start with a basic query for requests
        requests = Request.query.options(*self._load_options)
        requests = requests.order_by(Request.timestamp.desc())
        # Set default filters values
        filters.setdefault('page', 1)
        filters.setdefault('sort', '-submit_timestamp')
        # Apply the filters
        known_attrs = ('page', 'division', 'alliance', 'corporation',
                'pilot', 'system', 'constellation', 'region', 'ship_type',
                'status', 'details', 'payout', 'base_payout', 'kill_timestamp',
                'submit_timestamp')
        for attr, values in six.iteritems(filters):
            # massage pretty attribute names to the not-so-pretty ones
            if attr == 'ship':
                real_attr = 'ship_type'
            elif attr == 'submit_timestamp':
                real_attr = 'timestamp'
            else:
                real_attr = attr
            # massage negative/range filters
            if real_attr not in ('page', 'sort', 'details', 'status',
                                 'timestamp', 'kill_timestamp'):
                new_values = set()
                for value in values:
                    if value.startswith(('-', '<', '>')):
                        new_values.add((value[:1], value[1:]))
                    elif value.startswith(('<=', '>=')):
                        new_values.add((value[:1], value[:2]))
                        new_values.add(('=', value[:2]))
                    else:
                        new_values.add(('=', value))
                grouped = {'=': set(), '<': set(), '>': set(), '-': set()}
                for value in new_values:
                    grouped[value[0]].add(value[1])
            else:
                grouped = {'=': values, '-':[], '<':[], '>':[]}
            # Handle a couple attributes specially
            if real_attr == 'details':
                clauses = [Request.details.match(d) for d in values]
                requests = requests.filter(db.or_(*clauses)) 
            elif real_attr == 'page':
                continue
            elif real_attr == 'sort':
                if values[0] == '-':
                    descending = True
                    sort_attr = values[1:]
                else:
                    descending = False
                    sort_attr = values
                # massage special attribute names
                if sort_attr == 'ship':
                    sort_attr = 'ship_type'
                elif sort_attr == 'submit_timestamp':
                    sort_attr = 'timestamp'
                # Handle special (joined) sorts
                if sort_attr == 'division':
                    if descending:
                        column = db.func.lower(Division.name).desc()
                    else:
                        column = db.func.lower(Division.name).asc()
                    requests = requests.order_by(None)
                    requests = requests.join(Division).order_by(column)
                elif sort_attr == 'pilot':
                    if descending:
                        column = db.func.lower(Pilot.name).desc()
                    else:
                        column = db.func.lower(Pilot.name).asc()
                    requests = requests.order_by(None)
                    requests = requests.join(Pilot).order_by(column)
                else:
                    column = getattr(Request, sort_attr)
                    if descending:
                        column = column.desc()
                    else:
                        column = column.asc()
                    requests = requests.order_by(None)
                    requests = requests.order_by(column)
            elif real_attr in ('timestamp', 'kill_timestamp'):
                column = getattr(Request, real_attr)
                for value in values:
                    try:
                        start, end = parse_datetime(value)
                    except iso8601.ParseError as e:
                        current_app.logger.error(
                                u"Invalid date provided ({}). "
                                u"Exception: {}".format(value, e))
                        # TRANS: Error message shown when a date is written
                        # TRANS: incorrectly.
                        abort(400, gettext(u"Invalid date format. Please read "
                                           u"the documentation for date "
                                           u"filtering."))
                    requests = requests.filter(column.between(start, end))
            elif real_attr in known_attrs:
                column = getattr(Request, real_attr)
                # in_ isn't supported on relationships (yet).
                if hasattr(column, 'mapper'):
                    # This is black magic
                    id_column = column.mapper.attrs.id.class_attribute
                    name_column = column.mapper.attrs.name.class_attribute
                    mapped = db.session.query(id_column)
                    filtered = False
                    if grouped['=']:
                        mapped = mapped.filter(name_column.in_(grouped['=']))
                        filtered = True
                    if grouped['-']:
                        mapped = mapped.filter(~name_column.in_(grouped['-']))
                        filtered = True
                    if grouped['<']:
                        for lt_val in grouped['<']:
                            mapped = mapped.filter(name_column < lt_val)
                        filtered = True
                    if grouped['>']:
                        for gt_val in grouped['>']:
                            mapped = mapped.filter(name_column > gt_val)
                        filtered = True
                    if filtered:
                        mapped = mapped.subquery()
                        requests = requests.join(mapped)
                else:
                    if grouped['=']:
                        requests = requests.filter(column.in_(grouped['=']))
                    if grouped['-']:
                        requests = requests.filter(~column.in_(grouped['-']))
                    for lt_val in grouped['<']:
                        requests = requests.filter(column < lt_val)
                    for gt_val in grouped['>']:
                        requests = requests.filter(column > gt_val)
            else:
                # TRANS: Warning message shown when an unknown atribute is
                # TRANS: specified in the list of filters.
                flash(gettext(
                        u"Unknown filter attribute name: %(attribute)s.",
                        attribute=attr),
                    u'warning')
        return requests

    def dispatch_request(self, filters='', **kwargs):
        """Returns the response to requests.

        Part of the :py:class:`flask.views.View` interface.
        """
        filter_map = self.parse_filter(filters)
        current_app.logger.debug("Filter map: {}".format(filter_map))
        canonical_filter = self.unparse_filter(filter_map)
        if canonical_filter != filters:
            current_app.logger.debug(u"Redirecting to filter '{}' from filter"
                                     u" '{}'.".format(canonical_filter,
                                         filters))
            url_kwargs = {
                'filters': canonical_filter,
            }
            if 'fmt' in request.args:
                url_kwargs['fmt'] = request.args['fmt']
            return redirect(url_for(request.endpoint, **url_kwargs), code=301)
        requests = self.requests(filter_map)
        # Ignore rejected requests when summing the payout.
        # Discard ordering options, they affect the sum somehow.
        payout_requests = requests.\
                filter(Request.status != ActionType.rejected).\
                order_by(False).\
                with_entities(Request.id, Request.payout).\
                subquery(with_labels=True)
        total_payouts = db.session.query(db.func.sum(
                        payout_requests.c.request_payout))\
                .select_from(payout_requests)\
                .scalar()
        if total_payouts is None:
            total_payouts = PrettyDecimal(0)
        # API requests (including RSS) should have a limit of 200 requests,
        # otherwise go with the standard 15. THe standard 15 includes
        # XmlHttpRequest-based requests as those are going to be used to
        # rebuild the contents of an HTML view.
        if (request.is_json or request.is_xml or request.is_rss) and \
                not request.is_xhr:
            per_page = 200
        else:
            per_page = 15
        pager = requests.paginate(filter_map['page'], per_page=per_page,
                error_out=False)
        if len(pager.items) == 0 and pager.page > 1:
            filter_map['page'] = pager.pages
            return redirect(url_for(request.endpoint,
                    filters=self.unparse_filter(filter_map)))
        # Prep previous and next page links for API responses
        api_links = {}
        link_kwargs = {
            '_external': True,
        }
        if 'fmt' in request.args:
            link_kwargs['fmt'] = request.args['fmt']
        if pager.has_prev:
            filter_map['page'] -= 1
            api_links['prev'] = url_for(request.endpoint,
                    filters=self.unparse_filter(filter_map), **link_kwargs)
            filter_map['page'] = pager.page
        if pager.has_next:
            filter_map['page'] += 1
            api_links['next'] = url_for(request.endpoint,
                    filters=self.unparse_filter(filter_map), **link_kwargs)
            filter_map['page'] = pager.page
        # Handle API/RSS responses
        if request.is_json or request.is_xhr:
            jsonify_kwargs = {
                'requests': pager.items,
                'request_count': requests.count(),
                'total_payouts': total_payouts.currency()
            }
            # For JSON responses, add prev and next links (when appropriate) to
            # aid API consumers in walking a list of requests.
            if request.is_json:
                jsonify_kwargs.update(api_links)
            return jsonify(**jsonify_kwargs)
        if request.is_rss:
            return xmlify('rss.xml', content_type='application/rss+xml',
                    requests=pager.items,
                    title=(kwargs['title'] if 'title' in kwargs else u''),
                    main_link=url_for(request.endpoint, filters=filters,
                        _external=True))
        if request.is_xml:
            xmlify_kwargs = {
                'requests': pager.items,
                'total_payouts': total_payouts,
            }
            # As for JSON API responses, add prev and next links
            xmlify_kwargs.update(api_links)
            return xmlify('requests_list.xml', **xmlify_kwargs)
        if 'title' in kwargs:
            title = kwargs.pop('title')
        else:
            title = self.title
        return render_template(self.template, pager=pager, filters=filter_map,
                total_payouts=total_payouts, title=title, **kwargs)

    @classproperty
    def _load_options(cls):
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


def url_for_page(pager, page_num):
    """Utility method used in Jinja templates."""
    filters = request.view_args.get('filters', '')
    filters = RequestListing.parse_filter(filters)
    filters['page'] = page_num
    return url_for(request.endpoint,
            filters=RequestListing.unparse_filter(filters))


class PersonalRequests(RequestListing):
    """Shows a list of all personally submitted requests and divisions the user
    has permissions in.

    It will show all requests the current user has submitted.
    """

    template = 'requests_personal.html'

    def requests(self, filters):
        requests = super(PersonalRequests, self).requests(filters)
        requests = requests\
                .join(User)\
                .filter(User.id==current_user.id)
        return requests

    @property
    def title(self):
        current_locale = get_locale()
        if current_locale is None:
            current_locale = babel.Locale('en')
        # Special case possesive form in English
        if current_locale.language.lower() == 'en' and \
                current_user.name[:-1] == u's':
            return u"{}' Requests".format(current_user.name)
        else:
            # TRANS: The title of the page listing all requests an individual
            # TRANS: user has made.
            return gettext(u"%(name)s's Requests", name=current_user.name)


class PermissionRequestListing(RequestListing):
    """Show all requests that the current user has permissions to access.

    This is used for the various permission-specific views.
    """

    def __init__(self, permissions, statuses, title=None):
        """Create a :py:class:`PermissionRequestListing` for the given
        permissions and statuses.

        :param tuple permissions: The permissions to filter by
        :param tuple statuses: A tuple of valid statuses for requests to be in
        """
        if permissions in PermissionType.all:
            permissions = (permissions,)
        # Admin permission has to be explicitly added because it's used in a
        # complicated query in requests()
        self.permissions = (PermissionType.admin,) + tuple(permissions)
        self.statuses = statuses
        if title is None:
            self.title = u', '.join(map(lambda s: s.description, self.statuses))
        else:
            self.title = ensure_unicode(title)

    def dispatch_request(self, filters='', **kwargs):
        if not current_user.has_permission(self.permissions):
            abort(403)
        else:
            return super(PermissionRequestListing, self).dispatch_request(
                    filters,
                    title=gettext(self.title),
                    **kwargs)

    def requests(self, filters):
        current_groups = db.select([users_groups.c.group_id])\
                .where(users_groups.c.user_id == current_user.id).alias()
        divisions = db.select([Permission.division_id.label('division_id')])\
                .where(Permission.permission.in_(self.permissions))\
                .where(db.or_(
                        Permission.entity_id == current_user.id,
                        Permission.entity_id.in_(current_groups)))\
                .alias('permitted_divisions')
        # modify filters
        if 'status' not in filters:
            filters['status'] = self.statuses
        requests = super(PermissionRequestListing, self).requests(filters)\
                .join(divisions, Request.division_id==divisions.c.division_id)
        return requests.distinct()


class PayoutListing(PermissionRequestListing):
    """A special view made for quickly processing payouts for requests."""

    template = 'payout.html'

    def __init__(self):
        # Just a special case of PermissionRequestListing
        super(PayoutListing, self).__init__((PermissionType.pay,),
                (ActionType.approved,), u'Pay Outs')

    def requests(self, filters):
        if 'sort' not in filters:
            filters['sort'] = 'submit_timestamp'
        return super(PayoutListing, self).requests(filters)

    def dispatch_request(self, filters='', **kwargs):
        if hasattr(request, 'json_extended'):
            if isinstance(request.json_extended, bool):
                old_value = request.json_extended
                request.json_extended = defaultdict(lambda: old_value)
        else:
            request.json_extended = {}
        request.json_extended[Request] = True
        if not current_user.has_permission(self.permissions):
            abort(403)
        return super(PayoutListing, self).dispatch_request(
                filters,
                form=ActionForm())


def register_perm_request_listing(app, endpoint, path, permissions, statuses,
        title=None):
    """Utility function for creating :py:class:`PermissionRequestListing`
    views.

    :param app: The application to add the view to
    :type app: :py:class:`flask.Flask`
    :param str endpoint: The name of the view
    :param str path: The URL path for the view
    :param tuple permissions: Passed to
        :py:meth:`PermissionRequestListing.__init__`
    :param iterable statuses: Passed to
        :py:meth:`PermissionRequestListing.__init__`
    """
    if not path.endswith('/'):
        path += '/'
    view = PermissionRequestListing.as_view(endpoint, permissions=permissions,
            statuses=statuses, title=title)
    app.add_url_rule(path, view_func=view)
    app.add_url_rule('{}rss.xml'.format(path), view_func=view)
    app.add_url_rule(path + '<path:filters>', view_func=view)


@blueprint.record
def register_class_views(state):
    """Called when the blueprint is registered, this function defines routes
    for and attaches the class-based views to the app.
    """
    try:
        prefixes = state.app.request_prefixes
    except AttributeError:
        prefixes = []
        state.app.request_prefixes = prefixes
    prefixes.append(state.url_prefix if state.url_prefix is not None else '')
    # Personal list
    personal_view = PersonalRequests.as_view('personal_requests')
    state.add_url_rule('/personal/', view_func=personal_view)
    state.add_url_rule('/personal/rss.xml', view_func=personal_view)
    state.add_url_rule('/personal/<path:filters>', view_func=personal_view)
    # Payout list
    payout_view = PayoutListing.as_view('list_approved_requests')
    payout_url_stub = '/pay/'
    state.add_url_rule(payout_url_stub, view_func=payout_view)
    state.add_url_rule(payout_url_stub + 'rss.xml', view_func=payout_view)
    state.add_url_rule(payout_url_stub + '<path:filters>',
            view_func=payout_view)
    # Other more generalized listings
    register_perm_request_listing(state, 'list_pending_requests',
            '/pending/', (PermissionType.review, PermissionType.audit),
            ActionType.pending, u'Pending Requests')
    register_perm_request_listing(state, 'list_completed_requests',
            '/completed/', PermissionType.elevated, ActionType.finalized,
            u'Completed Requests')
    # Special all listing, mainly intended for API users
    register_perm_request_listing(state, 'list_all_requests',
            '/all/', PermissionType.elevated, ActionType.statuses,
            u'All Requests')


class ValidKillmail(URL):
    """Custom :py:class:'~.Field' validator that checks if any
    :py:class:`~.Killmail` accepts the given URL.
    """
    def __init__(self, mail_class, **kwargs):
        self.mail_class = mail_class
        super(ValidKillmail, self).__init__(**kwargs)

    def __call__(self, form, field):
        super(ValidKillmail, self).__call__(form, field)
        try:
            mail = self.mail_class(field.data)
        except ValueError as e:
            if six.PY2:
                raise ValidationError(unicode(e))
            else:
                # Py3 chains the exceptions
                raise ValidationError
        except LookupError as e:
            if six.PY2:
                raise ValidationError(unicode(e))
            else:
                # Py3 chains the exceptions
                raise ValidationError
        else:
            if mail.verified:
                form.killmail = mail
                raise StopValidation
            else:
                raise ValidationError(
                # TRANS: Error message show when trying to submit a killmail
                # TRANS: that cannot be verified.
                        gettext(u"%(url)s cannot be verified.", url=field.data))


def get_killmail_validators():
    """Get a list of :py:class:`ValidKillmail`\s for each killmail source.

    This method is used to delay accessing `current_app` until we're in a
    request context.
    :returns: a list of :py:class:`ValidKillmail`\s
    :rtype list:
    """
    validators = [ValidKillmail(s) for s in current_app.killmail_sources]
    validators.append(InputRequired())
    return validators


def get_killmail_descriptions():
    km_list = u"".join(
            [Markup(u"<li>{}</li>").format(km.description) for km in \
                    current_app.killmail_sources])
    # TRANS: Header for a list of the kinds of links that are acceptable to
    # TRANS: submit as killmails for SRP.
    description = gettext(u"Acceptable Killmail Links:<ul>%(sources)s</ul>",
            sources=km_list)
    description = Markup(description)
    return description


class RequestForm(Form):
    # TRANS: Label for an input field for the killmail URL
    url = URLField(lazy_gettext(u'Killmail URL'))

    # TRANS: Label for a text entry field for inputting supporting details
    # TRANS: about a loss.
    details = TextAreaField(lazy_gettext(u'Details'),
        validators=[InputRequired()])

    # TRANS: Label for an dropdown menu to select which division to submit for
    # TRANS: SRP to.
    division = SelectField(lazy_gettext(u'Division'), coerce=int)

    # TRANS: Label for the button that submits the form.
    submit = SubmitField(lazy_gettext(u'Submit'))

    def validate_url(form, field):
        failures = set()
        for v in get_killmail_validators():
            try:
                v(form, field)
            except ValidationError as e:
                failures.add(unicode(e))
            else:
                continue
        else:
            # If execution reached here, it means a StopValidation exception
            # wasn't raised (meaning the killmail isn't valid).
            raise ValidationError([e for e in failures])

    def validate_division(form, field):
        division = Division.query.get(field.data)
        if division is None:
            # TRANS: Error message shown when trying to submit a request to a
            # TRANS: non-existant division.
            raise ValidationError(gettext(u"No division with ID '%(div_id)s'.",
                    div_id=field.data))
        if not current_user.has_permission(PermissionType.submit, division):
            # TRANS: Error message shown when trying to a submit a request to a
            # TRANS: division you do not have the submission permission in.
            raise ValidationError(gettext(u"You do not have permission to "
                                          u"submit to division '%(name)s'.",
                    name=division.name))


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
    if not current_user.has_permission(PermissionType.submit):
        abort(403)
    form = RequestForm()
    # Do it in here so we can access current_app (needs to be in an app
    # context)
    form.url.description = get_killmail_descriptions()
    form.details.description = current_app.config['SRP_DETAILS_DESCRIPTION']
    # Create a list of divisions this user can submit to
    form.division.choices = current_user.submit_divisions()
    if len(form.division.choices) == 1:
        form.division.data = form.division.choices[0][0]

    if form.validate_on_submit():
        mail = form.killmail
        # Prevent submitting other people's killmails
        pilot = Pilot.query.get(mail.pilot_id)
        if not pilot or pilot not in current_user.pilots:
            # TRANS: Error message shown when trying to submit a lossmail from
            # TRANS: A character not associated with your user account.
            flash(gettext(u"You can only submit killmails of characters you "
                          u"control"),
                    u'warning')
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
            return redirect(url_for('.get_request_details',
                request_id=srp_request.id))
        else:
            # TRANS: Error message shown when trying to submit a killmail for
            # TRANS: SRP a second time.
            flash(gettext(u"This kill has already been submitted"), u'warning')
            return redirect(url_for('.get_request_details',
                request_id=srp_request.id))
    return render_template('form.html', form=form,
    # TRANS: Title for the page showing the form for submitting SRP requests.
            title=gettext(u'Submit Request'))


class ModifierForm(Form):

    id_ = HiddenField(default='modifier')

    # TRANS: Label for an input field for the amount a modifier is for. Can be
    # TRANS: either a percentage or an ISK value (in millions of ISK).
    value = DecimalField(lazy_gettext(u'Value'))

    type_ = HiddenField(validators=[AnyOf(('rel-bonus', 'rel-deduct',
            'abs-bonus', 'abs-deduct'))])

    # TRANS: Label for a text field for inputting the reason a modifier is
    # TRANS: being applied.
    note = TextAreaField(lazy_gettext(u'Reason'))


class VoidModifierForm(Form):

    id_ = HiddenField(default='void')

    modifier_id = HiddenField()

    void = SubmitField(Markup(u'x'))

    def __init__(self, modifier=None, *args, **kwargs):
        if modifier is not None:
            self.modifier_id = modifier.id
        super(VoidModifierForm, self).__init__(*args, **kwargs)


class PayoutForm(Form):

    id_ = HiddenField(default='payout')

    value = DecimalField(u'M ISK', validators=[InputRequired()])


class ActionForm(Form):

    id_ = HiddenField(default='action')

    # TRANS: Label for a text field for adding a note to an action on a
    # TRANS: request, or for making a comment on a request.
    note = TextAreaField(u'Note')

    type_ = HiddenField(default='comment',
            validators=[AnyOf(list(ActionType.values()))])


class ChangeDetailsForm(Form):

    id_ = HiddenField(default='details')

    details = TextAreaField(lazy_gettext(u'Details'),
            validators=[InputRequired()])


class AddNote(Form):

    id_ = HiddenField(default='note')

    # TRANS: Label for text input field for a note to be added about a user.
    note = TextAreaField(lazy_gettext(u'Add Note'),
            # TRANS: Help text explaining a hidden feature about the notes made
            # TRANS: about users.
            description=lazy_gettext(
                u"If you have something like '#{Kill ID}', it will be "
                u"linkified to the corresponding request (if it exists). For "
                u"example, #1234567 would be linked to the request for the "
                u"kill with ID 1234567."),
            validators=[InputRequired()])


killmail_re = re.compile(r'#(\d+)')


@blueprint.route('/<int:request_id>/', methods=['GET'])
@login_required
@varies('Accept')
def get_request_details(request_id=None, srp_request=None):
    """Handles responding to all of the :py:class:`~.models.Request` detail
    functions.

    The various modifier functions all depend on this function to create the
    actual response content.
    Only one of the arguments is required. The ``srp_request`` argument is a
    conveniece to other functions calling this function that have already
    retrieved the request.

    :param int request_id: the ID of the request.
    :param srp_request: the request.
    :type srp_request: :py:class:`~.models.Request`
    """
    if srp_request is None:
        srp_request = Request.query.get_or_404(request_id)
    # Different templates are used for different roles
    if current_user.has_permission(PermissionType.review,
            srp_request.division):
        template = 'request_review.html'
    elif current_user.has_permission(PermissionType.pay, srp_request.division):
        template = 'request_pay.html'
    elif current_user == srp_request.submitter or current_user.has_permission(
            PermissionType.audit):
        template = 'request_detail.html'
    else:
        abort(403)
    if request.is_json or request.is_xhr:
        return jsonify(srp_request._json(True))
    if request.is_xml:
        return xmlify('request.xml', srp_request=srp_request)
    return render_template(template, srp_request=srp_request,
            modifier_form=ModifierForm(formdata=None),
            payout_form=PayoutForm(formdata=None),
            action_form=ActionForm(formdata=None),
            void_form=VoidModifierForm(formdata=None),
            details_form=ChangeDetailsForm(formdata=None, obj=srp_request),
            note_form=AddNote(formdata=None),
            # TRANS: Title for the page showing the details about a single
            # TRANS: SRP request.
            title=gettext(u"Request #%(request_id)s",
                    request_id=srp_request.id))


def _add_modifier(srp_request):
    form = ModifierForm()
    if form.validate():
        if 'bonus' in form.type_.data:
            value = form.value.data
        elif 'deduct' in form.type_.data:
            value = form.value.data * -1
        if 'abs' in form.type_.data:
            ModClass = AbsoluteModifier
            value *= 1000000
        elif 'rel' in form.type_.data:
            ModClass = RelativeModifier
            value /= 100
        try:
            mod = ModClass(srp_request, current_user, form.note.data, value)
            db.session.add(mod)
            db.session.commit()
        except ModifierError as e:
            flash(unicode(e), u'error')
    return get_request_details(srp_request=srp_request)


def _change_payout(srp_request):
    form = PayoutForm()
    if not current_user.has_permission(PermissionType.review, srp_request):
        # TRANS: Error message when someone who does not have the reviewer
        # TRANS: permission tries to change the base payout of a request.
        flash(gettext(u"Only reviewers can change the base payout."), u'error')
    elif form.validate():
        try:
            srp_request.base_payout = form.value.data * 1000000
            db.session.commit()
        except ModifierError as e:
            flash(unicode(e), u'error')
    return get_request_details(srp_request=srp_request)


def _add_action(srp_request):
    form = ActionForm()
    if form.validate():
        type_ = ActionType.from_string(form.type_.data)
        try:
            Action(srp_request, current_user, form.note.data, type_)
            db.session.commit()
        except ActionError as e:
            flash(unicode(e), u'error')
    return get_request_details(srp_request=srp_request)


def _void_modifier(srp_request):
    form = VoidModifierForm()
    if form.validate():
        modifier_id = int(form.modifier_id.data)
        modifier = Modifier.query.get(modifier_id)
        if modifier is None:
            # TRANS: Error message when a user tries to void (cancel) a
            # TRANS: modifier that does not exist.
            flash(gettext(u"Invalid modifier ID %(modifier_id)d.",
                    modifier_id=modifier_id),
                u'error')
        else:
            try:
                modifier.void(current_user)
                db.session.commit()
            except ModifierError as e:
                flash(unicode(e), u'error')
    return get_request_details(srp_request=srp_request)


def _change_details(srp_request):
    form = ChangeDetailsForm()
    if current_user != srp_request.submitter:
        # TRANS: Error message shown when someone other than the request
        # TRANS: submitter tries to change the details of the request.
        flash(gettext(u"Only the submitter can change the request details."),
                u'error')
    elif srp_request.finalized:
        # TRANS: Error message shown when the submitter ties to change the
        # TRANS: details when the request is no long pending (not finished).
        flash(gettext(u"Details can only be changed when the request is still "
                      u"pending.")
                , u'error')
    elif form.validate():
        # TRANS: The old request details have are saved in a comment on the
        # TRANS: request. This is the text that is put at the beginning of the
        # TRANS: comment
        archive_note = gettext(u"Old Details: %(details)s",
                details=srp_request.details)
        if srp_request.status == ActionType.evaluating:
            action_type = ActionType.comment
        else:
            action_type = ActionType.evaluating
        archive_action = Action(srp_request, current_user, archive_note,
                action_type)
        srp_request.details = form.details.data
        db.session.commit()
    return get_request_details(srp_request=srp_request)


def _add_note(srp_request):
    form = AddNote()
    if not current_user.has_permission(PermissionType.elevated):
        # TRANS: Error message shown when someone without the proper
        # TRANS: permissions tries to add a note to a user.
        flash(gettext(u"You do not have permission to add a note to a user."),
                u'error')
    elif form.validate():
        # Linkify killmail IDs
        note_content = Markup.escape(form.note.data)
        for match in killmail_re.findall(note_content):
            kill_id = int(match)
            check_request = db.session.query(Request.id).filter_by(id=kill_id)
            if db.session.query(check_request.exists()):
                link = u'<a href="{url}">#{kill_id}</a>'.format(
                        url=url_for('.get_request_details',
                                request_id=kill_id),
                        kill_id=kill_id)
                link = Markup(link)
                note_content = note_content.replace(u'#' + match, link)
        # Create the note
        note = Note(srp_request.submitter, current_user, note_content)
        db.session.commit()
    return get_request_details(srp_request=srp_request)


@blueprint.route('/<int:request_id>/', methods=['POST'])
@login_required
def modify_request(request_id):
    """Handles POST requests that modify :py:class:`~.models.Request`\s.

    Because of the numerous possible forms, this function bounces execution to
    a more specific function based on the form's "id\_" field.

    :param int request_id: the ID of the request.
    """
    srp_request = Request.query.get_or_404(request_id)
    if request.form['id_'] == 'modifier':
        return _add_modifier(srp_request)
    elif request.form['id_'] == 'payout':
        return _change_payout(srp_request)
    elif request.form['id_'] == 'action':
        return _add_action(srp_request)
    elif request.form['id_'] == 'void':
        return _void_modifier(srp_request)
    elif request.form['id_'] == 'details':
        return _change_details(srp_request)
    elif request.form['id_'] == 'note':
        return _add_note(srp_request)
    else:
        return abort(400)


class DivisionChange(Form):

    division = SelectField(lazy_gettext(u'Division'), coerce=int)

    submit = SubmitField(lazy_gettext(u'Submit'))


@blueprint.route('/<int:request_id>/division/', methods=['GET', 'POST'])
@login_required
def request_change_division(request_id):
    srp_request = Request.query.get_or_404(request_id)
    if not current_user.has_permission(PermissionType.review, srp_request) and\
            current_user != srp_request.submitter:
        current_app.logger.warn(u"User '{}' does not have permission to change"
                                u" request #{}'s division".format(
                                    current_user, srp_request.id))
        abort(403)
    if srp_request.finalized:
        msg = (u"Cannot change request #{}'s division as it is in a finalized"
               u" state").format(srp_request.id)
        current_app.logger.info(msg)
        # TRANS: Error message shown when a user tries to move a request but is
        # TRANS: unable to becuase the request has been paid or rejected.
        flash(gettext(u"Cannot change the division as this request is in a "
                      u"finalized state"),
                u'error')
        return redirect(url_for('.get_request_details', request_id=request_id))
    division_choices = srp_request.submitter.submit_divisions()
    try:
        division_choices.remove(
                (srp_request.division.id, srp_request.division.name))
    except ValueError:
        pass
    if len(division_choices) == 0:
        current_app.logger.debug(u"No other divisions to move request #{} to."\
                .format(srp_request.id))
        # TRANS: Message shown when a user tries to change a request's division
        # TRANS: but they do not have access to any other divisions.
        flash(gettext(u"No other divisions to move to."), u'info')
        return redirect(url_for('.get_request_details', request_id=request_id))
    form = DivisionChange()
    form.division.choices = division_choices
    # Default to the first value if there's only once choice.
    if len(division_choices) == 1:
        form.division.data = form.division.choices[0][0]
    if form.validate_on_submit():
        new_division = Division.query.get(form.division.data)
        # TRANS: When a request is moved from one division to another, a
        # TRANS: comment is added noting the old division's name and the new
        # TRANS: division's name. This is the text of that note.
        archive_note = gettext(u"Moving from division '%(old_division)s' to "
                               u"division '%(new_division)s'.",
                old_division=srp_request.division.name,
                new_division=new_division.name)
        if srp_request.status == ActionType.evaluating:
            type_ = ActionType.comment
        else:
            type_ = ActionType.evaluating
        archive_action = Action(srp_request, current_user, archive_note, type_)
        srp_request.division = new_division
        db.session.commit()
        # TRANS: Confirmation message shown when wa request has been
        # TRANS: successfully moved to a new division.
        flash(gettext(u"Request #%(request_id)d moved to %(division)s "
                      u"division",
                    request_id=srp_request.id, division=new_division.name),
                u'success')
        if current_user.has_permission(PermissionType.elevated, new_division) \
                or current_user == srp_request.submitter:
            return redirect(url_for('.get_request_details',
                    request_id=request_id))
        else:
            return redirect(url_for('.list_pending_requests'))
    else:
        current_app.logger.warn(u"Form validation failed for division change:"
                                u" {}.".format(form.errors))
    form.division.data = srp_request.division.id
    return render_template('form.html', form=form,
            # TRANS: Title for the page showing the form for changing a
            # TRANS: request's division.
            title=lazy_gettext(u"Change #%(request_id)d's Division",
                request_id=srp_request.id))
