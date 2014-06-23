import datetime as dt
from decimal import Decimal
import locale
from sqlalchemy.types import DateTime
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from flask import Markup

from . import db
from .util import DeclEnum, classproperty, AutoID, Timestamped, AutoName
from .auth import PermissionType


class PrettyDecimal(Decimal):
    """:py:class:`~.Decimal` subclass that pretty-prints its string
    representation.

    It also returns that string representation for templating engines that
    support the ``__html__`` protocol.
    """

    def __str__(self):
        return locale.currency(self, symbol=False, grouping=True)

    def __html__(self):
        return Markup(str(self))


class PrettyNumeric(db.TypeDecorator):
    """Type Decorator for :py:class:`~.Numeric` that reformats the userland
    values into :py:class:`PrettyDecimal`\s.
    """

    impl = db.Numeric

    def process_result_value(self, value, dialect):
        return PrettyDecimal(value) if value is not None else None


class ActionType(DeclEnum):

    # The actual stored values are single character to make it easier on
    # engines that don't support native enum types.

    #: Status for a request being evaluated.
    evaluating = 'evaluating', 'Evaluating'

    #: Status for a request that has been evaluated and is awaitng payment.
    approved = 'approved', 'Approved'

    #: Status for a request that has been paid. This is a terminatint state.
    paid = 'paid', 'Paid'

    #: Status for a requests that has been rejected. This is a terminating
    #: state.
    rejected = 'rejected', 'Rejected'

    #: Status for a request that is missing details and needs further action.
    incomplete = 'incomplete', 'Incomplete'

    #: A special type of :py:class:`Action` representing a comment made on the
    #: request.
    comment = 'comment', 'Comment'

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


class ModifierError(ValueError):
    """Error raised when a modification is attempted to a :py:class:`Request`
    when it's in an invalid state.
    """
    pass


class Action(db.Model, AutoID, Timestamped, AutoName):
    """Actions change the state of a Request.
    
    With the exception of the comment action (which does nothing), actions
    change the state of a Request.
    """

    #: The action be taken. See :py:class:`ActionType` for possible values.
    type_ = db.Column(ActionType.db_type(), nullable=False)

    #: The ID of the :py:class:`Request` this action applies to.
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'))

    #: The :py:class:`Request` this action applies to.
    request = db.relationship('Request', back_populates='actions')

    #: The ID of the :py:class:`~.User` who made this action.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    #: The :py:class:`~.User` who made this action.
    user = db.relationship('User', back_populates='actions')

    #: Any additional notes for this action.
    note = db.Column(db.Text)

    def __init__(self, request, user, note=None, type_=None):
        if type_ is not None:
            self.type_ = type_
        self.user = user
        self.note = note
        self.timestamp = dt.datetime.utcnow()
        self.request = request

    @db.validates('type_')
    def set_request_type(self, attr, type_):
        if self.request is not None:
            if type_ != ActionType.comment and self.timestamp >=\
                    self.request.actions[0].timestamp:
                self.request.status = type_
        return type_

    def __repr__(self):
        return "{x.__class__.__name__}({x.request}, {x.user}, {x.type_})".\
                format(x=self)


class Modifier(db.Model, AutoID, Timestamped, AutoName):
    """Modifiers apply bonuses or penalties to Requests.

    This is an abstract base class for the pair of concrete implementations.
    Modifiers can be voided at a later date. The user who voided a modifier and
    when they did are recorded.
    """

    #: Discriminator column for SQLAlchemy
    _type = db.Column(db.String(20), nullable=False)

    #: The ID of the :py:class:`Request` this modifier applies to.
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'))

    #: The :py:class:`Request` this modifier applies to.
    request = db.relationship('Request', back_populates='modifiers')

    #: The ID of the :py:class`~.User` who added this modifier.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    #: The :py:class:`~.User` who added this modifier.
    user = db.relationship('User', foreign_keys=[user_id])

    #: Any notes explaining this modification.
    note = db.Column(db.Text)

    #: The ID of the :py:class:`~.User` who voided this modifier (if voided).
    voided_user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
            nullable=True)

    #: The :py:class:`~.User` who voided this modifier if it has been voided.
    voided_user = db.relationship('User', foreign_keys=[voided_user_id])

    #: If this modifier has been voided, this will be the timestamp of when it
    #: was voided.
    voided_timestamp = db.Column(DateTime)

    @hybrid_property
    def voided(self):
        """Boolean of whether this modifier has been voided or not."""
        return self.voided_user is not None and \
                self.voided_timestamp is not None

    @voided.expression
    def voided(cls):
        return db.and_(
                cls.voided_user_id != None,
                cls.voided_timestamp != None
        )

    @declared_attr
    def __mapper_args__(cls):
        """SQLAlchemy late-binding attribute to set mapper arguments.

        Obviates subclasses from having to specify polymorphic identities.
        """
        args = {'polymorphic_identity': cls.__name__}
        if cls.__name__ == 'Modifier':
            args['polymorphic_on'] = cls._type
        return args

    def __init__(self, request, user, note, value):
        self.user = user
        self.note = note
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
            raise ModifierError("Modifiers can only be voided when the request"
                                " is in the evaluating state.")
        if not user.has_permission(PermissionType.review,
                self.request.division):
            raise ModifierError("You must be a reviewer to be able to void "
                                "modifiers.")
        self.voided_user = user
        self.voided_timestamp = dt.datetime.utcnow()


