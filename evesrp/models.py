import datetime as dt
from decimal import Decimal
import locale
from sqlalchemy.types import DateTime
from sqlalchemy.ext.hybrid import hybrid_property

from . import db
from .enum import DeclEnum, classproperty
from .auth import PermissionType


class AutoID(object):
    """Mixin adding a primary key integer column named 'id'."""
    id = db.Column(db.Integer, primary_key=True)


class Timestamped(object):
    """Mixin adding a timestamp column.

    The timestamp defaults to the current time.
    """
    timestamp = db.Column(DateTime, nullable=False,
            default=dt.datetime.utcnow())


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


class Action(db.Model, AutoID, Timestamped):
    """Actions change the state of a Request.
    
    With the exception of the comment action (which does nothing), actions
    change the state of a Request.
    """

    __tablename__ = 'action'

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


class Modifier(db.Model, AutoID, Timestamped):
    """Modifiers apply bonuses or penalties to Requests.

    Modifiers come in two varieties, absolute and percentage. Absolue modifiers
    are things like "2m ISK cyno bonus" or "5m reduction for meta guns".
    Percentage modifiers apply as a percentage, such as "25% reduction for nerf
    tank" or "15% alliance logistics bonus". They can also be voided at a later
    date. The user who voided a modifier and when they did are recorded.
    """

    __tablename__ = 'modifier'

    #: What kind of modifier this is, either ``'absolute'`` or
    #: ``'percentage'``.
    type_ = db.Column(db.Enum('absolute', 'percentage',
            name='modifier_type'), nullable=False)

    #: The ID of the :py:class:`Request` this modifier applies to.
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'))

    #: The :py:class:`Request` this modifier applies to.
    request = db.relationship('Request', back_populates='modifiers')

    #: The value of this modifier. If this is an absolute modifier (
    #: :py:attr:`type_` is ``'absolute'``) this is in millions of ISK. If
    #: :py:attr:`type_` is ``'percentage'``, this is the percentage of the
    #: bonus or deduction. If it's a bonus, still only set the value between
    #: 1.0 and 0.0. For example: a 20% bonus would be 0.20.
    value = db.Column(db.Float)

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

    def __init__(self, request, user, note, **kwargs):
        self.user = user
        self.note = note
        self.request = request
        super(Modifier, self).__init__(**kwargs)

    def __repr__(self):
        if self.type_ == 'absolute':
            value = "{}M ISK".format(self.value)
        else:
            value = "{}%".format(self.value)
        return ("{x.__class__.__name__}({x.request}, {x.user}, {value},"
                "{x.voided})".format(x=self, value=value))

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


class Request(db.Model, AutoID, Timestamped):
    """Requests represent SRP requests."""

    __tablename__ = 'request'

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
    base_payout = db.Column(db.Float, default=0.0)

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
        modifier_sum = db.session.query(db.func.sum(Modifier.value))\
                .join(Request)\
                .filter(Modifier.request_id==self.id)\
                .filter(~Modifier.voided)

        abs_mods = modifier_sum.filter(Modifier.type_=='absolute')
        per_mods = modifier_sum.filter(Modifier.type_=='percentage')
        absolute = abs_mods.one()[0]
        if absolute is None:
            absolute = 0
        percentage = per_mods.one()[0]
        if percentage is None:
            percentage = 0
        payout = self.base_payout + absolute
        payout = payout + (payout * percentage / 100)

        class _Payout(object):
            def __init__(self, payout):
                self.raw_payout = payout
                scaled = Decimal.from_float(self.raw_payout)
                scaled *= 1000000
                self.scaled_payout = scaled

            def __str__(self):
                return locale.format('%d', int(self), grouping=True)

            def __int__(self):
                return int(self.scaled_payout)

            def __float__(self):
                return self.raw_payout

        return _Payout(payout)

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
            self.base_payout = 0.0
        super(Request, self).__init__(**kwargs)

    @db.validates('base_payout')
    def validate_payout(self, attr, value):
        """Ensures that base_payout is positive. The value is clamped to 0."""
        if self.status == ActionType.evaluating or self.status is None:
            return float(value) if value >= 0 else 0.0
        else:
            raise ModifierError("The request must be in the evaluating state "
                                "to change the base payout.")

    state_rules = {
        ActionType.evaluating: {
            ActionType.incomplete: (PermissionType.review,),
            ActionType.rejected: (PermissionType.review,),
            ActionType.approved: (PermissionType.review,),
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
