import itertools

import six

from evesrp import new_models as models
from . import errors


class BaseStore(object):
    """Basic implementation of a storage provider.
    """

    # Authentication

    def get_authn_user(self, provider_uuid, provider_key):
        """Get an :py:class:`~.AuthenticatedUser` from storage.

        If a user is unable to be found for the provided provider and key, the
        string `u'not found'` will be present in the errors array.

        :param provider_uuid: The UUID for the
            :py:class:`~.AuthenticationProvider` for this
            :py:class:`~.AuthenticatedUser`.
        :type provider_uuid: :py:class:`uuid.UUID`
        :param str provider_key: The key identifying a unique user to the
            authentication provider.
        :return: The user (if found).
        :rtype: :py:class:`~.AuthenticatedUser` or `None`
        """
        raise NotImplementedError

    def add_authn_user(self, user_id, provider_uuid, provider_key,
                       extra_data=None, **kwargs):
        raise NotImplementedError

    def save_authn_user(self, authn_user):
        raise NotImplementedError

    def get_authn_group(self, provider_uuid, provider_key):
        raise NotImplementedError

    def add_authn_group(self, group_id, provider_uuid, provider_key,
                        extra_data=None, **kwargs):
        raise NotImplementedError

    def save_authn_group(self, authn_group):
        raise NotImplementedError

    # Divisions

    def get_division(self, division_id):
        raise NotImplementedError

    def get_divisions(self, division_ids=None):
        """Get multiple divisions.

        If a collection of :py:class:`~.Division` IDs is given, only the
        divisions with those IDs are fetched. If no IDs are given, all
        divisions are fetched. If an ID is given for a non-existant division,
        no error is raised.

        :param division_ids: Division IDs to check for.
        :type division_ids: None or :py:class:`collections.Container`
        :rtype: iterable
        """
        raise NotImplementedError

    def add_division(self, name):
        raise NotImplementedError

    def save_division(self, division):
        raise NotImplementedError

    # Removing Divisions is not supported.
    # Being able to remove Divisions would also entail removing all Requests to
    # that Division, and all Actions and Modifiers for those Requests, and if
    # that's the last Request for a Killmail, removing that Killmail. You'd
    # also lose all records from that division, which is kinda the goal of this
    # application (keeping records).

    # Permissions

    def get_permissions(self, **kwargs):
        # entity_id, division_id, types, type_
        raise NotImplementedError

    def add_permission(self, division_id, entity_id, type_):
        raise NotImplementedError

    def remove_permission(self, *args, **kwargs):
        """Remove a Permission from storage.
        There are two modes of operation for this method:
            remove_permission(permission)
        or
            remove_permission(division_id, entity_id, type_)

        Because the combination of division, entity and permission type must be
        unique, you can refer to a permission either by it's ID or the tuple of
        those values. For the second mode of operation, keyword or positional
        arguments are allowed.
        """
        raise NotImplementedError

    # Users and Groups

    def get_user(self, user_id):
        raise NotImplementedError

    def get_users(self, group_id=None):
        """Get multiple users.

        If a :py:class:`~.Group` ID number is given, only members of that groups
        will be returned. Otherwise, every user is returned.

        :param group_id: :py:attr:`~.Group.id_` to get users for.
        :type group_id: int or None
        :rtype: iterable
        """
        raise NotImplementedError

    def add_user(self, name, is_admin=False):
        raise NotImplementedError

    def save_user(self, user):
        """Save a modified user.

        The only two attributes that can save on a user are the user's name and
        whether thay are an admin or not.

        :param user: The user to save.
        :type user: :py:class:`~.User`
        """
        raise NotImplementedError

    def get_group(self, group_id):
        raise NotImplementedError

    def get_groups(self, user_id=None):
        """Get multiple groups.

        If given a :py:class:`~.User` ID, looks up all groups that user is a
        member of. Otherwise, it returns all groups.

        :param user_id: A :py:attr:`~.User.id_` to look up groups for.
        :type user_id: int or None
        :rtype: iterable
        """
        raise NotImplementedError

    def add_group(self, name):
        raise NotImplementedError

    def save_group(self, group):
        """Save a changed group.

        The only attribute that can change on a group is
        :py:attr:`~.Group.name`. Any other changed attributes will not be
        saved.

        :param group: The group to save.
        :type group: :py:class:`~.Group`
        """
        raise NotImplementedError

    def get_entity(self, entity_id):
        """Get an entity, whether it's a user or a group.

        :rtype: :py:class:`~.User` or :py:class:`~.Group`
        """
        raise NotImplementedError

    def associate_user_group(self, user_id, group_id):
        raise NotImplementedError

    def disassociate_user_group(self, user_id, group_id):
        raise NotImplementedError

    # Killmails

    def get_killmail(self, killmail_id):
        raise NotImplementedError

    def get_killmails(self, killmail_ids):
        id_set = set(killmail_ids)
        for kid in id_set:
            try:
                yield self.get_killmail(kid)
            except errors.NotFoundError:
                pass

    def add_killmail(self, **kwargs):
        """Create a record for a killmail.

        :param int id_: The CCP ID for the killmail.
        :param int user_id: The internal ID for the user owning the character
            on this killmail at the time of first submission.
        :param int character_id: The CCP (and internal) ID for the
            :py:class:`~.Character` on this killmail belongs to (the victim in
            other words).
        :param int corporation_id: The CCP ID for the corporation the victim
            belonged to at the time of the loss.
        :param alliance_id: The CCP ID the victim's corporation was in at the
            time of the loss. May be `None` if they were not in an alliance.
        :type alliance_id: int or None
        :param int system_id: The CCP ID for the solar system the loss took
            place in.
        :param int constellation_id: The CCP ID of the constellation the loss
            took place in.
        :param int region_id: The CCP ID of the region the loss took place in.
        :param datetime timestamp: The date and time the loss happened.
        """
        raise NotImplementedError

    # Again, same reasons for not implementing Killmail removal as Division

    # Requests

    def get_request(self, request_id=None, killmail_id=None, division_id=None):
        """Retrieve a request for SRP.

        Either `request_id` or both `killmail_id` and `division_id` must be
        given.
        :param int request_id: The ID number for the request.
        :param int killmail_id: The ID for the killmail associated with a
            request.
        :param int division_id: The ID of the division associated with a
            request.
        """
        raise NotImplementedError

    def get_requests(self, killmail_id):
        raise NotImplementedError

    def add_request(self, killmail_id, division_id, details=u''):
        raise NotImplementedError

    def save_request(self, request):
        """Save an updated request to storage.

        The only attributes documented to be able to change on a request are
        `details`, `status`, `base_payout`, and `payout`. If any other
        attribute has been changed, it is not guaranteed to be saved.
        If the save failed for some reason, the errors list will have details.

        :param request: The updated request to save.
        :type request: :py:class:`evesrp.models.Request`
        :rtype: `None`
        """
        raise NotImplementedError

    # Request Actions

    def get_action(self, action_id):
        raise NotImplementedError

    def get_actions(self, request_id):
        raise NotImplementedError

    def add_action(self, request_id, type_, user_id, contents=u''):
        raise NotImplementedError

    # Modification of existing Actions is not something that should be
    # happening, so it's not implemented.

    # Request Modifiers

    def get_modifier(self, modifier_id):
        raise NotImplementedError

    def get_modifiers(self, request_id, void=None, type_=None):
        """Get modifers for a request.
        :param int request_id: The ID number of the request.
        :param void: If `True`, only return voided modifiers. For `False`, only
            return unvoided modifiers. If `None`, returns all modifiers,
            regardless of status.
        :type void: bool or None
        :param type_: If given, returns only modifiers of that type.
        :type type_: :py:class:`~.ModifierType` or None
        """
        raise NotImplementedError

    def add_modifier(self, request_id, user_id, type_, value, note=u''):
        raise NotImplementedError

    def void_modifier(self, modifier_id, user_id):
        """
        :param int modifier_id: The ID of the modifier to void.
        :param int user_id: The ID of the :py:class:`~.User` voiding this
            :py:class:`~.Modifier`.
        :return: The timestamp the :py:class:`~.Modifier` was voided.
        :rtype: :py:class:`datetime.datetime`
        """
        # In contrast to Actions, Modifiers are changed after creation, but
        # only in a specific manner: they are only voided (and unable to be
        # un-voided).
        raise NotImplementedError

    # Filtering

    def filter_requests(self, filters):
        raise NotImplementedError

    _mapped_fields = {
        'character_name': 'character_id',
        'corporation_name': 'corporation_id',
        'alliance_name': 'alliance_id',
        'type_name': 'type_id',
        'system_name': 'system_id',
        'constellation_name': 'constellation_id',
        'region_name': 'region_id',
    }
    for field_name in itertools.chain(models.Request.fields,
                                      models.Killmail.fields):
        if field_name.endswith('_id'):
            mapped_name = field_name[:-3] + '_name'
            _mapped_fields[mapped_name] = field_name

    @classmethod
    def map_fields(cls, field_names):
        real_fields = set()
        for field_name in field_names:
            if field_name in cls._mapped_fields:
                real_fields.add(cls._mapped_fields[field_name])
            else:
                real_fields.add(field_name)
        return real_fields

    def _format_sparse(self, request, fields, killmail=None, killmails=None):
        """Helper method for implementing `filter_sparse`

        `request` should be a `dict`, as well as `killmail` (if provided).
        `fields` should be a `set` of strings to include as keys in the output.

        If `fields` contains fields that need to be looked up on a `Killmail`
        instance and neither `killmail` nor `killmails` are given, an exception
        will be raised.
        `killmails` is a dict, with the keys being the integer IDs of the
        killmails, and the value being a `dict` of the killmail itself.
        """
        # killmail_id is available on both Request and Killmail
        shared_fields = models.Killmail.fields.intersection(
            models.Request.fields)
        no_shared_fields = set(fields)
        no_shared_fields.difference_update(shared_fields)
        if models.Request.fields.isdisjoint(no_shared_fields) and \
                killmail == killmails is None:
            raise TypeError(u"Either 'killmail' or 'killmails' must be given"
                            u" if a killmail field is being returned.")
        elif killmail is None and killmails is not None:
            killmail = killmails[request.killmail_id]
        # Construct the sparse request dictionary
        sparse_request = {}
        # A helper function to look up values from the appropriate object

        def lookup_field(field_name):
            # the timestamp fields are named the same on their objects
            if field_name.endswith('_timestamp'):
                real_field_name = 'timestamp'
            elif field_name == 'request_id':
                real_field_name = 'id_'
            else:
                real_field_name = field_name
            if field_name in models.Request.fields:
                obj = request
            elif field_name in models.Killmail.fields:
                obj = killmail
            return getattr(obj, real_field_name)

        # Fill in each field specified
        for field_name in fields:
            if field_name in self._mapped_fields:
                id_name = self._mapped_fields[field_name]
                id_value = lookup_field(id_name)
                # id_name is structured like 'foo_id', so the base name
                # is 'foo'
                base_name = id_name[:-3]
                getter = getattr(self, 'get_' + base_name)
                kwargs = {
                    id_name: id_value,
                }
                response = getter(**kwargs)
                try:
                    sparse_request[field_name] = response[u'name']
                except TypeError:
                    sparse_request[field_name] = response.name
            else:
                sparse_request[field_name] = lookup_field(field_name)
        return sparse_request

    def filter_sparse(self, filters, fields):
        full_requests = self.filter_requests(filters)
        format_kwargs = {'fields': fields}
        # Don't count fields on both Request and Killmail to figure out if we
        # need to fetch killmails
        shared_fields = models.Killmail.fields.intersection(
            models.Request.fields)
        no_shared_fields = set(fields)
        no_shared_fields.difference_update(shared_fields)
        if not models.Killmail.fields.isdisjoint(
                self.map_fields(no_shared_fields)):
            killmail_ids = {r.killmail_id for r in
                            self.filter_requests(filters)}
            full_killmails = self.get_killmails(killmail_ids=killmail_ids)
            format_kwargs['killmails'] = {km.id_: km for km in full_killmails}
        return [self._format_sparse(request, **format_kwargs)
                for request in self.filter_requests(filters)]

    # Characters

    def get_character(self, character_id):
        raise NotImplementedError

    def get_characters(self, user_id):
        raise NotImplementedError

    def add_character(self, user_id, character_id, character_name):
        raise NotImplementedError

    def save_character(self, character):
        """Save a modified character.

        The only things that can change are the character's name and their
        owning user's ID. Characters can have their name changed by CCP (for
        example, if it's found to be offensive). Characters can also be
        transferred to another account.
        :param character: The character to save.
        :type character: :py:class:`evesrp.models.Character`
        """
        raise NotImplementedError

    # User Notes

    def get_notes(self, subject_id):
        raise NotImplementedError

    def add_note(self, subject_id, submitter_id, contents):
        raise NotImplementedError

    # CCP Lookups

    def get_region(self, region_name=None, region_id=None,
                   constellation_name=None, constellation_id=None,
                   system_name=None, system_id=None):
        raise NotImplementedError

    def get_constellation(self, constellation_name=None, constellation_id=None,
                          system_name=None, system_id=None):
        raise NotImplementedError

    def get_system(self, system_name=None, system_id=None):
        raise NotImplementedError

    def get_alliance(self, alliance_name=None, alliance_id=None,
                     corporation_name=None, corporation_id=None,
                     character_name=None, character_id=None):
        raise NotImplementedError

    def get_corporation(self, corporation_name=None, corporation_id=None,
                        character_name=None, character_id=None):
        raise NotImplementedError

    def get_ccp_character(self, character_name=None, character_id=None):
        raise NotImplementedError

    def get_type(self, type_name=None, type_id=None):
        raise NotImplementedError
