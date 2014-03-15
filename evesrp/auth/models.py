from .. import db

users_groups = db.Table('users_groups', db.Model.metadata,
        db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
        db.Column('group_id', db.Integer, db.ForeignKey('groups.id')))


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
    evaluators and payers. The default implementation does _no_ authentication.
    To provide actual authentication, subclass the User module and implement
    blahdeblahblah.

    TODO: Actually put what to implement.
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), nullable=False, index=True)
    division_admin = db.Column(db.Boolean, nullable=False, default=False)
    full_admin = db.Column(db.Boolean, nullable=False, default=False)
    user_type = db.Column(db.String(50), nullable=False, default='user')
    __mapper_args__ = {
            'polymorphic_identity': 'user',
            'polymorphic_on': user_type
    }

    def _all_submit(self):
        submit = set(self._submit_divisions)
        for group in self.groups:
            submit.update(group._submit_divisions)
        return submit

    def _all_review(self):
        review = set(self._review_divisions)
        for group in self.groups:
            review.update(group._review_divisions)
        return review

    def _all_payout(self):
        payout = set(self._payout_divisions)
        for group in self.groups:
            payout.update(group._payout_divisions)
        return payout

    def __init__(self, *kwargs):
        self.divisions = _DivisionDict(self._all_submit, self._all_review,
                self._all_payout)
        super(User, self).__init__(kwargs)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)


class Group(db.Model, AutoID):
    """Base class for a group of users.

    Represents a group of users. Usable for granting permissions to submit,
    evaluate and pay.
    """
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    users = db.relationship('User', secondary=users_groups, backref=groups)


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
    id = db.Column(db.Integer, primary_key=True)
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