class AbsoluteModifier(Modifier):
    """Subclass of :py:class:`Modifier` for representing absolute
    modifications.

    Absolute modifications are those that are not dependent on the value of
    :py:attr:`Request.base_payout`.
    """

    id = db.Column(db.Integer, db.ForeignKey('modifier.id'), primary_key=True)

    #: How much ISK to add or remove from the payout
    value = db.Column(PrettyNumeric(precision=15, scale=2), nullable=False, default=0.0)

    def __str__(self):
        return '{}M ISK {}'.format(self.value / 1000000,
                'bonus' if self.value >= 0 else 'penalty')


class RelativeModifier(Modifier):
    """Subclass of :py:class:`Modifier` for representing relative modifiers.

    Relative modifiers depend on the value of :py:attr:`Modifier.base_payout`
    to calculate their effect.
    """

    id = db.Column(db.Integer, db.ForeignKey('modifier.id'), primary_key=True)

    #: What percentage of the payout to add or remove
    value = db.Column(db.Float, nullable=False, default=0.0)

    def __str__(self):
        return '{}% {}'.format(self.value * 100,
                'bonus' if self.value >= 0 else 'penalty')


class Request(db.Model, AutoID, Timestamped, AutoName):
    """Requests represent SRP requests."""

    #: The ID of the :py:class:`~.User` who submitted this request.
    submitter_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    #: The :py:class:`~.User` who submitted this request.
    submitter = db.relationship('User', back_populates='requests')

    #: The ID of the :py:class`~.Division` this request was submitted to.
    division_id = db.Column(db.Integer, db.ForeignKey('division.id'),
            nullable=False)

    #: The :py:class:`~.Division` this request was submitted to.
    division = db.relationship('Division', back_populates='requests')

    #: A list of :py:class:`Action`\s that have been applied to this request,
    #: sorted in the order they were applied.
    actions = db.relationship('Action', back_populates='request',
            order_by='desc(Action.timestamp)')

    #: A list of all :py:class:`Modifier`\s that have been applied to this
    #: request, regardless of wether they have been voided or not. They're
    #: sorted in the order they were added.
    modifiers = db.relationship('Modifier', back_populates='request',
            order_by='desc(Modifier.timestamp)', lazy='dynamic')

    #: The URL of the source killmail.
    killmail_url = db.Column(db.String(512), nullable=False)

    #: The ID of the :py:class:`~.Pilot` for the killmail.
    pilot_id = db.Column(db.Integer, db.ForeignKey('pilot.id'), nullable=False)

    #: The :py:class:`~.Pilot` for the killmail this request is for.
    pilot = db.relationship('Pilot', back_populates='requests')

    #: The corporation of the :py:attr:`pilot` at the time of the killmail.
    corporation = db.Column(db.String(150), nullable=False, index=True)

    #: The alliance of the :py:attr:`pilot` at the time of the killmail.
    alliance = db.Column(db.String(150), nullable=True, index=True)

    #: The type of ship that was destroyed.
    ship_type = db.Column(db.String(75), nullable=False, index=True)

    #: The date and time of when the ship was destroyed.
    kill_timestamp = db.Column(DateTime, nullable=False, index=True)

    #: The base payout for this request in millions of ISK.
    #: :py:attr:`modifiers` apply to this value.
    base_payout = db.Column(PrettyNumeric(precision=15, scale=2), default=0.0)

    #: Supporting information for the request.
    details = db.deferred(db.Column(db.Text))

    #: The current status of this request
    status = db.Column(ActionType.db_type(), nullable=False,
            default=ActionType.evaluating)

    #: The solar system this loss occured in.
    system = db.Column(db.String(25), nullable=False, index=True)

    #: The constellation this loss occured in.
    constellation = db.Column(db.String(25), nullable=False, index=True)

    #: The region this loss occured in.
    region = db.Column(db.String(25), nullable=False, index=True)

    @property
    def payout(self):
        """The resulting payout taking all active :py:attr:`modifiers` into
        account.

        The return value is an internal class that will return different
        representations depending on the type it is being coerced to.
        :py:class:`Strings <str>` will be formatted accroding to the current
        locale with thousands separators, :py:func:`float`\s will be in
        millions of ISK, and :py:func:`ints`\s will be the total ISK value
        (equivalent to the string representation).
        """
        # Evaluation method for payout:
        # almost_payout = (sum(absolute_modifiers) + base_payout)
        # payout = almost_payout + (sum(percentage_modifiers) * almost_payout)
        abs_mods = db.session.query(db.func.sum(AbsoluteModifier.value))\
                .join(Request)\
                .filter(Modifier.request_id==self.id)\
                .filter(~Modifier.voided)
        rel_mods = db.session.query(db.func.sum(RelativeModifier.value))\
                .join(Request)\
                .filter(Modifier.request_id==self.id)\
                .filter(~Modifier.voided)
        absolute = abs_mods.one()[0]
        if absolute is None:
            absolute = Decimal(0)
        relative = rel_mods.one()[0]
        if relative is None:
            relative = Decimal(0)
        else:
            relative = Decimal.from_float(relative)
        payout = self.base_payout + absolute
        payout = payout + (payout * relative)

        return PrettyDecimal(payout)

    @hybrid_property
    def finalized(self):
        """If this request is in a finalized status (``'paid'`` or
        ``'rejected'``).
        """
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
    def validate_payout(self, attr, value):
        """Ensures that base_payout is positive. The value is clamped to 0."""
        if self.status == ActionType.evaluating or self.status is None:
            if value is None or value < 0:
                return Decimal(0.0)
            else:
                return Decimal(value)
        else:
            raise ModifierError("The request must be in the evaluating state "
                                "to change the base payout.")

    state_rules = {
        ActionType.evaluating: {
            ActionType.incomplete: (PermissionType.review,),
            ActionType.rejected: (PermissionType.review,),
            ActionType.approved: (PermissionType.review,),
            ActionType.evaluating: (PermissionType.review,
                PermissionType.submit),
        },
        ActionType.incomplete: {
            ActionType.rejected: (PermissionType.review,),
            ActionType.evaluating: (PermissionType.review,
                PermissionType.submit),
        },
        ActionType.rejected: {
            ActionType.evaluating: (PermissionType.review,),
        },
        ActionType.approved: {
            ActionType.evaluating: (PermissionType.review,),
            ActionType.paid: (PermissionType.pay,),
        },
        ActionType.paid: {
            ActionType.approved: (PermissionType.pay,),
            ActionType.evaluating: (PermissionType.pay,),
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
    def validate_status(self, attr, new_status):
        """Enforces that status changes follow the status state diagram below.
        When an invalid change is attempted, :py:class:`ActionError` is
        raised.

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

        def check_status(*valid_states):
            if new_status not in valid_states:
                raise ActionError("{} is not a valid status to change "
                        "to from {} (valid options: {})".format(new_status,
                                self.status, valid_states))


        if new_status == ActionType.comment:
            raise ValueError("ActionType.comment is not a valid status")
        # Initial status
        if self.status is None:
            return new_status
        rules = self.state_rules[self.status]
        if new_status not in rules:
            raise ActionError("{} is not a valid status to change to from {} "
                    "(valid options: {})".format(new_status,
                            self.status, list(rules.keys())))
        return new_status

    @db.validates('actions')
    def update_status_from_action(self, attr, action):
        """Updates :py:attr:`status` whenever a new :py:class:`~.Action`
        is added and verifies permissions.
        """
        if action.type_ is None:
            # Action.type_ are not nullable, so rely on the fact that it will
            # be set later to let it slide now.
            return action
        elif action.type_ != ActionType.comment:
            rules = self.state_rules[self.status]
            self.status = action.type_
            permissions = rules[action.type_]
            if not action.user.has_permission(permissions, self.division):
                raise ActionError("Insufficient permissions to perform that "
                                  "action.")
        elif action.type_ == ActionType.comment:
            if action.user != self.submitter \
                    and not action.user.has_permission(PermissionType.elevated,
                            self.division):
                raise ActionError("You must either own or have special"
                                  "privileges to comment on this request.")
        return action

    def __repr__(self):
        return "{x.__class__.__name__}({x.submitter}, {x.division}, {x.id})".\
                format(x=self)

    @db.validates('modifiers')
    def validate_add_modifier(self, attr, modifier):
        if self.status != ActionType.evaluating:
            raise ModifierError("Modifiers can only be added when the request "
                                "is in an evaluating state.")
        if not modifier.user.has_permission(PermissionType.review,
                self.division):
            raise ModifierError("Only reviewers can add modifiers.")
        return modifier

    @property
    def transformed(self):
        """Get a special HTML representation of an attribute.

        Divisions can have a transformer defined on a for attributes that
        output a URL associated with that attribute. This property provides
        easy access to the output of any transformed attributes on this
        request.
        """
        class RequestTransformer(object):
            def __getattr__(self, attr):
                raw_value = getattr(self._request, attr)
                if attr in self._request.division.transformers:
                    transformer = self._request.division.transformers[attr]
                    return Markup('<a href="{link}">{value}</a>').format(
                            link=transformer(raw_value), value=str(raw_value))
                else:
                    return raw_value

            def __init__(self, request):
                self._request = request
        return RequestTransformer(self)
