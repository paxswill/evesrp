import datetime as dt
from decimal import Decimal

import pytest
from six.moves import zip

from evesrp import new_models as models
from evesrp import search_filter as sfilter
from evesrp import storage
from evesrp.util import parse_datetime, utc


class CommonStorageTest(object):
    """Shared common tests for Storage implementations

    Subclasses must overrider the store and populated_store fixtures. See
    TestMemoryStore for the data that needs to be present in populated_store.
    """

    # Common tests

    @staticmethod
    def _test_get(getter, good_id, bad_id):
        good_resp = getter(good_id)
        assert good_resp.id_ == good_id
        with pytest.raises(storage.NotFoundError):
            bad_resp = getter(bad_id)

    @staticmethod
    def _test_add(adder, getter, data):
        id_ = data['id']
        data = dict(data)
        data['id_'] = data.pop('id')
        with pytest.raises(storage.NotFoundError):
            getter(id_)
        added = adder(**data)
        fetched = getter(id_)
        assert added == fetched
        assert fetched is not None

    # Authentication Entities

    def test_get_authn_entity(self, populated_store, entity_type,
                              auth_provider_uuid, auth_provider_key,
                              authn_entity):
        getter = getattr(populated_store, 'get_authn_' + entity_type)
        assert getter(auth_provider_uuid, auth_provider_key) == \
            authn_entity
        with pytest.raises(storage.NotFoundError):
            getter(auth_provider_uuid, 'Foo')

    def test_add_authn_entity(self, populated_store, entity_type,
                              auth_provider_uuid, authn_entity_dict):
        adder = getattr(populated_store, 'add_authn_' + entity_type)
        getter = getattr(populated_store, 'get_authn_' + entity_type)
        new_key = 'authn_{}_new'.format(entity_type)
        with pytest.raises(storage.NotFoundError):
            getter(auth_provider_uuid, new_key)
        if entity_type == 'user':
            added = adder(9, auth_provider_uuid, new_key)
        elif entity_type == 'group':
            added = adder(4000, auth_provider_uuid, new_key)
        assert getter(auth_provider_uuid, new_key) == added

    def test_save_authn_entity(self, populated_store, entity_type,
                               auth_provider_key, auth_provider_uuid):
        saver = getattr(populated_store, 'save_authn_' + entity_type)
        getter = getattr(populated_store, 'get_authn_' + entity_type)
        entity1 = getter(auth_provider_uuid, auth_provider_key)
        assert entity1.extra_data == {}
        entity1.test_extra = 'Foo'
        saver(entity1)
        entity2 = getter(auth_provider_uuid, auth_provider_key)
        assert entity2.extra_data == {'test_extra': 'Foo'}

    # Divisions

    def test_get_division(self, populated_store):
        self._test_get(populated_store.get_division, 10, 20)

    def test_get_divisions(self, populated_store):
        resp = populated_store.get_divisions((10, 30))
        divisions = resp
        assert len(divisions) == 2
        # Division name isn't considered for equality, only ID
        assert models.Division(u'', 10) in divisions
        assert models.Division(u'', 30) in divisions
        # No list gets all
        assert len(populated_store.get_divisions()) == 2
        assert len(populated_store.get_divisions((10, 20))) == 1
        assert len(populated_store.get_divisions((10, 40))) == 1
        assert len(populated_store.get_divisions((20, 40))) == 0

    def test_add_division(self, store):
        pre_resp = store.get_divisions()
        assert len(pre_resp) == 0
        add_resp = store.add_division(u'Division Foo')
        new_id = add_resp.id_
        post_resp = store.get_divisions()
        assert len(post_resp) == 1
        get_resp = store.get_division(new_id)
        assert post_resp[0] == get_resp

    def test_save_division(self, populated_store):
        pre_division = populated_store.get_division(10)
        assert pre_division.name == u'Testing Division'
        pre_division.name = u'Even Better Testing Division'
        populated_store.save_division(pre_division)
        post_division = populated_store.get_division(10)
        assert post_division.name == u'Even Better Testing Division'

    # Permissions

    @pytest.mark.parametrize('permission_filter,expected_indexes', (
        (
            {'division_id': 30},
            (0, 2, 4),
        ),
        (
            {'entity_id': 7},
            (3, 4),
        ),
        (
            {'type_': models.PermissionType.submit},
            (1, 2),
        ),
        (
            {
                'division_id': 30,
                'type_': models.PermissionType.review,
            },
            (4,),
        ),
        (
            {
                'division_id': (20, 10),
            },
            (1, 3),
        ),
        (
            {
                'division_id': 10,
                'type_': models.PermissionType.pay,
            },
            tuple(),
        ),
    ))
    def test_get_permissions(self, populated_store, permission_filter,
                             expected_indexes):
        permissions = (
            models.Permission(
                division_id=30,
                entity_id=2,
                type_=models.PermissionType.pay,
            ),
            models.Permission(
                division_id=10,
                entity_id=9,
                type_=models.PermissionType.submit,
            ),
            models.Permission(
                division_id=30,
                entity_id=5000,
                type_=models.PermissionType.submit,
            ),
            models.Permission(
                division_id=10,
                entity_id=7,
                type_=models.PermissionType.review,
            ),
            models.Permission(
                division_id=30,
                entity_id=7,
                type_=models.PermissionType.review,
            ),
        )
        expected_permissions = {permissions[idx] for idx in expected_indexes}
        permissions = populated_store.get_permissions(**permission_filter)
        assert set(permissions) == expected_permissions

    @pytest.mark.parametrize('user_id', (0, 9),
                             ids=('invalid_user', 'valid_user'))
    @pytest.mark.parametrize('division_id', (0, 30),
                             ids=('invalid_division', 'valid_division'))
    def test_add_permission(self, populated_store, user_id, division_id):
        pre_permissions = populated_store.get_permissions(
            type_=models.PermissionType.audit)
        pre_permissions = set(pre_permissions)
        assert len(pre_permissions) == 0
        if user_id == 0 or division_id == 0:
            with pytest.raises(storage.NotFoundError):
                populated_store.add_permission(
                    division_id, user_id, models.PermissionType.audit)
        else:
            added_permission = populated_store.add_permission(
                division_id, user_id, models.PermissionType.audit)
            permissions_post = populated_store.get_permissions(
                type_=models.PermissionType.audit)
            permissions_post = set(permissions_post)
            assert len(permissions_post) == 1
            assert added_permission == permissions_post.pop()

    @pytest.mark.parametrize('remove_args,remove_kwargs', (
        (
            (
                models.Permission(division_id=30,
                                  entity_id=7,
                                  type_=models.PermissionType.review),
            ),
            {},
        ),
        (
            (30, 7, models.PermissionType.review),
            {},
        ),
        (
            tuple(),
            {
                'permission': models.Permission(
                    division_id=30, entity_id=7,
                    type_=models.PermissionType.review),
            },
        ),
        (
            tuple(),
            {
                'division_id': 30,
                'entity_id': 7,
                'type_': models.PermissionType.review,
            },
        ),
        # Not present, but attempt to remove anyway
        (
            tuple(),
            {
                'division_id': 90,
                'entity_id': 7,
                'type_': models.PermissionType.pay,
            },
        ),
    ))
    def test_remove_permission(self, populated_store, remove_args,
                               remove_kwargs):
        populated_store.remove_permission(*remove_args, **remove_kwargs)
        get_resp = set(populated_store.get_permissions())
        if remove_kwargs.get('type_', None) != models.PermissionType.pay:
            assert len(get_resp) == 4
        else:
            assert len(get_resp) == 5

    # Users and Groups

    def test_get_user(self, populated_store):
        self._test_get(populated_store.get_user, 9, 1)

    @pytest.mark.parametrize('group_id,member_ids', (
        (3000, {9, }),
        (4000, {2, }),
        (5000, {2, 9}),
        (6000, set())
    ))
    def test_get_users(self, populated_store, group_id, member_ids):
        get_resp = populated_store.get_users(group_id)
        users = get_resp
        user_ids = {user.id_ for user in users}
        assert member_ids == user_ids

    @pytest.mark.parametrize('is_admin', (True, False))
    def test_add_user(self, store, is_admin):
        add_resp = store.add_user(u'User 6', is_admin)
        user = add_resp
        get_resp = store.get_user(user.id_)
        assert get_resp == user

    def test_get_group(self, populated_store):
        self._test_get(populated_store.get_group, 6000, 0)

    @pytest.mark.parametrize('user_id,group_ids', (
        (2, {4000, 5000}),
        (9, {3000, 5000}),
        (1, set()),
    ))
    def test_get_groups(self, populated_store, user_id, group_ids):
        get_resp = populated_store.get_groups(user_id)
        groups = get_resp
        expected_group_ids = {group.id_ for group in groups}
        assert group_ids == expected_group_ids

    def test_add_group(self, store):
        add_resp = store.add_group(u'Group ????')
        group = add_resp
        get_resp = store.get_group(group.id_)
        assert get_resp == group

    @pytest.mark.parametrize('user_id', (0, 9),
                             ids=('invalid_user', 'valid_user'))
    @pytest.mark.parametrize('group_id', (0, 6000),
                             ids=('invalid_group', 'valid_group'))
    def test_associate(self, populated_store, user_id, group_id):
        if user_id == 0 or group_id == 0:
            with pytest.raises(storage.NotFoundError):
                populated_store.associate_user_group(user_id, group_id)
        else:
            populated_store.associate_user_group(user_id, group_id)
            users = list(populated_store.get_users(group_id))
            assert len(users) == 1

    def test_disassociate(self, populated_store):
        pre_resp = populated_store.get_users(3000)
        assert len(pre_resp) == 1
        populated_store.disassociate_user_group(9, 3000)
        post_resp = populated_store.get_users(3000)
        assert len(post_resp) == 0

    # Killmails

    def test_get_killmail(self, populated_store):
        self._test_get(populated_store.get_killmail, 60713776, 0)

    @pytest.mark.parametrize('requested_ids', (
        (52861733, ),
        (60713776, ),
        (52861733, 60713776),
        (52861733, 0, 60713776),
    ))
    def test_get_killmails(self, populated_store, requested_ids):
        resp = populated_store.get_killmails(requested_ids)
        killmails = resp
        killmail_ids = {km.id_ for km in killmails}
        expected_ids = {id_ for id_ in requested_ids if id_ != 0}
        assert killmail_ids == expected_ids

    @pytest.mark.parametrize('user_id', (0, 9),
                             ids=('invalid_user', 'valid_user'))
    @pytest.mark.parametrize('character_id', (0, None),
                             ids=('invalid_character', 'valid_character'))
    def test_add_killmail(self, populated_store, killmail_data, user_id,
                          character_id):
        full_km_data = dict(killmail_data)
        full_km_data['id_'] = full_km_data.pop('id')
        if character_id is not None:
            full_km_data['character_id'] = character_id
        full_km_data['user_id'] = user_id
        if user_id == 0 or character_id is not None:
            with pytest.raises(storage.NotFoundError):
                populated_store.add_killmail(**full_km_data)
        else:
            killmail = populated_store.add_killmail(**full_km_data)
            assert killmail is not None

    # Requests

    def test_get_request(self, populated_store):
        # Start with a request_id
        req1_resp = populated_store.get_request(request_id=123)
        assert req1_resp.killmail_id == 52861733
        # Now try a killmail and division_id
        req2_resp = populated_store.get_request(division_id=10,
                                                killmail_id=52861733)
        assert req2_resp.killmail_id == 52861733
        # Now check that it fails appropriately
        with pytest.raises(storage.NotFoundError):
            populated_store.get_request(987)

    def test_get_requests(self, populated_store):
        single_resp = populated_store.get_requests(60713776)
        assert len(single_resp) == 1
        multiple_resp = populated_store.get_requests(52861733)
        assert len(multiple_resp) == 2

    def test_add_request(self, populated_store):
        with pytest.raises(storage.NotFoundError):
            pre_request = populated_store.get_request(division_id=10,
                                                      killmail_id=60713776)
        new_request = populated_store.add_request(60713776, 10,
                                                  u'Gimme money.')
        post_request = populated_store.get_request(division_id=10,
                                                   killmail_id=60713776)
        assert new_request == post_request
        assert new_request.killmail_id == 60713776
        assert new_request.division_id == 10

    def test_save_request(self, populated_store):
        req1_resp = populated_store.get_request(456)
        request = req1_resp
        assert request.base_payout == Decimal(7000000)
        request.base_payout = Decimal(5000000)
        populated_store.save_request(request)
        post_resp = populated_store.get_request(456)
        assert post_resp.base_payout == Decimal(5000000)

    # Actions

    def test_get_action(self, populated_store):
        self._test_get(populated_store.get_action, 10000, 0)

    @pytest.mark.parametrize('request_id,action_count', (
        (456, 0),
        (789, 1),
        (123, 2),
    ))
    def test_get_actions(self, populated_store, request_id, action_count):
        resp = populated_store.get_actions(request_id)
        assert len(resp) == action_count

    def test_add_action(self, populated_store):
        add_resp = populated_store.add_action(456, models.ActionType.approved,
                                              7)
        get_resp = populated_store.get_actions(456)
        assert len(get_resp) == 1
        assert add_resp == get_resp[0]

    # Modifier

    def test_get_modifier(self, populated_store):
        self._test_get(populated_store.get_modifier, 100000, 0)

    @pytest.mark.parametrize('request_id,void,type_,expected_ids', (
        (123, None, None, {100000, }),
        (123, True, None, set()),
        (123, True, models.ModifierType.relative, set()),
        (123, True, models.ModifierType.absolute, set()),
        (123, False, None, {100000, }),
        (123, False, models.ModifierType.relative, set()),
        (123, False, models.ModifierType.absolute, {100000, }),

        (456, None, None, {200000, 300000}),
        (456, True, None, {200000, }),
        (456, True, models.ModifierType.relative, set()),
        (456, True, models.ModifierType.absolute, {200000, }),
        (456, False, None, {300000, }),
        (456, False, models.ModifierType.relative, {300000, }),
        (456, False, models.ModifierType.absolute, set()),

        (789, None, None, {400000, 500000}),
        (789, True, None, set()),
        (789, True, models.ModifierType.relative, set()),
        (789, True, models.ModifierType.absolute, set()),
        (789, False, None, {400000, 500000}),
        (789, False, models.ModifierType.relative, {400000, 500000}),
        (789, False, models.ModifierType.absolute, set()),
    ))
    def test_get_modifiers(self, populated_store, request_id, void, type_,
                           expected_ids):
        modifiers_resp = populated_store.get_modifiers(request_id, void=void,
                                                       type_=type_)
        actual_ids = {m.id_ for m in modifiers_resp}
        assert actual_ids == expected_ids

    def test_add_modifier(self, populated_store):
        pre_resp = populated_store.get_modifiers(
            456, void=False, type_=models.ModifierType.absolute)
        assert len(pre_resp) == 0
        add_resp = populated_store.add_modifier(456, 7,
                                                models.ModifierType.absolute,
                                                654321,
                                                u'Testing bonus')
        post_resp = populated_store.get_modifiers(
            456, void=False, type_=models.ModifierType.absolute)
        assert len(post_resp) == 1
        assert add_resp.id_ == post_resp[0].id_

    @pytest.mark.parametrize('modifier_id', (100000, 0, 200000),
                             ids=('valid_id', 'invalid_id', 'already_void'))
    def test_void_modifier(self, populated_store, modifier_id):
        if modifier_id == 0:
            with pytest.raises(storage.NotFoundError):
                populated_store.void_modifier(modifier_id, 7)
        elif modifier_id == 200000:
            with pytest.raises(storage.VoidedModifierError):
                populated_store.void_modifier(modifier_id, 7)
        else:
            populated_store.void_modifier(modifier_id, 7)
            modifier = populated_store.get_modifier(modifier_id)
            assert modifier.is_void

    # Filtering

    @pytest.fixture(params=(
        sfilter.Filter(killmail_timestamp=(parse_datetime('2016-04-04'), )),
        sfilter.Filter(character_id=(570140137, )),
        sfilter.Filter(character_id=(570140137, 2112311608)),
        sfilter.Filter(),
        sfilter.Filter(division_id=(10, )),
        sfilter.Filter(details=(u'please', )),
        sfilter.Filter(killmail_timestamp=(parse_datetime('2016-04-04'), ),
                       type_id=(593, )),
    ))
    def filter_(self, request):
        return request.param

    @pytest.fixture
    def filter_ids(self, filter_):
        if len(filter_) == 0:
            return {123, 456, 789, 234, 345}
        elif len(filter_) == 1:
            if 'character_id' in filter_:
                if len(filter_['character_id']) == 1:
                    return {123, 456, 234, 345}
                elif len(filter_['character_id']) == 2:
                    return {123, 456, 789, 234, 345}
            elif 'details' in filter_:
                return {456, 345}
            elif 'division_id' in filter_:
                return {123, 345}
            elif 'killmail_timestamp' in filter_:
                return {234, 345}
        elif len(filter_) == 2:
            return {234, 345}

    def test_filter(self, populated_store, filter_, filter_ids):
        requests = populated_store.filter_requests(filter_)
        matching_ids = {r['id'] for r in requests}
        assert matching_ids == filter_ids

    @pytest.mark.parametrize('filter_', (sfilter.Filter(), ))
    @pytest.mark.parametrize('fields', (
        {'request_id', },
        {'request_id', 'type_id'},
        {'request_id', 'type_name'},
        {'request_id', 'killmail_timestamp'},
        {'request_id', 'request_timestamp'},
        {'request_id', 'character_id'},
        {'request_id', 'character_name'},
        {'request_id', 'status'}
    ))
    def test_sparse_filter(self, populated_store, filter_, fields):
        sparse = populated_store.filter_sparse(filter_, fields)
        request_ids = [123, 456, 789, 234, 345]
        other_data = {
            'type_id': [4310, 4310, 605, 593, 593],
            'type_name': [u'Tornado', u'Tornado', u'Heron', u'Tristan',
                          u'Tristan'],
            'killmail_timestamp': [
                dt.datetime(2016, 3, 28, 2, 32, 50, tzinfo=utc),
                dt.datetime(2016, 3, 28, 2, 32, 50, tzinfo=utc),
                dt.datetime(2017, 3, 12, 0, 33, 10, tzinfo=utc),
                dt.datetime(2016, 4, 4, 17, 58, 45, tzinfo=utc),
                dt.datetime(2016, 4, 4, 18, 19, 27, tzinfo=utc),
            ],
            'request_timestamp': [
                dt.datetime(2016, 3, 30, 9, 30, tzinfo=utc),
                dt.datetime(2017, 3, 10, 10, 11, 12, tzinfo=utc),
                dt.datetime(2017, 3, 15, 13, 27, tzinfo=utc),
                dt.datetime(2017, 4, 10, tzinfo=utc),
                dt.datetime(2017, 4, 9, tzinfo=utc),
            ],
            'character_id': [570140137, 570140137, 2112311608, 570140137,
                             570140137],
            'character_name': [u'Paxswill', u'Paxswill', u'marssell kross',
                               u'Paxswill', u'Paxswill'],
            'status': [
                models.ActionType.rejected,
                models.ActionType.evaluating,
                models.ActionType.approved,
                models.ActionType.incomplete,
                models.ActionType.incomplete,
            ],
        }
        for field in other_data.keys():
            if field in fields:
                extra_values = other_data[field]
                packed = zip(request_ids, extra_values)
                expected = [{'request_id': r, field: e} for r, e in packed]
                break
        else:
            # first case, only request_id
            expected = [{'request_id': r} for r in request_ids]
        assert sparse == expected

    # Characters

    def test_get_character(self, populated_store):
        self._test_get(populated_store.get_character, 570140137, 0)

    def test_add_character(self, populated_store):
        with pytest.raises(storage.NotFoundError):
            populated_store.get_character(95465499)
        new_character = populated_store.add_character(7, 95465499,
                                                      'CCP Bartender')
        character = populated_store.get_character(95465499)
        assert character == new_character
        assert character.id_ == 95465499

    def test_save_character(self, populated_store):
        # Act like 'Paxswill' is offensive
        pre_resp = populated_store.get_character(570140137)
        character = pre_resp
        character.name = u'Gallente Citizen 570140137'
        populated_store.save_character(character)
        post_resp = populated_store.get_character(570140137)
        assert post_resp.name == u'Gallente Citizen 570140137'

    # Notes

    @pytest.mark.parametrize('note_present', (True, False),
                             ids=('note_present', 'note_not_present'))
    def test_get_notes(self, populated_store, note_present):
        if note_present:
            subject_id = 9
            num_notes = 1
        else:
            subject_id = 7
            num_notes = 0
        resp = populated_store.get_notes(subject_id)
        assert len(resp) == num_notes

    def test_add_note(self, populated_store):
        pre_resp = populated_store.get_notes(7)
        assert len(pre_resp) == 0
        add_resp = populated_store.add_note(7, 7,
                                            u"Isn't the number seven awesome?")
        post_resp = populated_store.get_notes(7)
        assert len(post_resp) == 1
        assert add_resp == post_resp[0]
