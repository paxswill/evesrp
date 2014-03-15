import datetime as dt

from . import db
from .auth import User, Group, Division


class AutoID(object):
    """Mixin adding an integer column named 'id'."""
    id = db.Column(db.Integer, primary_key=True)


class Timestamped(object)
    """Mixin adding a timestamp column.

    The timestamp defaults to the current time.
    """
    timestamp = db.Column(db.Datetime, nullable=False,
            default=dt.datetime.utcnow())


class Action(db.Model, AutoID, Timestamped):
    """Actions change the state of a Request.
    
    With the exception of the comment action (which does nothing), actions
    change the state of a Request.
    """
    __tablename__ = 'actions'
    action_type = db.Column(db.Enum('unevaluated', 'evaluated', 'paid',
            'rejected', 'incomplete', 'comment', name='action_type'), nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='actions')
    note = db.Column(db.Text)


class Modifier(db.Model, AutoID, Timestamped):
    """Modifiers apply bonuses or penalties to Requests.

    Modifiers come in two varieties, absolute and percentage. Absolue modifiers
    are things like "2m ISK cyno bonus" or "5m reduction for meta guns".
    Percentage modifiers apply as a percentage, such as "25% reduction for nerf
    tank" or "15% alliance logistics bonus". They can also be voided at a later
    date. The user who voided a modifier and when they did are recorded.
    """
    __tablename__ = 'modifiers'
    modifier_type = db.Column(db.Enum('absolute', 'percentage',
            name='modifier_type'), nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'))
    # The data type of the value column is not set in stone yet. It might
    # change alter as I think about wether it should be a float or maybe
    # decimal, or maybe even integer.
    # For now, if the modifier_type is absolute, it should be treated as the
    # coefficient of a value in scientific notation raised to the 6th power. In
    # short, in millions.
    value = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User')
    note = db.Column(db.Text)
    voided = db.Column(db.Boolean, nullable=False, default=False)
    voided_user_id = db.Column(db.Integer, db.ForeignKey('users.id'),
            nullable=True)
    voided_user = db.relationship('User')
    voided_timestamp = db.Column(db.DateTime)


class Request(db.Model, AutoID, Timestamped):
    """Requests represent SRP requests."""
    __tablename__ = 'requests'
    submitter_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    submitter = db.relationship('User', backref='requests')
    division_id = db.Column(db.Integer, db.ForeignKey('divisions.id'))
    division = db.relationship('Division', backref='requests')
    actions = db.relationship('Action', backref='request',
            order_by='desc(Action.timestamp)')
    modifiers = db.relationship('Modifier', backref='request',
            order_by='desc(Modifier.timestamp)')
    killmail_url = db.Column(db.String(512), nullable=False)
    # Same as Modifer.value, base_payout is the coefficient to 10^6 a.k.a in
    # millions
    base_payout = db.Column(db.Float)

