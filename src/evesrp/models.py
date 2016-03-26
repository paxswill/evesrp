from __future__ import absolute_import
import datetime as dt
from decimal import Decimal
import six
from six.moves import filter, map, range
from sqlalchemy import event
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.event import listens_for
from sqlalchemy.schema import DDL, DropIndex
from flask import Markup, current_app, url_for
from flask.ext.babel import gettext, lazy_gettext
from flask.ext.login import current_user

from . import db
from .util import DeclEnum, classproperty, AutoID, Timestamped, AutoName,\
        unistr, ensure_unicode, PrettyDecimal, PrettyNumeric, DateTime
from .auth import PermissionType


if six.PY3:
    unicode = str

class ActionType(DeclEnum):

    # The actual stored values are single character to make it easier on
    # engines that don't support native enum types.

    # TRANS: Name of the status a request is in when it has been submitted and
    # TRANS: is ready to be evaluated.
    evaluating = u'evaluating', lazy_gettext(u'Evaluating')
    """Status for a request being evaluated."""

    # TRANS: Name of the status where a request has had a payout amount set,
    # TRANS: and is ready to be paid out. In other words, approved for payout.
    approved = u'approved', lazy_gettext(u'Approved')
    """Status for a request that has been evaluated and is awaitng payment."""

    # TRANS: Name of the status a request is in if the ISK has been sent to the
    # TRANS: requesting person, and no further action is needed.
    paid = u'paid', lazy_gettext(u'Paid')
    """Status for a request that has been paid. This is a terminatint state."""

    # TRANS: Name of the status a request has where a reviewer has rejected the
    # TRANS: request for SRP.
    rejected = u'rejected', lazy_gettext(u'Rejected')
    """Status for a requests that has been rejected. This is a terminating
    state.
    """

    # TRANS: When a request needs more information to be approved or rejected,
    # TRANS: it is in this status.
    incomplete = u'incomplete', lazy_gettext(u'Incomplete')
    """Status for a request that is missing details and needs further
    action.
    """

    # TRANS: A comment made on a request.
    comment = u'comment', lazy_gettext(u'Comment')
    """A special type of :py:class:`Action` representing a comment made on the
    request.
    """

    @classproperty
    def finalized(cls):
        return frozenset((cls.paid, cls.rejected))

    @classproperty
    def pending(cls):
        return frozenset((cls.evaluating, cls.approved, cls.incomplete))

    @classproperty
    def statuses(cls):
        return frozenset((cls.evaluating, cls.approved, cls.paid, cls.rejected,
                cls.incomplete))


class ActionError(ValueError):
    """Error raised for invalid state changes for a :py:class:`Request`."""
    pass


class Action(db.Model, AutoID, Timestamped, AutoName):
    """Actions change the state of a Request.
    
    :py:class:`Request`\s enforce permissions when actions are added to them.
    If the user adding the action does not have the appropriate
    :py:class:`~.Permission`\s in the request's :py:class:`Division`, an
    :py:exc:`ActionError` will be raised.

    With the exception of the :py:attr:`comment <ActionType.comment>` action
    (which just adds text to a request), actions change the
    :py:attr:`~Request.status` of a Request.
    """

    #: The action be taken. See :py:class:`ActionType` for possible values.
    # See set_request_type below for the effect setting this attribute has on
    # the parent Request.
    type_ = db.Column(ActionType.db_type(), nullable=False)

    #: The ID of the :py:class:`Request` this action applies to.
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'))

    #: The :py:class:`Request` this action applies to.
    request = db.relationship('Request', back_populates='actions',
            cascade='save-update,merge,refresh-expire,expunge')

    #: The ID of the :py:class:`~.User` who made this action.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    #: The :py:class:`~.User` who made this action.
    user = db.relationship('User', back_populates='actions',
            cascade='save-update,merge,refresh-expire,expunge')

    #: Any additional notes for this action.
    note = db.Column(db.Text(convert_unicode=True))

    def __init__(self, request, user, note=None, type_=None):
        if type_ is not None:
            self.type_ = type_
        self.user = user
        self.note = ensure_unicode(note)
        # timestamp has to be an actual value (besides None) before the request
        # is set so thhe request's validation doesn't fail.
        self.timestamp = dt.datetime.utcnow()
        self.request = request

    def __repr__(self):
        return "{x.__class__.__name__}({x.request}, {x.user}, {x.type_})".\
                format(x=self)

    def _json(self, extended=False):
        try:
            parent = super(Action, self)._json(extended)
        except AttributeError:
            parent = {}
        parent[u'type'] = self.type_
        if extended:
            parent[u'note'] = self.note or u''
            parent[u'timestamp'] = self.timestamp
            parent[u'user'] = self.user
        return parent


