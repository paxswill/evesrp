import six
from . import errors
from .. import new_models as models


class PermissionsAdmin(object):

    def __init__(self, store, user):
        self.user = user
        self.store = store

    def create_division(self, division_name):
        if not self.user.admin:
            raise errors.AdminPermissionError(u"User '{}' has insufficient "
                                              u"permissions to create "
                                              u"divisions.".format(self.user))
        division = models.Division(division_name, None)
        division.id_ = self.store.add_division(division)
        return division


class DivisionAdmin(object):

    def __init__(self, store, user, division):
        self.store = store
        if isinstance(user, six.integer_types):
            user = self.store.get_user(user_id=user)
        self.user = user
        if isinstance(division, six.integer_types):
            division = self.store.get_division(division_id=division)
        self.division = division
        if not self.user.admin:
            permissions = self.store.get_permissions(
                division_id=self.division.id_,
                type_ = models.PermissionType.admin)
            if not permissions:
                error_message = (u"User '{}' has insufficient permissions to "
                                 u"administer divisions.")
                error_message = error_message.format(self.user.id_)
                raise errors.AdminPermissionError(error_message)

    def list_permissions(self, type_):
        permissions = self.store.get_permissions(division_id=self.division.id_,
                                                 type_=type_)
        return permissions
