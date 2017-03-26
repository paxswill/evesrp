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
        return self.store.add_division(division_name)

    def list_divisions(self):
        permissions = self.user.get_permissions(self.store)
        division_ids = {permission.division_id for permission in permissions}
        divisions = self.store.get_divisions(division_ids)
        return divisions


class DivisionAdmin(object):

    def __init__(self, store, user, division):
        self.store = store
        if isinstance(user, six.integer_types):
            user = self.store.get_user(user_id=user)
        if isinstance(division, six.integer_types):
            division = self.store.get_division(division_id=division)
        # self.division _MUST_ be set before setting self.user
        self.division = division
        self.user = user

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, new_user):
        if not new_user.admin:
            permissions = self.store.get_permissions(
                entity_id=new_user.id_,
                division_id=self.division.id_,
                type_=models.PermissionType.admin)
            if not permissions:
                error_message = (u"User '{}' has insufficient permissions to "
                                 u"administer divisions.")
                error_message = error_message.format(new_user.id_)
                raise errors.AdminPermissionError(error_message)
        self._user = new_user

    def list_permissions(self, type_):
        permissions = self.store.get_permissions(division_id=self.division.id_,
                                                 type_=type_)
        return permissions