class ModifierError(ValueError):
    """Error raised when a modification is attempted to a :py:class:`Request`
    when it's in an invalid state.
    """
    pass


class Modifier(db.Model, AutoID, Timestamped, AutoName):
    """Modifiers apply bonuses or penalties to Requests.

    This is an abstract base class for the pair of concrete implementations.
    Modifiers can be voided at a later date. The user who voided a modifier and
    when it was voided are recorded.

    :py:class:`Request`\s enforce permissions when modifiers are added. If the
    user adding a modifier does not have the appropriate
    :py:class:`~.Permission`\s in the request's :py:class:`~.Division`, a
    :py:exc:`ModifierError` will be raised.
    """

    #: Discriminator column for SQLAlchemy
    _type = db.Column(db.String(20, convert_unicode=True), nullable=False)

    #: The ID of the :py:class:`Request` this modifier applies to.
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'))

    #: The :py:class:`Request` this modifier applies to.
    request = db.relationship('Request', back_populates='modifiers',
            cascade='save-update,merge,refresh-expire,expunge')

    #: The ID of the :py:class`~.User` who added this modifier.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    #: The :py:class:`~.User` who added this modifier.
    user = db.relationship('User', foreign_keys=[user_id],
            cascade='save-update,merge,refresh-expire,expunge')

    #: Any notes explaining this modification.
    note = db.Column(db.Text(convert_unicode=True))

    #: The ID of the :py:class:`~.User` who voided this modifier (if voided).
    voided_user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
            nullable=True)

    #: The :py:class:`~.User` who voided this modifier if it has been voided.
    voided_user = db.relationship('User', foreign_keys=[voided_user_id],
            cascade='save-update,merge,refresh-expire,expunge')

    #: If this modifier has been voided, this will be the timestamp of when it
    #: was voided.
    voided_timestamp = db.Column(DateTime)

    @hybrid_property
    def voided(self):
        return self.voided_user is not None and \
                self.voided_timestamp is not None

    @classmethod
    def _voided_select(cls):
        """Create a subquery with two columns, ``modifier_id`` and ``voided``.

        Used for the expressions of :py:attr:`voided` and
        :py:attr:`Request.payout`.
        """
        user = db.select([cls.id.label('modifier_id'),
                cls.voided_user_id.label('user_id')]).alias('user_sub')
        timestamp = db.select([cls.id.label('modifier_id'),
                cls.voided_timestamp.label('timestamp')]).alias('timestamp_sub')
        columns = [
            db.and_(
                user.c.user_id != None,
                timestamp.c.timestamp != None).label('voided'),
            user.c.modifier_id.label('modifier_id'),
        ]
        return db.select(columns).where(
                user.c.modifier_id == timestamp.c.modifier_id)\
                .alias('voided_sub')

    @voided.expression
    def voided(cls):
        return cls._voided_select().c.voided

    @declared_attr
    def __mapper_args__(cls):
        """SQLAlchemy late-binding attribute to set mapper arguments.

        Obviates subclasses from having to specify polymorphic identities.
        """
        cls_name = unicode(cls.__name__)
        args = {'polymorphic_identity': cls_name}
        if cls_name == u'Modifier':
            args['polymorphic_on'] = cls._type
        return args

    def __init__(self, request, user, note, value):
        self.user = user
        self.note = ensure_unicode(note)
        self.value = value
        self.request = request

    def __repr__(self):
        return ("{x.__class__.__name__}({x.request}, {x.user},"
                "{x}, {x.voided})".format(x=self, value=self))

    def void(self, user):
        """Mark this modifier as void.

        :param user: The user voiding this modifier
        :type user: :py:class:`~.User`
        """
        if self.request.status != ActionType.evaluating:
            # TRANS: Error message shown when trying to void (cancel) a
            # modifier but the request is not in the evaluating state, so the
            # attempt fails.
            raise ModifierError(gettext(u"Modifiers can only be voided when "
                                        u"the request is in the evaluating "
                                        u"state."))
        if not user.has_permission(PermissionType.review,
                self.request.division):
            # TRANS: Error message shown when you attempt to void a modifier
            # but are prevented from doing so because you do not hold the
            # reviewer permission.
            raise ModifierError("You must be a reviewer to be able to void "
                                "modifiers.")
        self.voided_user = user
        self.voided_timestamp = dt.datetime.utcnow()

    @db.validates('request')
    def _check_request_status(self, attr, request):
        if current_app.config['SRP_SKIP_VALIDATION']:
            return request
        if request.status != ActionType.evaluating:
            raise ModifierError(gettext(u"Modifiers can only be added when the"
                                        u" request is in an evaluating "
                                        u"state."))
        if not self.user.has_permission(PermissionType.review,
                request.division):
            raise ModifierError(gettext(u"Only reviewers can add modifiers."))
        return request

    def _json(self, extended=False):
        try:
            parent = super(Modifier, self)._json(extended)
        except AttributeError:
            parent = {}
        parent[u'value'] = self.value
        if extended:
            parent[u'note'] = self.note or u''
            parent[u'timestamp'] = self.timestamp
            parent[u'user'] = self.user
            if self.voided:
                parent[u'void'] = {
                    u'user': self.voided_user,
                    u'timestamp': self.voided_timestamp,
                }
            else:
                parent[u'void'] = False
        else:
            parent[u'void'] = self.voided
        return parent


