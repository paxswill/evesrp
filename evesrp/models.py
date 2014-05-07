import datetime as dt
from decimal import Decimal
import locale
from sqlalchemy.types import DateTime
from sqlalchemy.ext.hybrid import hybrid_property

from . import db


class AutoID(object):
    """Mixin adding a primary key integer column named 'id'."""
    id = db.Column(db.Integer, primary_key=True)


class Timestamped(object):
    """Mixin adding a timestamp column.

    The timestamp defaults to the current time.
    """
    timestamp = db.Column(DateTime, nullable=False,
            default=dt.datetime.utcnow())


action_type = db.Enum('evaluating', 'approved', 'paid', 'rejected',
        'incomplete', 'comment', name='action_type')


class Action(db.Model, AutoID, Timestamped):
    """Actions change the state of a Request.
    
    With the exception of the comment action (which does nothing), actions
    change the state of a Request.
    """

    __tablename__ = 'action'

    #: The action being taken. Must be one of: ``'evaluating'``,
    #: ``'approved'``, ``'paid'``, ``'rejected'``, ``'incomplete'``,
    #: or ``'comment'``.
    _type = db.Column(action_type, nullable=False)

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

    def __init__(self, request, user, note):
        self.request = request
        self.user = user
        self.note = note
        self.timestamp = dt.datetime.utcnow()

    @property
    def type_(self):
        return self._type

    @type_.setter
    def type_(self, type_):
        if type_ != 'comment' and self.timestamp >=\
                self.request.actions[0].timestamp:
            self.request.status = type_
        self._type = type_

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

    def __init__(self, request, user, note):
        self.request = request
        self.user = user
        self.note = note

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

    #: The :py:class`~.Division` this request was submitted to.
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
    status = db.Column(action_type, nullable=False, default='evaluating')

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
        return self.status == 'paid' or self.status == 'rejected'

    @finalized.expression
    def finalized(cls):
        return db.or_(cls.status == 'paid', cls.status == 'rejected')

    def __init__(self, submitter, details, division, killmail):
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

    def __repr__(self):
        return "{x.__class__.__name__}({x.submitter}, {x.division}, {x.id})".\
                format(x=self)
