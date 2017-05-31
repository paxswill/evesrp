import uuid

from graphql_relay.node.node import to_global_id
import pytest


@pytest.mark.parametrize(
    'provider_uuid,key,type_name,entity_id',
    (
        (uuid.UUID('3a80f9c8-f552-472b-9ed4-a479cb8f8521'),
         'authn_user',
         'User',
         9),
        (uuid.UUID('3a80f9c8-f552-472b-9ed4-a479cb8f8521'),
         'authn_group',
         'Group',
         3000),
    ),
    ids=('user', 'group')
)
def test_identity(graphql_client, provider_uuid, key, type_name, entity_id):
    query_placeholders = {}
    field_name = type_name.lower()
    query_placeholders['type_name'] = type_name
    query_placeholders['field_name'] = field_name
    query = '''
    query getIdentity($uuid: ID!, $key: ID!) {
        identity(uuid: $uuid, key: $key) {
            ... on %(type_name)sIdentity {
                providerUuid
                providerKey
                %(field_name)s {
                    id
                }
            }
        }
    }
    ''' % query_placeholders
    result = graphql_client.execute(
        query,
        variable_values={
            'uuid': str(provider_uuid),
            'key': key,
        }
    )
    entity = {'id': to_global_id(type_name, entity_id)}
    assert result == {
        'data': {
            'identity': {
                'providerUuid': str(provider_uuid),
                'providerKey': key,
                field_name: entity,
            }
        }
    }


@pytest.mark.parametrize(
    'group_id,expected_user_ids',
    (
        (None, (2, 7, 9)),
        (to_global_id('Group', 3000), (9, )),
        (to_global_id('Group', 5000), (2, 9)),
    ),
    ids=('all_users', 'one_user', 'multiple_users')
)
def test_users(graphql_client, group_id, expected_user_ids):
    query = '''
    query getUsers($groupID: ID) {
        users(groupId: $groupID) {
            id
        }
    }
    '''
    result = graphql_client.execute(query,
                                    variable_values={'groupID': group_id})
    users = [{'id': to_global_id('User', uid)} for uid in expected_user_ids]
    assert result == {
        'data': {
            'users': users
        }
    }


@pytest.mark.parametrize(
    'user_id,expected_group_ids',
    (
        (None, (3000, 4000, 5000, 6000)),
        (to_global_id('User', 2), (4000, 5000)),
    ),
    ids=('all_groups', 'users_groups')
)
def test_groups(graphql_client, user_id, expected_group_ids):
    query = '''
    query getGroups($userID: ID) {
        groups(userId: $userID) {
            id
        }
    }
    '''
    result = graphql_client.execute(query,
                                    variable_values={'userID': user_id})
    groups = [{'id': to_global_id('Group', gid)} for gid in expected_group_ids]
    assert result == {
        'data': {
            'groups': groups
        }
    }


def test_divisions(graphql_client):
    query = '''
    {
        divisions {
            id
        }
    }
    '''
    result = graphql_client.execute(query)
    expected_divisions = [{'id': to_global_id('Division', did)}
                          for did in (10, 30)]
    assert result == {
        'data': {
            'divisions': expected_divisions
        }
    }


@pytest.mark.parametrize(
    'permission_args,is_present',
    (
        (
            {
                'division_id': to_global_id('Division', 30),
                'entity_id': to_global_id('User', 2),
                'type_': 'pay',
            },
            True
        ),
        (
            # This permission definition is also a good test if the permission
            # field definition is ever changed to also resolve a user's group
            # membership and those permissions.
            {
                'division_id': to_global_id('Division', 30),
                'entity_id': to_global_id('User', 2),
                'type_': 'submit',
            },
            False
        ),
    ),
    ids=('present', 'not_present')
)
def test_permission(graphql_client, permission_args, is_present):
    query = '''
    query checkPermission($divisionID: ID!, $entityID: ID!,
                          $permission: PermissionType!) {
        permission(entityId: $entityID, divisionId: $divisionID,
                   permissionType: $permission) {
            permission
            entity {
                ... on Node {
                    id
                }
            }
            division {
                id
            }
        }
    }
    '''
    result = graphql_client.execute(
        query,
        variable_values={
            'divisionID': permission_args['division_id'],
            'entityID': permission_args['entity_id'],
            'permission': permission_args['type_'],
        }
    )
    assert 'data' in result
    permission = result['data']['permission']
    if is_present:
        assert permission == {
            'division': {'id': permission_args['division_id']},
            'entity': {'id': permission_args['entity_id']},
            'permission': permission_args['type_']
        }
    else:
        assert permission is None