@unistr
class AbsoluteModifier(Modifier):
    """Subclass of :py:class:`Modifier` for representing absolute
    modifications.

    Absolute modifications are those that are not dependent on the value of
    :py:attr:`Request.base_payout`.
    """

    id = db.Column(db.Integer, db.ForeignKey('modifier.id'), primary_key=True)

    #: How much ISK to add or remove from the payout
    value = db.Column(PrettyNumeric(precision=15, scale=2), nullable=False,
            default=Decimal(0))

    def _json(self, extended=False):
        try:
            parent = super(AbsoluteModifier, self)._json(extended)
        except AttributeError:
            parent = {}
        parent[u'type'] = 'absolute'
        return parent


@unistr
class RelativeModifier(Modifier):
    """Subclass of :py:class:`Modifier` for representing relative modifiers.

    Relative modifiers depend on the value of :py:attr:`Modifier.base_payout`
    to calculate their effect.
    """

    id = db.Column(db.Integer, db.ForeignKey('modifier.id'), primary_key=True)

    #: What percentage of the payout to add or remove
    value = db.Column(db.Numeric(precision=8, scale=5), nullable=False,
            default=Decimal(0))

    def _json(self, extended=False):
        try:
            parent = super(RelativeModifier, self)._json(extended)
        except AttributeError:
            parent = {}
        parent[u'type'] = 'relative'
        return parent


