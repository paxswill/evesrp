from decimal import Decimal

import pytest

from evesrp import new_models as models


class CommonStorageTest(object):
    """Shared common tests for Storage implementations

    Subclasses must overrider the store and populated_store fixtures. See
    TestMemoryStore for the data that needs to be present in populated_store.
    """

    # Common tests

    @staticmethod
    def _test_get(getter, good_id, bad_id):
        good_resp = getter(good_id)
        assert good_resp[u'result'].id_ == good_id
        bad_resp = getter(bad_id)
        assert bad_resp[u'result'] is None
        assert 'not found' in bad_resp[u'errors'][0]

    @staticmethod
    def _test_add(adder, getter, data):
        id_ = data['id']
        data = dict(data)
        data['id_'] = data.pop('id')
        pre_resp = getter(id_)
        assert pre_resp[u'result'] is None
        add_resp = adder(**data)
        post_resp = getter(id_)
        assert post_resp[u'result'] == add_resp[u'result']
        assert post_resp[u'result'] is not None

    # Authentication Entities

    def test_get_authn_entity(self, populated_store, entity_type,
                              auth_provider_uuid, auth_provider_key,
                              authn_entity):
        getter = getattr(populated_store, 'get_authn_' + entity_type)
        assert getter(auth_provider_uuid, auth_provider_key)[u'result'] == \
            authn_entity
        assert getter(auth_provider_uuid, 'Foo')[u'result'] is None

    def test_add_authn_entity(self, store, entity_type, authn_entity_dict):
        adder = getattr(store, 'add_authn_' + entity_type)
        getter = getattr(store, 'get_authn_' + entity_type)
        resp = getter(authn_entity_dict[u'provider_uuid'],
                      authn_entity_dict[u'provider_key'])
        assert resp['result'] is None
        assert u'not found' in resp['errors']
        added = adder(**authn_entity_dict)[u'result']
        assert getter(authn_entity_dict[u'provider_uuid'],
                      authn_entity_dict[u'provider_key'])[u'result'] == added

    def test_save_authn_entity(self, populated_store, entity_type,
                               auth_provider_key, auth_provider_uuid):
        saver = getattr(populated_store, 'save_authn_' + entity_type)
        getter = getattr(populated_store, 'get_authn_' + entity_type)
        entity1 = getter(auth_provider_uuid, auth_provider_key)[u'result']
        assert entity1.extra_data == {}
        entity1.test_extra = 'Foo'
        saver(entity1)
        entity2 = getter(auth_provider_uuid, auth_provider_key)[u'result']
        assert entity2.extra_data == {'test_extra': 'Foo'}

    # Divisions

    def test_get_division(self, populated_store):
        self._test_get(populated_store.get_division, 10, 20)

    def test_get_divisions(self, populated_store):
        resp = populated_store.get_divisions((10, 30))
        divisions = resp[u'result']
        assert len(divisions) == 2
        # Division name isn't considered for equality, only ID
        assert models.Division(u'', 10) in divisions
        assert models.Division(u'', 30) in divisions
        # No list gets all
        assert len(populated_store.get_divisions()[u'result']) == 2
        assert len(populated_store.get_divisions((10, 20))[u'result']) == 1
        assert len(populated_store.get_divisions((10, 40))[u'result']) == 1
        assert len(populated_store.get_divisions((20, 40))[u'result']) == 0

    def test_add_division(self, store):
        pre_resp = store.get_divisions()
        assert len(pre_resp[u'result']) == 0
        add_resp = store.add_division(u'Division Foo')
        new_id = add_resp[u'result'].id_
        post_resp = store.get_divisions()
        assert len(post_resp[u'result']) == 1
        get_resp = store.get_division(new_id)
        assert post_resp[u'result'][0] == get_resp[u'result']

    def test_save_division(self, populated_store):
        pre_resp = populated_store.get_division(10)
        division = pre_resp[u'result']
        assert division.name == u'Testing Division'
        division.name = u'Even Better Testing Division'
        populated_store.save_division(division)
        post_resp = populated_store.get_division(10)
        assert post_resp[u'result'].name == u'Even Better Testing Division'

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
        resp = populated_store.get_permissions(**permission_filter)
        assert set(resp[u'result']) == expected_permissions

    @pytest.mark.parametrize('user_id', (0, 9),
                             ids=('invalid_user', 'valid_user'))
    @pytest.mark.parametrize('division_id', (0, 30),
                             ids=('invalid_division', 'valid_division'))
    def test_add_permission(self, populated_store, user_id, division_id):
        pre_resp = populated_store.get_permissions(
            type_=models.PermissionType.audit)
        assert len(pre_resp[u'result']) == 0
        add_resp = populated_store.add_permission(
            division_id, user_id, models.PermissionType.audit)
        if user_id == 0:
            assert add_resp[u'result'] is None
            assert u'Entity ID #0 not found' in add_resp[u'errors']
        if division_id == 0:
            assert add_resp[u'result'] is None
            assert u'Division ID #0 not found' in add_resp[u'errors']
        if user_id != 0 and division_id != 0:
            post_resp = populated_store.get_permissions(
                type_=models.PermissionType.audit)
            assert len(post_resp[u'result']) == 1
            assert add_resp[u'result'] == post_resp[u'result'].pop()

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
        get_resp = populated_store.get_permissions()
        if remove_kwargs.get('type_', None) != models.PermissionType.pay:
            assert len(get_resp[u'result']) == 4
        else:
            assert len(get_resp[u'result']) == 5

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
        users = get_resp[u'result']
        user_ids = {user.id_ for user in users}
        assert member_ids == user_ids

    @pytest.mark.parametrize('is_admin', (True, False))
    def test_add_user(self, store, is_admin):
        add_resp = store.add_user(u'User 6', is_admin)
        user = add_resp[u'result']
        get_resp = store.get_user(user.id_)
        assert get_resp[u'result'] == user

    def test_get_group(self, populated_store):
        self._test_get(populated_store.get_group, 6000, 0)

    @pytest.mark.parametrize('user_id,group_ids', (
        (2, {4000, 5000}),
        (9, {3000, 5000}),
        (1, set()),
    ))
    def test_get_groups(self, populated_store, user_id, group_ids):
        get_resp = populated_store.get_groups(user_id)
        groups = get_resp[u'result']
        expected_group_ids = {group.id_ for group in groups}
        assert group_ids == expected_group_ids

    def test_add_group(self, store):
        add_resp = store.add_group(u'Group ????')
        group = add_resp[u'result']
        get_resp = store.get_group(group.id_)
        assert get_resp[u'result'] == group

    @pytest.mark.parametrize('user_id', (0, 9),
                             ids=('invalid_user', 'valid_user'))
    @pytest.mark.parametrize('group_id', (0, 6000),
                             ids=('invalid_group', 'valid_group'))
    def test_associate(self, populated_store, user_id, group_id):
        resp = populated_store.associate_user_group(user_id, group_id)
        if user_id == 0:
            assert u"User ID #0 not found" in resp[u'errors']
        if group_id == 0:
            assert u"Group ID #0 not found" in resp[u'errors']
        if group_id != 0 and user_id != 0:
            post_resp = populated_store.get_users(group_id)
            assert len(post_resp[u'result']) == 1

    def test_disassociate(self, populated_store):
        pre_resp = populated_store.get_users(3000)
        assert len(pre_resp[u'result']) == 1
        populated_store.disassociate_user_group(9, 3000)
        post_resp = populated_store.get_users(3000)
        assert len(post_resp[u'result']) == 0

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
        killmails = resp[u'result']
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
        add_resp = populated_store.add_killmail(**full_km_data)
        if user_id == 0:
            assert add_resp[u'result'] is None
            assert u"User ID #0 not found" in add_resp[u'errors']
        if character_id is not None:
            assert add_resp[u'result'] is None
            assert u"Character ID #0 not found" in add_resp[u'errors']
        if user_id != 0 and character_id is None:
            assert add_resp[u'result'] is not None

    # Requests

    def test_get_request(self, populated_store):
        # Start with a request_id
        req1_resp = populated_store.get_request(request_id=123)
        assert req1_resp[u'result'].killmail_id == 52861733
        # Now try a killmail and division_id
        req2_resp = populated_store.get_request(division_id=10,
                                                killmail_id=52861733)
        assert req2_resp[u'result'].killmail_id == 52861733
        neg_resp = populated_store.get_request(234)
        assert neg_resp[u'result'] is None
        assert 'not found' in neg_resp[u'errors']

    def test_get_requests(self, populated_store):
        # TODO
        pass

    def test_add_request(self, populated_store):
        pre_resp = populated_store.get_request(division_id=10,
                                               killmail_id=60713776)
        assert pre_resp[u'result'] is None
        add_resp = populated_store.add_request(60713776, 10, u'Gimme money.')
        post_resp = populated_store.get_request(division_id=10,
                                                killmail_id=60713776)
        assert add_resp[u'result'] == post_resp[u'result']
        request = post_resp[u'result']
        assert request.killmail_id == 60713776
        assert request.division_id == 10

    def test_save_request(self, populated_store):
        req1_resp = populated_store.get_request(456)
        request = req1_resp[u'result']
        assert request.base_payout == Decimal(7000000)
        request.base_payout = Decimal(5000000)
        populated_store.save_request(request)
        post_resp = populated_store.get_request(456)
        assert post_resp[u'result'].base_payout == Decimal(5000000)

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
        assert len(resp[u'result']) == action_count

    def test_add_action(self, populated_store):
        add_resp = populated_store.add_action(456, models.ActionType.approved,
                                              7)
        get_resp = populated_store.get_actions(456)
        assert len(get_resp[u'result']) == 1
        assert add_resp[u'result'] == get_resp[u'result'][0]

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
        actual_ids = {m.id_ for m in modifiers_resp[u'result']}
        assert actual_ids == expected_ids

    def test_add_modifier(self, populated_store):
        pre_resp = populated_store.get_modifiers(
            456, void=False, type_=models.ModifierType.absolute)
        assert len(pre_resp[u'result']) == 0
        add_resp = populated_store.add_modifier(456, 7,
                                                models.ModifierType.absolute,
                                                654321,
                                                u'Testing bonus')
        post_resp = populated_store.get_modifiers(
            456, void=False, type_=models.ModifierType.absolute)
        assert len(post_resp[u'result']) == 1
        assert add_resp[u'result'].id_ == post_resp[u'result'][0].id_

    @pytest.mark.parametrize('modifier_id', (100000, 0, 200000),
                             ids=('valid_id', 'invalid_id', 'already_void'))
    def test_void_modifier(self, populated_store, modifier_id):
        resp = populated_store.void_modifier(modifier_id, 7)
        if modifier_id == 0:
            assert u'not found' in resp[u'errors'][0]
        elif modifier_id == 200000:
            assert u'already void' in resp[u'errors'][0]
        else:
            post_resp = populated_store.get_modifier(modifier_id)
            assert post_resp[u'result'].is_void

    # Filtering

    # TODO

    # Characters

    def test_get_character(self, populated_store):
        self._test_get(populated_store.get_character, 570140137, 0)

    def test_add_character(self, populated_store):
        pre_resp = populated_store.get_character(95465499)
        assert pre_resp[u'result'] is None
        add_resp = populated_store.add_character(7, 95465499, 'CCP Bartender')
        post_resp = populated_store.get_character(95465499)
        assert add_resp[u'result'] == post_resp[u'result']
        assert post_resp[u'result'].id_ == 95465499

    def test_save_character(self, populated_store):
        # Act like 'Paxswill' is offensive
        pre_resp = populated_store.get_character(570140137)
        character = pre_resp[u'result']
        character.name = u'Gallente Citizen 570140137'
        populated_store.save_character(character)
        post_resp = populated_store.get_character(570140137)
        assert post_resp[u'result'].name == u'Gallente Citizen 570140137'

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
        assert len(resp[u'result']) == num_notes

    def test_add_note(self, populated_store):
        pre_resp = populated_store.get_notes(7)
        assert len(pre_resp['result']) == 0
        add_resp = populated_store.add_note(7, 7,
                                            u"Isn't the number seven awesome?")
        post_resp = populated_store.get_notes(7)
        assert len(post_resp['result']) == 1
        assert add_resp[u'result'] == post_resp[u'result'][0]
