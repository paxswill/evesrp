import six
from evesrp import new_models as models
from evesrp import search_filter
from . import errors


class BrowseActivity(object):

    def __init__(self, store, user):
        self.store = store
        if isinstance(user, six.integer_types):
            user = self.store.get_user(user_id=user)
        self.user = user

    _valid_fields = frozenset((
        'killmail_id',  # aka Killmail.id_
        'kill_timestamp',  # aka Killmail.timestamp
        # All of these are combo types, with an ID and name being returned
        'type',
        'pilot',
        'corporation',
        'alliance',
        'solar_system',
        'constellation',
        'region',
        'details',
        'division',  # Combo of division.id_ and division.name
        'submit_timestamp',  # aka Request.timestamp
        'status',
        'payout',
        'base_payout',
    ))

    def _list(self, search=None, fields=None):
        # if fields is None, return fully formed Request objects,
        # otherwise, return a collection of dicts, with the keys being the
        # field names.
        if fields is None:
            requests = self.store.filter_requests(search)
            killmail_ids = {r.killmail_id for r in requests}
            killmails = self.store.get_killmails(killmail_ids=killmail_ids)
            return {
                'requests': requests,
                'killmails': killmails,
            }
        else:
            field_set = set(fields)
            if not self._valid_fields.issuperset(field_set):
                invalid_fields = field_set.difference(self._valid_fields)
                raise errors.InvalidFieldsError(*invalid_fields)
            return self.store.filter_sparse(search, field_set)

    def list_personal(self, search=None, fields=None):
        personal_search = search_filter.Search()
        personal_search.add_filter('user_id', self.user.id_)
        personal_search.merge(search)
        return self._list(search=personal_search, fields=fields)

    def _create_permission_search(self, permissions):
        # Just in case only one permission is given instead of a collection
        try:
            len(permissions)
        except TypeError:
            permissions = {permissions, }
        user_permissions = self.user.get_permissions(self.store)
        division_ids = [perm[0] for perm in user_permissions if perm[1] in
                        permissions]
        permission_search = search_filter.Search()
        for division_id in division_ids:
            permission_search.add_filter('division_id', division_id)
        return permission_search

    def list_review(self, search=None, fields=None):
        review_search = self._create_permission_search(
            models.PermissionType.review)
        for status in models.ActionType.pending:
            review_search.add_filter('status', status)
        review_search.merge(search)
        return self._list(search=review_search, fields=fields)

    def list_pay(self, search=None, fields=None):
        pay_search = self._create_permission_search(models.PermissionType.pay)
        pay_search.add_filter('status', models.ActionType.approved)
        pay_search.merge(search)
        return self._list(search=pay_search, fields=fields)

    def list_all(self, search=None, fields=None):
        if not self.user.admin:
            # All search is still constrained by permissions
            all_search = self._create_permission_search(
                models.PermissionType.elevated)
        else:
            # Global admin users aren't filtered
            all_search = search_filter.Search()
        all_search.merge(search)
        return self._list(search=all_search, fields=fields)
