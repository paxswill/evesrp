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
        'killmail_id', # aka Killmail.id_
        'kill_timestamp', # aka Killmail.timestamp
        # All of these are combo types, with an ID and name being returned
        'type',
        'pilot',
        'corporation',
        'alliance',
        'solar_system',
        'constellation',
        'region',
        'details',
        'division', # Combo of division.id_ and division.name
        'submit_timestamp', # aka Request.timestamp
        'status',
        'payout',
        'base_payout',
    ))

    def _list(self, filters=None, fields=None):
        # if fields is None, return fully formed Request objects,
        # otherwise, return a collection of dicts, with the keys being the
        # field names.
        if fields is None:
            requests = self.store.get_requests(filters=filters)
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
            return self.store.get_sparse(filters=filters, fields=field_set)

    def list_personal(self, filters=None, fields=None):
        personal_filter = search_filter.Filter().add(user=self.user.id_)
        personal_filter = personal_filter.merge(filters)
        return self._list(filters=personal_filter, fields=fields)

    def _create_permission_filter(self, permissions):
        # Just in case only one permission is given instead of a collection
        try:
            len(permissions)
        except TypeError:
            permissions = {permissions,}
        user_permissions = self.user.get_permissions(self.store)
        division_ids = [perm[0] for perm in user_permissions if perm[1] in
                        permissions]
        permission_filter = search_filter.Filter()
        for division_id in division_ids:
            permission_filter = permission_filter.add(division=division_id)
        return permission_filter

    def list_review(self, filters=None, fields=None):
        review_filter = self._create_permission_filter(
            models.PermissionType.review)
        for status in models.ActionType.pending:
            review_filter = review_filter.add(status=status)
        review_filter = review_filter.merge(filters)
        return self._list(filters=review_filter, fields=fields)

    def list_pay(self, filters=None, fields=None):
        pay_filter = self._create_permission_filter(models.PermissionType.pay)
        pay_filter = pay_filter.add(status=models.ActionType.approved)
        pay_filter = pay_filter.merge(filters)
        return self._list(filters=pay_filter, fields=fields)

    def list_all(self, filters=None, fields=None):
        if not self.user.admin:
            # All filter is still constrained by permissions
            all_filter = self._create_permission_filter(
                models.PermissionType.elevated)
            # Union personal filter and elevated filter
            self.store.run_search(filters)
        else:
            # Global admin users aren't filtered
            all_filter = search_filter.Filter()
        all_filter = all_filter.merge(filters)
        return self._list(filters=all_filter, fields=fields)
