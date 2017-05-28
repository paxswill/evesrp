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
        assert permission is not None
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