class Request(db.Model, AutoID, Timestamped, AutoName):
    """Requests represent SRP requests."""

    #: The ID of the :py:class:`~.User` who submitted this request.
    submitter_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    #: The :py:class:`~.User` who submitted this request.
    submitter = db.relationship('User', back_populates='requests',
            cascade='save-update,merge,refresh-expire,expunge')

    #: The ID of the :py:class`~.Division` this request was submitted to.
    division_id = db.Column(db.Integer, db.ForeignKey('division.id'),
            nullable=False)

    #: The :py:class:`~.Division` this request was submitted to.
    division = db.relationship('Division', back_populates='requests',
            cascade='save-update,merge,refresh-expire,expunge')

    #: A list of :py:class:`Action`\s that have been applied to this request,
    #: sorted in the order they were applied.
    actions = db.relationship('Action', back_populates='request',
            cascade='all,delete-orphan',
            order_by='desc(Action.timestamp)')

    #: A list of all :py:class:`Modifier`\s that have been applied to this
    #: request, regardless of wether they have been voided or not. They're
    #: sorted in the order they were added.
    modifiers = db.relationship('Modifier', back_populates='request',
            cascade='all,delete-orphan',
            lazy='dynamic', order_by='desc(Modifier.timestamp)')

    #: The URL of the source killmail.
    killmail_url = db.Column(db.String(512, convert_unicode=True),
            nullable=False)

    #: The ID of the :py:class:`~.Pilot` for the killmail.
    pilot_id = db.Column(db.Integer, db.ForeignKey('pilot.id'), nullable=False)

    #: The :py:class:`~.Pilot` who was the victim in the killmail.
    pilot = db.relationship('Pilot', back_populates='requests',
            cascade='save-update,merge,refresh-expire,expunge')

    #: The corporation of the :py:attr:`pilot` at the time of the killmail.
    corporation = db.Column(db.String(150, convert_unicode=True),
            nullable=False, index=True)

    #: The alliance of the :py:attr:`pilot` at the time of the killmail.
    alliance = db.Column(db.String(150, convert_unicode=True), nullable=True,
            index=True)

    #: The type of ship that was destroyed.
    ship_type = db.Column(db.String(75, convert_unicode=True), nullable=False,
            index=True)

    # TODO: include timezones
    #: The date and time of when the ship was destroyed.
    kill_timestamp = db.Column(DateTime, nullable=False, index=True)

    base_payout = db.Column(PrettyNumeric(precision=15, scale=2),
            default=Decimal(0))
    """The base payout for this request.

    This value is clamped to a lower limit of 0. It can only be changed when
    this request is in an :py:attr:`~ActionType.evaluating` state, or else a
    :py:exc:`ModifierError` will be raised.
    """

    #: The payout for this requests taking into account all active modifiers.
    payout = db.Column(PrettyNumeric(precision=15, scale=2),
            default=Decimal(0), index=True, nullable=False)

    #: Supporting information for the request.
    details = db.deferred(db.Column(db.Text(convert_unicode=True)))

    #: The current status of this request
    status = db.Column(ActionType.db_type(), nullable=False,
            default=ActionType.evaluating)
    """This attribute is automatically kept in sync as :py:class:`Action`\s are
    added to the request. It should not be set otherwise.

    At the time an :py:class:`Action` is added to this request, the type of
    action is checked and the state diagram below is enforced. If the action is
    invalid, an :py:exc:`ActionError` is raised.

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

    #: The solar system this loss occured in.
    system = db.Column(db.String(25, convert_unicode=True), nullable=False,
            index=True)

    #: The constellation this loss occured in.
    constellation = db.Column(db.String(25, convert_unicode=True),
            nullable=False, index=True)

    #: The region this loss occured in.
    region = db.Column(db.String(25, convert_unicode=True), nullable=False,
            index=True)

    @hybrid_property
    def finalized(self):
        return self.status in ActionType.finalized

    @finalized.expression
    def finalized(cls):
        return db.or_(cls.status == ActionType.paid,
                cls.status == ActionType.rejected)

    def __init__(self, submitter, details, division, killmail, **kwargs):
        """Create a :py:class:`Request`.

        :param submitter: The user submitting this request
        :type submitter: :py:class:`~.User`
        :param str details: Supporting details for this request
        :param division: The division this request is being submitted to
        :type division: :py:class:`~.Division`
        :param killmail: The killmail this request pertains to
        :type killmail: :py:class:`~.Killmail`
        """
        with db.session.no_autoflush:
            self.division = division
            self.details = details
            self.submitter = submitter
            # Pull basically everything else from the killmail object
            # The base Killmail object has an iterator defined that returns tuples
            # of Request attributes and values for those attributes
            for attr, value in killmail:
                setattr(self, attr, value)
            # Set default values before a flush
            if self.base_payout is None and 'base_payout' not in kwargs:
                self.base_payout = Decimal(0)
        super(Request, self).__init__(**kwargs)

    @db.validates('base_payout')
    def _validate_payout(self, attr, value):
        """Ensures that base_payout is positive. The value is clamped to 0."""
        if current_app.config['SRP_SKIP_VALIDATION']:
            return Decimal(value)
        # Allow self.status == None, as the base payout may be set in the
        # initializing state before the status has been set.
        if self.status == ActionType.evaluating or self.status is None:
            if value is None or value < 0:
                return Decimal('0')
            else:
                return Decimal(value)
        else:
            raise ModifierError(gettext(u"The request must be in the "
                                        u"evaluating state to change the base "
                                        u"payout."))

    state_rules = {
        ActionType.evaluating: {
            ActionType.incomplete: (PermissionType.review,
                PermissionType.admin),
            ActionType.rejected: (PermissionType.review,
                PermissionType.admin),
            ActionType.approved: (PermissionType.review,
                PermissionType.admin),
        },
        ActionType.incomplete: {
            ActionType.rejected: (PermissionType.review,
                PermissionType.admin),
            # Special case: the submitter can change it to evaluating by
            # changing the division or updating the details.
            ActionType.evaluating: (PermissionType.review,
                PermissionType.admin),
        },
        ActionType.rejected: {
            ActionType.evaluating: (PermissionType.review,
                PermissionType.admin),
        },
        ActionType.approved: {
            # Special case: the submitter can change it to evaluating by
            # changing the division.
            ActionType.evaluating: (PermissionType.review,
                PermissionType.admin),
            ActionType.paid: (PermissionType.pay, PermissionType.admin),
        },
        ActionType.paid: {
            ActionType.approved: (PermissionType.pay, PermissionType.admin),
            ActionType.evaluating: (PermissionType.pay, PermissionType.admin),
        },
    }

    def valid_actions(self, user):
        """Get valid actions (besides comment) the given user can perform."""
        possible_actions = self.state_rules[self.status]
        def action_filter(action):
            return user.has_permission(possible_actions[action],
                    self.division)
        return filter(action_filter, possible_actions)

    @db.validates('status')
    def _validate_status(self, attr, new_status):
        """Enforces that status changes follow the status state machine.
        When an invalid change is attempted, :py:class:`ActionError` is
        raised.
        """
        if current_app.config['SRP_SKIP_VALIDATION']:
            return new_status
        if new_status == ActionType.comment:
            raise ValueError(gettext(
                u"Comment is not a valid status"))
        # Initial status
        if self.status is None:
            return new_status
        rules = self.state_rules[self.status]
        if new_status not in rules:
            error_text = gettext(u"%(new_status)s is not a valid status to "
                                 u"change to from %(old_status)s.",
                    new_status=new_status,
                    old_status=self.status)
            raise ActionError(error_text)
        return new_status

    @db.validates('actions')
    def _verify_action_permissions(self, attr, action):
        """Verifies that permissions for Actions being added to a Request."""
        if current_app.config['SRP_SKIP_VALIDATION']:
            return action
        if action.type_ is None:
            # Action.type_ are not nullable, so rely on the fact that it will
            # be set later to let it slide now.
            return action
        elif action.type_ != ActionType.comment:
            # Peek behind the curtain to see the history of the status
            # attribute.
            status_history = db.inspect(self).attrs.status.history
            if status_history.has_changes():
                new_status = status_history.added[0]
                old_status = status_history.deleted[0]
            else:
                new_status = action.type_
                old_status = self.status
            rules = self.state_rules[old_status]
            permissions = rules[new_status]
            # Handle the special cases called out in state_rules
            if action.user == self.submitter and \
                    new_status == ActionType.evaluating and \
                    old_status in ActionType.pending:
                # Equivalent to self.status in (approved, incomplete) as
                # going from evaluating to evaluating is invalid (as checked by
                # the status validator).
                return action
            if not action.user.has_permission(permissions, self.division):
                raise ActionError(gettext(u"Insufficient permissions to "
                                          u"perform that action."))
        elif action.type_ == ActionType.comment:
            if action.user != self.submitter \
                    and not action.user.has_permission(
                            (PermissionType.review, PermissionType.pay,
                                PermissionType.admin),
                            self.division):
                raise ActionError(gettext(u"You must either own or have "
                                          u"special privileges to comment on "
                                          u"this request."))
        return action

    def __repr__(self):
        return "{x.__class__.__name__}({x.submitter}, {x.division}, {x.id})".\
                format(x=self)

    @property
    def transformed(self):
        """Get a special HTML representation of an attribute.

        Divisions can have a transformer defined on various attributes that
        output a URL associated with that attribute. This property provides
        easy access to the output of any transformed attributes on this
        request.
        """
        class RequestTransformer(object):
            def __init__(self, request):
                self._request = request

            def __getattr__(self, attr):
                raw_value = getattr(self._request, attr)
                if attr in self._request.division.transformers:
                    transformer = self._request.division.transformers[attr]
                    return Markup(u'<a href="{link}" target="_blank">'
                                  u'{value} <i class="fa fa-external-link">'
                                  u'</i></a>').format(
                                        link=transformer(raw_value),
                                        value=str(raw_value))
                else:
                    return raw_value

            def __iter__(self):
                for attr, transformer in\
                        self._request.division.transformers.items():
                    if attr == 'ship_type':
                        yield ('ship', transformer(getattr(self._request,
                                attr)))
                    else:
                        yield (attr, transformer(getattr(self._request, attr)))

        return RequestTransformer(self)

    def _json(self, extended=False):
        try:
            parent = super(Request, self)._json(extended)
        except AttributeError:
            parent = {}
        parent[u'href'] = url_for('requests.get_request_details',
                request_id=self.id)
        attrs = (u'killmail_url', u'kill_timestamp', u'pilot',
                 u'alliance', u'corporation', u'submitter',
                 u'division', u'status', u'base_payout', u'payout',
                 u'details', u'id', u'ship_type', u'system', u'constellation',
                 u'region')
        for attr in attrs:
            if attr == u'ship_type':
                parent['ship'] = self.ship_type
            elif u'payout' in attr:
                payout = getattr(self, attr)
                parent[attr] = payout.currency()
            else:
                parent[attr] = getattr(self, attr)
        parent[u'submit_timestamp'] = self.timestamp
        if extended:
            parent[u'actions'] = map(lambda a: a._json(True), self.actions)
            parent[u'modifiers'] = map(lambda m: m._json(True), self.modifiers)
            parent[u'valid_actions'] = self.valid_actions(current_user)
            parent[u'transformed'] = dict(self.transformed)
        return parent


# Define event listeners for syncing the various denormalized attributes

@listens_for(Action.type_, 'set')
def _action_type_to_request_status(action, new_status, old_status, initiator):
    """Set the Action's Request's status when the Action's type is changed."""
    if action.request is not None and new_status != ActionType.comment:
        action.request.status = new_status


