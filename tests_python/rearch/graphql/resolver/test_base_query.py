import collections

from graphql_relay.node.node import to_global_id
import pytest


@pytest.mark.parametrize(
    'relay_node_id,name',
    (
        ('VXNlcjo5', 'User 9'),  # User
        ('R3JvdXA6NTAwMA==', 'Group 5000'),  # Group
        ('RGl2aXNpb246MTA=', 'Testing Division'),  # Division
        ('Q2hhcmFjdGVyOjU3MDE0MDEzNw==', 'Paxswill'),  # Character
    ),
    ids=('user', 'group', 'division', 'character')
)
def test_named_node(graphql_client, relay_node_id, name):
    result = graphql_client.execute('''
    query getNode($nodeId: ID!) {
        node(id: $nodeId) {
            id
            ... on Named {
                name
            }
        }
    }
    ''', variable_values={'nodeId': relay_node_id})
    assert result == {
        'data': {
            'node': {
                'id': relay_node_id,
                'name': name,
            }
        }
    }

# Old style string formatting is being used throughout, as str.format uses
# braces, and I don't want to escape every brace in GraphQL queries. Format
# strings would be a nicer option if/when Python 2 support is ever dropped and
# I only support 3.6 and higher.


@pytest.mark.parametrize(
    'attribute,value',
    (
        ('admin', False),
        ('groups', [to_global_id('Group', g) for g in (5000, 3000)]),
        ('notes', [to_global_id('Note', 1)]),
        ('requests', [to_global_id('Request', km) for km in
                      (456, 345, 234, 123)]),
        ('characters', [to_global_id('Character', c) for c in
                        (2112311608, 570140137)]),
    ),
    ids=('admin', 'groups', 'notes', 'requests', 'characters')
)
def test_user(graphql_client, attribute, value):
    node_id = to_global_id('User', 9)
    if isinstance(value, collections.Sequence):
        expected = set(value)
        query = '''
        query getUser($nodeID: ID!) {
            node(id: $nodeID) {
                id
                ... on User {
                    %s {
                        id
                    }
                }
            }
        }
        ''' % attribute
    else:
        expected = value
        query = '''
        query getUser($nodeID: ID!) {
            node(id: $nodeID) {
                id
                ... on User {
                    %s
                }
            }
        }
        ''' % attribute
    result = graphql_client.execute(query, variable_values={'nodeID': node_id})
    # Do some silliness to compare things without respect to order
    if isinstance(value, collections.Sequence):
        assert 'data' in result
        ids = {v['id'] for v in result['data']['node'][attribute]}
        assert ids == expected
    else:
        assert result == {
            'data': {
                'node': {
                    'id': node_id,
                    attribute: expected,
                }
            }
        }


def test_group(graphql_client):
    node_id = to_global_id('Group', 5000)
    query = '''
    query getGroup($nodeID: ID!) {
        node(id: $nodeID) {
            id
            ... on Group {
                users {
                    id
                }
            }
        }
    }
    '''
    results = graphql_client.execute(query,
                                     variable_values={'nodeID': node_id})
    assert 'data' in results
    expected_user_ids = {to_global_id('User', uid) for uid in (2, 9)}
    result_user_ids = {u['id'] for u in results['data']['node']['users']}
    assert expected_user_ids == result_user_ids
