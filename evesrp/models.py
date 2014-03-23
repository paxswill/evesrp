import datetime as dt
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
    type_ = db.Column(db.Enum('unevaluated', 'evaluated', 'paid',
            'rejected', 'incomplete', 'comment', name='action_type'),
            nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'))
    request = db.relationship('Request', back_populates='actions')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='actions')
    note = db.Column(db.Text)


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
    voided = db.Column(db.Boolean, nullable=False, default=False)
    voided_user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
            nullable=True)
    voided_user = db.relationship('User', foreign_keys=[voided_user_id])
    voided_timestamp = db.Column(DateTime)


class Request(db.Model, AutoID, Timestamped):
    """Requests represent SRP requests."""
    __tablename__ = 'request'
    submitter_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    submitter = db.relationship('User', back_populates='requests')
    division_id = db.Column(db.Integer, db.ForeignKey('division.id'))
    division = db.relationship('Division', back_populates='requests')
    actions = db.relationship('Action', back_populates='request',
            order_by='desc(Action.timestamp)')
    modifiers = db.relationship('Modifier', back_populates='request',
            order_by='desc(Modifier.timestamp)')
    killmail_url = db.Column(db.String(512), nullable=False)
    # Same as Modifer.value, base_payout is the coefficient to 10^6 a.k.a in
    # millions
    base_payout = db.Column(db.Float)

