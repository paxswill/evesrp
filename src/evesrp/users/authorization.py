import collections
import itertools

import six

from . import errors
from .. import new_models as models


class PermissionsAdmin(object):

    def __init__(self, store, user):
        self.user = user
        self.store = store

    def create_division(self, division_name):
        """Create a new division.

        :raises AdminPermissionError: if the user is not a global admin.
        :param str division_name: The name of the new division.
        """
        if not self.user.admin:
            raise errors.AdminPermissionError(u"User '{}' has insufficient "
                                              u"permissions to create "
                                              u"divisions.".format(self.user))
        return self.store.add_division(division_name)

    def list_divisions(self):
        """List all divisions a user is able to administer.

        For users marked as admins globally, this will be all divisions.
        Otherwise, it is just divisions a user has the admin permission in.

        :rtype: iterable of :py:class:`~.Division`
        """
        if self.user.admin:
            # admins see all divisions
            return self.store.get_divisions()
        else:
            permissions = self.user.get_permissions(self.store)
            division_ids = {permission[1] for permission in permissions
                            if permission[0] in models.PermissionType}
            divisions = self.store.get_divisions(division_ids)
            return divisions

    def list_permissions(self):
        """List permissions the user has, grouped by division.

        Returns a dict with the keys being :py:class:`~.Division` objects and
        the values a set of :py:class:`~.PermissionType` members that the user
        has in each division.

        :rtype: dict
        """
        permissions = self.user.get_permissions(self.store)
        division_ids = {permission[1] for permission in permissions
                        if permission[0] in models.PermissionType}
        divisions = self.store.get_divisions(division_ids)
        divisions_map = {d.id_: d for d in divisions}
        permissions_map = {}
        for permission_type, permission_id in permissions:
            # Skip non-granted permissions (ex: user_id)
            if permission_type not in models.PermissionType:
                continue
            division = divisions_map[permission_id]
            if division not in permissions_map:
                permissions_map[division] = set()
            permissions_map[division].add(permission_type)
        return permissions_map

    def list_entities(self):
        # Entity listing is only availabe to admin users, either global admins
        # or with an admin permission in a division
        if not self.user.admin:
            # Check for an admin permission
            admin_permissions = list(self.store.get_permissions(
                type_=models.PermissionType.admin,
                entity_id=self.user.id_))
            if not len(admin_permissions):
                raise errors.AdminPermissionError(u"User '{}' has insufficient"
                                                  u" permissions to list all "
                                                  u"entities.")
        users = self.store.get_users()
        groups = self.store.get_groups()
        return itertools.chain(users, groups)


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
            permissions = set(permissions)
            if not permissions:
                error_message = (u"User '{}' has insufficient permissions to "
                                 u"administer divisions.")
                error_message = error_message.format(new_user.id_)
                raise errors.AdminPermissionError(error_message)
        self._user = new_user

    def list_entities(self, permission_type):
        permissions = self.store.get_permissions(division_id=self.division.id_,
                                                 type_=permission_type)
        entities = {self.store.get_entity(p.entity_id) for p in permissions}
        return entities

    def list_all_entities(self):
        permissions = collections.OrderedDict()
        # Enforcing order for later display
        ordered_permissions = (
            models.PermissionType.submit,
            models.PermissionType.review,
            models.PermissionType.pay,
            models.PermissionType.audit,
            models.PermissionType.admin,
        )
        for permission in ordered_permissions:
            permissions[permission] = self.list_entities(permission)
        return permissions

    def add_permission(self, entity, permission):
        return self.store.add_permission(self.division.id_, entity.id_,
                                         permission)

    def remove_permission(self, entity, permission):
       self.store.remove_permission(self.division.id_, entity.id_, permission)

