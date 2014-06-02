from collections import namedtuple
from functools import partial
from flask.ext.login import current_user
from flask.ext.principal import Permission, UserNeed, RoleNeed,\
        identity_loaded, identity_changed, Identity, Principal
from . import PermissionType
from .models import Division


principal = Principal()


# This can be confusing, so here goes. Needs really only need to be tuples, of
# some unspecified (but known) length. So, we create named tuples, and then to
# make creating them easier freeze the first argument using partial.
ReimbursementNeed = namedtuple('ReimbursementNeed', ['method', 'division'])
SubmitRequestsNeed = partial(ReimbursementNeed, PermissionType.submit)
ReviewRequestsNeed = partial(ReimbursementNeed, PermissionType.review)
PayoutRequestsNeed = partial(ReimbursementNeed, PermissionType.pay)


# Now, create Permission classes for these kinds of needs.
class SubmitRequestsPermission(Permission):
    def __init__(self, div_or_request):
        if isinstance(div_or_request, Division):
            need = SubmitRequestsNeed(div_or_request.id)
        else:
            need = SubmitRequestsNeed(div_or_request.division.id)
        super(SubmitRequestsPermission, self).__init__(need)


class ReviewRequestsPermission(Permission):
    def __init__(self, div_or_request):
        if isinstance(div_or_request, Division):
            need = ReviewRequestsNeed(div_or_request.id)
        else:
            need = ReviewRequestsNeed(div_or_request.division.id)
        super(ReviewRequestsPermission, self).__init__(need)


class PayoutRequestsPermission(Permission):
    def __init__(self, div_or_request):
        if isinstance(div_or_request, Division):
            need = PayoutRequestsNeed(div_or_request.id)
        else:
            need = PayoutRequestsNeed(div_or_request.division.id)
        super(PayoutRequestsPermission, self).__init__(need)


admin_permission = Permission(RoleNeed('admin'))


def load_user_permissions(sender, identity):
    identity.user = current_user

    if current_user.is_authenticated():
        # Set user role (see and modify their own requests)j
        identity.provides.add(UserNeed(current_user.id))

        # Set division roles
        for perm in current_user.permissions:
            identity.provides.add(ReimbursementNeed(perm.permission,
                    perm.division.id))

        # If they're an admin, set that
        if current_user.admin:
            identity.provides.add(RoleNeed('admin'))
