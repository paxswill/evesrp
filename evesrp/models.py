import datetime as dt
from decimal import Decimal
import locale
from sqlalchemy.types import DateTime

from . import db


class AutoID(object):
    """Mixin adding an integer column named 'id'."""
    id = db.Column(db.Integer, primary_key=True)


class Timestamped(object):
    """Mixin adding a timestamp column.

    The timestamp defaults to the current time.
    """
    timestamp = db.Column(DateTime, nullable=False,
            default=dt.datetime.utcnow())


class Action(db.Model, AutoID, Timestamped):
    """Actions change the state of a Request.
    
    With the exception of the comment action (which does nothing), actions
    change the state of a Request.
    """
    __tablename__ = 'action'
    type_ = db.Column(db.Enum('evaluating', 'approved', 'paid',
            'rejected', 'incomplete', 'comment', name='action_type'),
            nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'))
    request = db.relationship('Request', back_populates='actions')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='actions')
    note = db.Column(db.Text)

    def __init__(self, request, user, note):
        self.request = request
        self.user = user
        self.note = note
        self.timestamp = dt.datetime.utcnow()


class Modifier(db.Model, AutoID, Timestamped):
    """Modifiers apply bonuses or penalties to Requests.

    Modifiers come in two varieties, absolute and percentage. Absolue modifiers
    are things like "2m ISK cyno bonus" or "5m reduction for meta guns".
    Percentage modifiers apply as a percentage, such as "25% reduction for nerf
    tank" or "15% alliance logistics bonus". They can also be voided at a later
    date. The user who voided a modifier and when they did are recorded.
    """
    __tablename__ = 'modifier'
    type_ = db.Column(db.Enum('absolute', 'percentage',
            name='modifier_type'), nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'))
    request = db.relationship('Request', back_populates='modifiers')
    # The data type of the value column is not set in stone yet. It might
    # change as I think about whether it should be a float or maybe
    # decimal, or maybe even integer.
    # For now, if the modifier_type is absolute, it should be treated as the
    # coefficient of a value in scientific notation raised to the 6th power. In
    # short, in millions.
    value = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', foreign_keys=[user_id])
    note = db.Column(db.Text)
    voided_user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
            nullable=True)
    voided_user = db.relationship('User', foreign_keys=[voided_user_id])
    voided_timestamp = db.Column(DateTime)

    @property
    def voided(self):
        return self.voided_user is not None and \
                self.voided_timestamp is not None

    def __init__(self, request, user, note):
        self.request = request
        self.user = user
        self.note = note

    def void(self, user):
        self.voided_user = user
        self.voided_timestamp = dt.datetime.utcnow()


class Request(db.Model, AutoID, Timestamped):
    """Requests represent SRP requests."""
    __tablename__ = 'request'
    submitter_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    submitter = db.relationship('User', back_populates='requests')
    division_id = db.Column(db.Integer, db.ForeignKey('division.id'),
            nullable=False)
    division = db.relationship('Division', back_populates='requests')
    actions = db.relationship('Action', back_populates='request',
            order_by='desc(Action.timestamp)')
    modifiers = db.relationship('Modifier', back_populates='request',
            order_by='desc(Modifier.timestamp)')
    killmail_url = db.Column(db.String(512), nullable=False)
    pilot_id = db.Column(db.Integer, db.ForeignKey('pilot.id'), nullable=False)
    pilot = db.relationship('Pilot', back_populates='requests')
    corporation = db.Column(db.String(150), nullable=False, index=True)
    alliance = db.Column(db.String(150), nullable=True, index=True)
    ship_type = db.Column(db.String(75), nullable=False)
    # Same as Modifer.value, base_payout is the coefficient to 10^6 a.k.a in
    # millions
    base_payout = db.Column(db.Float, default=0.0)
    details = db.Column(db.Text)

    @property
    def payout(self):
        payout = self.base_payout
        for modifier in self.modifiers:
            if modifier.voided:
                continue
            if modifier.type_ == 'absolute':
                payout += modifier.value
            elif modifier.type_ == 'percentage':
                if modifier.value > 0:
                    payout += payout * modifier.value / 100
                else:
                    payout -= payout * modifier.value / 100

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

    @property
    def status(self):
        for action in self.actions:
            if action.type_ == 'comment':
                continue
            else:
                return action.type_
        else:
            return 'evaluating'

    @property
    def finalized(self):
        return self.status in ('paid', 'rejected')

    def __init__(self, submitter, details, division, killmail):
        self.division = division
        self.details = details
        self.submitter = submitter
        # Pull basically everything else from the killmail object
        # The base Killmail object has an iterator defined that returns tuples
        # of Request attributes and values for those attributes
        for attr, value in killmail:
            setattr(self, attr, value)
