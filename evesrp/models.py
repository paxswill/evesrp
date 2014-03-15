import datetime as dt

from . import db


class AutoID(object):
    """Mixin adding an integer column named 'id'."""
    id = db.Column(db.Integer, primary_key=True)


class Timestamped(object)
    """Mixin adding a timestamp column.

    The timestamp defaults to the current time.
    """
    timestamp = db.Column(db.Datetime, nullable=False,
            default=dt.datetime.utcnow())




# TODO Oh god, this tangled web of divisions, users and groups is bad. It needs
# to be refactored once it's working and tests that verify it works are
# written. Then, redo the organization.

class _DivisionDict(object):
    def __init__(self, submit, review, payout):
        self.submit = submit
        self.review = review
        self.payout = payout

    def __getitem__(self, key):
        if key == 'submit':
            return self.submit()
        elif key == 'review':
            return self.review()
        elif key == 'payout':
            return self.payout()
        else:
            raise KeyError("'{}' is not a valid key for
                DivisionDicts".format(key))
            return None


class User(db.Model, AutoID):
    """User base class.

    Represents a user, not only those who can submit requests but also
    evaluators and payers.
    """
    __tablename__ = 'users'
    username = db.Column(db.String(128), nullable=False)
    visible_name = db.Column(db.String(128))


class Group(db.Model, AutoID):
    """Base class for a group of users.

    Represents a group of users. Usable for granting permissions to submit,
    evaluate and pay.
    """
    __tablename__ = 'groups'
    name = db.Column(db.String(128), nullable=False)


submit_users = db.Table('submit_users', db.model.metadata,
        db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
        db.Column('division_id', db.Integer, db.ForeignKey('divisions.id')))

submit_groups = db.Table('submit_groups', db.model.metadata,
        db.Column('group_id', db.Integer, db.ForeignKey('groups.id')),
        db.Column('division_id', db.Integer, db.ForeignKey('divisions.id')))

review_users = db.Table('review_users', db.model.metadata,
        db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
        db.Column('division_id', db.Integer, db.ForeignKey('divisions.id')))

review_groups = db.Table('review_groups', db.model.metadata,
        db.Column('group_id', db.Integer, db.ForeignKey('groups.id')),
        db.Column('division_id', db.Integer, db.ForeignKey('divisions.id')))

payout_users = db.Table('payout_users', db.model.metadata,
        db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
        db.Column('division_id', db.Integer, db.ForeignKey('divisions.id')))

payout_groups = db.Table('payout_groups', db.model.metadata,
        db.Column('group_id', db.Integer, db.ForeignKey('groups.id')),
        db.Column('division_id', db.Integer, db.ForeignKey('divisions.id')))


class Division(db.Model, AutoID):
    """A reimbursement division.

    A division has (possible non-intersecting) groups of people that can submit
    requests, review requests, and pay out requests.
    """
    __tablename__ = 'divisions'
    name = db.Column(db.String(128), nullable=False)
    submit_users = db.relationship('User', secondary=submit_users,
            backref='_submit_divisions')
    submit_groups = db.relationship('Group', secondary=submit_groups,
            backref='_submit_divisions')
    review_users = db.relationship('User', secondary=review_users,
            backref='_review_divisions')
    review_groups = db.relationship('Group', secondary=review_groups,
            backref='_review_divisions')
    payout_users = db.relationship('User', secondary=payout_users,
            backref='_payout_divisions')
    payout_groups = db.relationship('Group', secondary=payout_groups,
            backref='_payout_divisions')

    @property
    def submitters(self):
        submitters = set(self.submit_users)
        for group in self.submit_groups:
            submitters.update(group.users)
        return submitters

    @property
    def reviewers(self):
        reviewers = set(self.review_users)
        for group in self.review_groups:
            reviewers.update(group.users)
        return reviewers

    @property
    def payers(self):
        payers = set(self.payout_users)
        for group in self.payout_groups:
            payers.update(group.users)
        return payers



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

