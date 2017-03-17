import six


class BaseStore(object):
    """Basic implementation of a storage provider.

    All public methods that return something other than `None` return
    a :py:class:`dict` with at least a `u'result'` key. This key will be what
    is documented as the return value in the methods below. If the value for
    the result key is `None`, there will be an `u'errors'` key with an array of
    text strings detailing what went wrong. There may also be a `u'warnings'`
    key, following the same format as the errors, but for non-fatal warnings
    instead.
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

    def get_users(self, group_id):
        raise NotImplementedError

    def add_user(self, name, is_admin=False):
        raise NotImplementedError

    def get_group(self, group_id):
        raise NotImplementedError

    def get_groups(self, user_id):
        raise NotImplementedError

    def add_group(self, name):
        raise NotImplementedError

    def associate_user_group(self, user_id, group_id):
        raise NotImplementedError

    def disassociate_user_group(self, user_id, group_id):
        raise NotImplementedError

    # Killmails

    def get_killmail(self, killmail_id):
        raise NotImplementedError

    def get_killmails(self, killmail_ids):
        killmails = {self.get_killmail(kid)[u'result'] for kid in killmail_ids}
        # filter out any empty or None values
        killmails = filter(None, killmails)
        return {
            u'result': list(killmails),
        }

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

    _request_fields = frozenset((
        'killmail_id',
        'division',
        'division_id',
        'submit_timestamp',
        'details',
        'payout',
        'base_payout',
        'status',
    ))

    _killmail_fields = frozenset((
        # 'user' is not a field that can be queried in a sparse search because
        # sparse searches are to be used only for presentation to the user, and
        # the user shouldn't need to know the specific user behind a request,
        # only the character.
        'kill_timestamp',
        'type',
        'type_id',
        'pilot',
        'pilot_id',
        'corporation',
        'corporation_id',
        'alliance',
        'alliance_id',
        'solar_system',
        'solar_system_id',
        'constellation',
        'constellation_id',
        'region',
        'region_id',
    ))

    _combo_fields = {
        'division': ('division_id', 'division_name'),
        'type': ('type_id', 'type_name'),
        'pilot': ('pilot_id', 'pilot_name'),
        'corporation': ('corporation_id', 'corporation_name'),
        'alliance': ('alliance_id', 'alliance_name'),
        'solar_system': ('system_id', 'solar_system_name'),
        'constellation': ('constellation_id', 'constellation_name'),
        'region': ('region_id', 'region_name'),
    }

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
        if not self._killmail_fields.isdisjoint(fields) and \
                killmail == killmails is None:
            raise ValueError(u"Either 'killmail' or 'killmails' must be given"
                             u" if a killmail field is being returned.")
        elif killmail is None and killmails is not None:
            killmail = killmails[request['killmail_id']]
        # separate the field names into actual fields on objects, and things to
        # look up in another database/store.
        simple_fields = set(fields)
        active_combo_fields = {}
        for combo_field, replacement_fields in six.iteritems(
                self._combo_fields):
            if combo_field in simple_fields:
                active_combo_fields[combo_field] = replacement_fields
                simple_fields.remove(combo_field)
        # Construct the sparse request dictionary
        sparse_request = {}
        # A helper function to look up values from the appropriate object

        def lookup_field(field_name):
            # the timestamp fields are named the same on their objects
            if field_name.endswith('_timestamp'):
                real_field_name = 'timestamp'
            else:
                real_field_name = field_name
            if field_name in self._request_fields:
                return request[real_field_name]
            elif field_name in self._killmail_fields:
                return killmail[real_field_name]
        # First add the simple (aka non-combo) fields
        for field in simple_fields:
            sparse_request[field] = lookup_field(field)
        # Now add the combo fields
        for combo_field, replacement_fields in six.iteritems(
                active_combo_fields):
            id_field, name_field = replacement_fields
            id_ = lookup_field(id_field)
            # Some names are able to be looked up through this app's database,
            # while most of the others need to be looked up from CCP.
            if id_field in ('division_id', 'pilot_id'):
                # Being a little clever here, lookup the appropriate get_
                # method on this store for the thing we're looking up.
                get_object = getattr(self, 'get_' + combo_field)
                name = get_object(id_)['name']
            else:
                # TODO: CCP Lookup
                pass
            sparse_request[combo_field] = {
                'id': id_,
                'name': name,
            }
        return sparse_request

    def filter_sparse(self, filters, fields):
        full_requests = self.filter_requests(filters)
        format_kwargs = {'fields': fields}
        if not self._killmail_fields.isdisjoint(fields):
            killmail_ids = {r['killmail_id'] for r in full_requests}
            full_killmails = self.get_killmails(killmail_ids=killmail_ids)
            format_kwargs['killmails'] = {km['id']: km for km in 
                                          full_killmails[u'result']}
        for request in full_requests:
            yield self._format_sparse(request, **format_kwargs)

    # Characters

    def get_character(self, character_id):
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
