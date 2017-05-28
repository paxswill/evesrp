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