# Copied over from storage/base_test.py
@pytest.mark.parametrize('permission_filter,expected_indexes', (
    (
        {'division_id': [to_global_id('Division', 30)]},
        (0, 2, 4),
    ),
    (
        {'entity_id': [to_global_id('User', 7)]},
        (3, 4),
    ),
    (
        {'type_': ['submit']},
        (1, 2),
    ),
    (
        {
            'division_id': [to_global_id('Division', 30)],
            'type_': ['review'],
        },
        (4,),
    ),
    (
        {
            'division_id': [to_global_id('Division', d) for d in (20, 10)],
        },
        (1, 3),
    ),
    (
        {
            'division_id': [to_global_id('Division', 10)],
            'type_': ['pay'],
        },
        tuple(),
    ),
    (
        {
            'division_id': [to_global_id('Division', 30)],
            'entity_id': [to_global_id('User', 2)],
            'type_': ['submit'],
        },
        tuple(),
    ),
))
def test_permissions(graphql_client, permission_filter, expected_indexes):
    permissions = (
        {
            'division': {'id': to_global_id('Division', 30)},
            'entity': {'id': to_global_id('User', 2)},
            'permission': 'pay',
        },
        {
            'division': {'id': to_global_id('Division', 10)},
            'entity': {'id': to_global_id('User', 9)},
            'permission': 'submit',
        },
        {
            'division': {'id': to_global_id('Division', 30)},
            'entity': {'id': to_global_id('Group', 5000)},
            'permission': 'submit',
        },
        {
            'division': {'id': to_global_id('Division', 10)},
            'entity': {'id': to_global_id('User', 7)},
            'permission': 'review',
        },
        {
            'division': {'id': to_global_id('Division', 30)},
            'entity': {'id': to_global_id('User', 7)},
            'permission': 'review',
        },
    )
    query = '''
    query getPermissions($divisionID: [ID!], $entityID: [ID!],
                         $permissionType: [PermissionType!]) {
        permissions(divisionIds: $divisionID, entityIds: $entityID,
                    permissionTypes: $permissionType) {
            permission
            entity {
                ... on Node {
                    id
                }
            }
            division {
                ... on Node {
                    id
                }
            }
        }
    }
    '''
    result = graphql_client.execute(
        query,
        variable_values={
            'divisionID': permission_filter.get('division_id'),
            'entityID': permission_filter.get('entity_id'),
            'permissionType': permission_filter.get('type_'),
        }
    )

    def to_tuple(p):
        return (
            p['permission'],
            p['entity']['id'],
            p['division']['id'],
        )

    expected_permissions = [permissions[idx] for idx in expected_indexes]
    expected_permission_tuples = {to_tuple(p) for p in expected_permissions}
    assert 'data' in result
    permission_tuples = {to_tuple(p) for p in result['data']['permissions']}
    assert permission_tuples == expected_permission_tuples


@pytest.mark.parametrize(
    'user_id,expect_notes',
    (
        (to_global_id('User', 9), True),
        # User 7 is chosen as it was the submitter for the test note about User
        # 9
        (to_global_id('User', 7), False),
    ),
    ids=('notes', 'no_notes')
)
def test_get_notes(graphql_client, user_id, expect_notes):
    query = '''
    query getNotes($subjectID: ID!) {
        notes(subjectId: $subjectID) {
            id
        }
    }
    '''
    result = graphql_client.execute(query,
                                    variable_values={'subjectID': user_id})
    if expect_notes:
        notes = [
            {
                'id': to_global_id('Note', 1)
            }
        ]
    else:
        notes = []
    assert result == {
        'data': {
            'notes': notes,
        }
    }


@pytest.mark.parametrize('valid_id', (True, False),
                         ids=('valid_id', 'invalid_id'))
def test_get_ccp_character(graphql_client, valid_id):
    if valid_id:
        ccp_id = 570140137
    else:
        ccp_id = 0
    query = '''
    query getCharacter($ccpID: Int!) {
        character(ccpId: $ccpID) {
            id
            name
        }
    }
    '''
    result = graphql_client.execute(query, variable_values={'ccpID': ccp_id})
    if valid_id:
        character = {
            'id': to_global_id('Character', 570140137),
            'name': u'Paxswill',
        }
    else:
        character = None
    assert result == {
        'data': {
            'character': character,
        }
    }