@listens_for(Request.actions, 'append')
def _request_status_from_actions(srp_request, action, initiator):
    """Updates Request.status when new Actions are added."""
    # Pass when Action.type_ is None, as it'll get updated later
    if action.type_ is not None and action.type_ != ActionType.comment:
        srp_request.status = action.type_


@listens_for(Request.base_payout, 'set')
def _recalculate_payout_from_request(srp_request, base_payout, *args):
    """Recalculate a Request's payout when the base payout changes."""
    if base_payout is None:
        base_payout = Decimal(0)
    voided = Modifier._voided_select()
    modifiers = srp_request.modifiers.join(voided,
                voided.c.modifier_id==Modifier.id)\
            .filter(~voided.c.voided)\
            .order_by(False)
    absolute = modifiers.join(AbsoluteModifier).\
            with_entities(db.func.sum(AbsoluteModifier.value)).\
            scalar()
    if not isinstance(absolute, Decimal):
        absolute = Decimal(0)
    relative = modifiers.join(RelativeModifier).\
            with_entities(db.func.sum(RelativeModifier.value)).\
            scalar()
    if not isinstance(relative, Decimal):
        relative = Decimal(0)
    payout = (base_payout + absolute) * (Decimal(1) + relative)
    srp_request.payout = PrettyDecimal(payout)