@pytest.mark.parametrize('valid_id', (True, False),
                         ids=('valid_id', 'invalid_id'))
def test_get_ccp_killmail(graphql_client, valid_id):
    if valid_id:
        ccp_id = 52861733
    else:
        ccp_id = 0
    query = '''
    query getKillmail($ccpID: Int!) {
        killmail(ccpId: $ccpID) {
            id
            url
        }
    }
    '''
    result = graphql_client.execute(query, variable_values={'ccpID': ccp_id})
    if valid_id:
        killmail = {
            'id': to_global_id('Killmail', 52861733),
            'url': u'https://zkillboard.com/kill/52861733/',
        }
    else:
        killmail = None
    assert result == {
        'data': {
            'killmail': killmail,
        }
    }


@pytest.mark.parametrize('with_actions', (True, False),
                         ids=('with_actions', 'without_actions'))
def test_get_actions(graphql_client, with_actions):
    if with_actions:
        request_id = to_global_id('Request', 123)
    else:
        request_id = to_global_id('Request', 456)
    query = '''
    query getActions($requestID: ID!) {
        actions(requestId: $requestID) {
            id
        }
    }
    '''
    result = graphql_client.execute(query,
                                     variable_values={'requestID': request_id})
    if with_actions:
        actions = [
            {'id': to_global_id('Action', 10000)},
            {'id': to_global_id('Action', 20000)},
        ]
    else:
        actions = []
    assert result == {
        'data': {
            'actions': actions
        }
    }


@pytest.mark.parametrize('include_void', (None, True, False),
                         ids=('void_none', 'with_void', 'without_void'))
@pytest.mark.parametrize('modifier_type', (None, 'absolute', 'relative'),
                         ids=('type_none', 'absolute', 'relative'))
@pytest.mark.parametrize('request_id',
                         [to_global_id('Request', r) for r in (456, 234)],
                         ids=('Request456', 'Request234'))
def test_get_modifiers(graphql_client, request_id, include_void,
                       modifier_type):
    query = '''
    query getModifiers($requestID: ID!, $void: Boolean, $type: ModifierType) {
        modifiers(requestId: $requestID, includeVoid: $void,
                  modifierType: $type) {
            id
        }
    }
    '''
    variables = {
        'requestID': request_id,
    }
    if include_void is not None:
        variables['void'] = include_void
    if modifier_type is not None:
        variables['type'] = modifier_type
    if request_id == to_global_id('Request', 234):
        modifier_ids = []
    else:
        if modifier_type == 'relative':
            modifier_ids = [300000]
        elif modifier_type == 'absolute':
            if include_void is None or include_void:
                modifier_ids = [200000]
            else:
                modifier_ids = []
        else:
            if include_void is None or include_void:
                modifier_ids = [200000, 300000]
            else:
                modifier_ids = [300000]
    modifiers = [{'id': to_global_id('Modifier', mid)} for mid in modifier_ids]
    result = graphql_client.execute(query, variable_values=variables)
    assert result == {
        'data': {
            'modifiers': modifiers
        }
    }


@pytest.mark.parametrize(
    'killmail_id',
    [to_global_id('Killmail', k) for k in (0, 60713776)],
    ids=('invalid_killmail', 'valid_killmail')
)
@pytest.mark.parametrize(
    'division_id',
    [to_global_id('Division', k) for k in (0, 10, 30)],
    ids=('non_existant_division', 'valid_division', 'invalid_division')
)
def test_get_request(graphql_client, killmail_id, division_id):
    query = '''
    query getRequest($killmailID: ID!, $divisionID: ID!) {
        request(divisionId: $divisionID, killmailId: $killmailID) {
            id
        }
    }
    '''
    result = graphql_client.execute(
        query,
        variable_values={
            'killmailID': killmail_id,
            'divisionID': division_id,
        }
    )
    if killmail_id == to_global_id('Killmail', 60713776) and \
            division_id == to_global_id('Division', 30):
        request = {'id': to_global_id('Request', 789)}
    else:
        request = None
    assert 'data' in result
    assert ('errors' in result) == (request is None)
    assert result['data']['request'] == request