@listens_for(Modifier.request, 'set', propagate=True)
@listens_for(Modifier.voided_user, 'set', propagate=True)
def _recalculate_payout_from_modifier(modifier, value, *args):
    """Recalculate a Request's payout when it gains a Modifier or when one of
    its Modifiers is voided.
    """
    # Force a flush at the beginning, then delay other flushes
    db.session.flush()
    with db.session.no_autoflush:
        # Get the request for this modifier
        if isinstance(value, Request):
            # Triggered by setting Modifier.request
            srp_request = value
        else:
            # Triggered by setting Modifier.voided_user
            srp_request = modifier.request
        voided = Modifier._voided_select()
        modifiers = srp_request.modifiers.join(voided,
                    voided.c.modifier_id==Modifier.id)\
                .filter(~voided.c.voided)\
                .order_by(False)
        absolute = modifiers.join(AbsoluteModifier).\
                with_entities(db.func.sum(AbsoluteModifier.value)).\
                scalar()
        if not isinstance(absolute, Decimal):
            absolute = Decimal(0)
        relative = modifiers.join(RelativeModifier).\
                with_entities(db.func.sum(RelativeModifier.value)).\
                scalar()
        if not isinstance(relative, Decimal):
            relative = Decimal(0)
        # The modifier that's changed isn't reflected yet in the database, so we
        # apply it here.
        if isinstance(value, Request):
            # A modifier being added to the Request
            if modifier.voided:
                # The modifier being added is already void
                return
            direction = Decimal(1)
        else:
            # A modifier already on a request is being voided
            direction = Decimal(-1)
        if isinstance(modifier, AbsoluteModifier):
            absolute += direction * modifier.value
        elif isinstance(modifier, RelativeModifier):
            relative += direction * modifier.value
        payout = (srp_request.base_payout + absolute) * \
                (Decimal(1) + relative)
        srp_request.payout = PrettyDecimal(payout)


# The next few lines are responsible for adding a full text search index on the
# Request.details column for MySQL.
_create_fts = DDL('CREATE FULLTEXT INDEX ix_%(table)s_details_fulltext '
                       'ON %(table)s (details);')
_drop_fts = DDL('DROP INDEX ix_%(table)s_details_fulltext ON %(table)s')


event.listen(
        Request.__table__,
        'after_create',
        _create_fts.execute_if(dialect='mysql')
)


event.listen(
        Request.__table__,
        'before_drop',
        _drop_fts.execute_if(dialect='mysql')
)
