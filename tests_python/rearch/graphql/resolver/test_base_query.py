import collections
import datetime as dt

from graphql_relay.node.node import to_global_id
import pytest

from evesrp.util import utc


# Old style string formatting is being used throughout, as str.format uses
# braces, and I don't want to escape every brace in GraphQL queries. Format
# strings would be a nicer option if/when Python 2 support is ever dropped
# and I only support 3.6 and higher.


class TestNode(object):
    """Tests both fetching using the node field on Query, but also that the
    types implementing Node also work with (almost) all of their own fields.
    """

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
    def test_named_node(self, graphql_client, relay_node_id, name):
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

    @pytest.mark.parametrize(
        'relay_node_id,permission_tuples',
        (
            (to_global_id('User', 9), (
                # Order is entity_id, permssion string, division_id
                (to_global_id('User', 9), 'submit',
                 to_global_id('Division', 10)),
                (to_global_id('Group', 5000), 'submit',
                 to_global_id('Division', 30)),
            )),
            (to_global_id('Group', 5000), (
                (to_global_id('Group', 5000), 'submit',
                 to_global_id('Division', 30)),
            )),
        ),
        ids=('user', 'group')
    )
    def test_entity(self, graphql_client, relay_node_id, permission_tuples):
        result = graphql_client.execute('''
        query getEntity($nodeID: ID!) {
            node(id: $nodeID) {
                id
                ... on Entity {
                    permissions {
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
            }
        }
        ''', variable_values={'nodeID': relay_node_id})

        def to_tuple(permission_result):
            return (permission_result['entity']['id'],
                    permission_result['permission'],
                    permission_result['division']['id'])

        assert 'data' in result
        assert result['data']['node']['id'] == relay_node_id
        expected_permissions = set(permission_tuples)
        permissions = {to_tuple(p) for p in
                       result['data']['node']['permissions']}
        assert expected_permissions == permissions

    @pytest.mark.parametrize(
        'attribute,value',
        (
            ('admin', False),
            ('groups', [to_global_id('Group', g) for g in (5000, 3000)]),
            ('notes', [to_global_id('Note', 1)]),
            ('requests', [to_global_id('Request', km) for km in
                          (456, 345, 234, 123)]),
            # TODO: Add requests_connection test
            ('characters', [to_global_id('Character', c) for c in
                            (2112311608, 570140137)]),
        ),
        ids=('admin', 'groups', 'notes', 'requests', 'characters')
    )
    def test_user(self, graphql_client, attribute, value):
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
        result = graphql_client.execute(
            query,
            variable_values={'nodeID': node_id}
        )
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

    def test_group(self, graphql_client):
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

    def test_division(self, graphql_client):
        node_id = to_global_id('Division', 30)
        query = '''
        query getDivision($nodeID: ID!) {
            node(id: $nodeID) {
                id
            }
        }
        '''
        results = graphql_client.execute(query,
                                         variable_values={'nodeID': node_id})
        assert results == {
            'data': {
                'node': {
                    'id': node_id
                }
            }
        }

    @pytest.mark.parametrize(
        'attribute,value',
        (
            ('subject', {'id': to_global_id('User', 9)}),
            ('submitter', {'id': to_global_id('User', 7)}),
            ('contents', (u'Not the sharpest tool in the shed. Keeps '
                          u'losing things, deny future requests.')),
            ('timestamp', dt.datetime(2017, 4, 1, tzinfo=utc).isoformat()),
        ),
        ids=('subject', 'submitter', 'contents', 'timestamp')
    )
    def test_note(self, graphql_client, attribute, value):
        node_id = to_global_id('Note', 1)
        if isinstance(value, dict):
            query = '''
            query getNote($nodeID: ID!) {
                node(id: $nodeID) {
                    id
                    ... on Note {
                        %s {
                            id
                        }
                    }
                }
            }
            ''' % attribute
        else:
            query = '''
            query getNote($nodeID: ID!) {
                node(id: $nodeID) {
                    id
                    ... on Note {
                        %s
                    }
                }
            }
            ''' % attribute
        result = graphql_client.execute(
            query,
            variable_values={'nodeID': node_id}
        )
        assert result == {
            'data': {
                'node': {
                    'id': node_id,
                    attribute: value,
                }
            }
        }

    @pytest.mark.parametrize(
        'attribute,value',
        (
            ('user', {'id': to_global_id('User', 9)}),
            ('ccpId', 570140137),
        ),
        ids=('user', 'ccp_id')
    )
    def test_character(self, graphql_client, attribute, value):
        node_id = to_global_id('Character', 570140137)
        if isinstance(value, dict):
            query = '''
            query getCharacter($nodeID: ID!) {
                node(id: $nodeID) {
                    id
                    ... on Character {
                        %s {
                            id
                        }
                    }
                }
            }
            ''' % attribute
        else:
            query = '''
            query getCharacter($nodeID: ID!) {
                node(id: $nodeID) {
                    id
                    ... on Character {
                        %s
                    }
                }
            }
            ''' % attribute
        result = graphql_client.execute(
            query,
            variable_values={'nodeID': node_id}
        )
        assert result == {
            'data': {
                'node': {
                    'id': node_id,
                    attribute: value,
                }
            }
        }

    @pytest.mark.parametrize(
        'attribute,value',
        (
            ('killmailId', 52861733),
            ('user', {'id': to_global_id('User', 9)}),
            ('character', {'id': to_global_id('Character', 570140137)}),
            ('corporation', {'id': 1018389948, 'name': u'Dreddit'}),
            ('alliance', {'id': 498125261,
                          'name': u'Test Alliance Please Ignore'}),
            ('system', {'id': 30000848, 'name': u'M-OEE8'}),
            ('constellation', {'id': 20000124, 'name': u'1P-VL2'}),
            ('region', {'id': 10000010, 'name': u'Tribute'}),
            ('type', {'id': 4310, 'name': u'Tornado'}),
            ('timestamp',
             dt.datetime(2016, 3, 28, 2, 32, 50, tzinfo=utc).isoformat()),
            ('url', 'https://zkillboard.com/kill/52861733/'),
            ('requests', {to_global_id('Request', rid) for rid in (123, 456)}),
        ),
        ids=('killmail_id', 'user', 'character', 'corporation', 'alliance',
             'system', 'constellation', 'region', 'type', 'timestamp', 'url',
             'requests')
    )
    def test_killmail(self, graphql_client, attribute, value):
        node_id = to_global_id('Killmail', 52861733)
        if isinstance(value, (dict, set)):
            if isinstance(value, dict):
                fields = ' '.join(value.keys())
            else:
                fields = 'id'
            query = '''
            query getKillmail($nodeID: ID!) {
                node(id: $nodeID) {
                    id
                    ... on Killmail {
                        %s {
                            %s
                        }
                    }
                }
            }
            ''' % (attribute, fields)
        else:
            query = '''
            query getKillmail($nodeID: ID!) {
                node(id: $nodeID) {
                    id
                    ... on Killmail {
                        %s
                    }
                }
            }
            ''' % attribute
        result = graphql_client.execute(
            query,
            variable_values={'nodeID': node_id}
        )
        if isinstance(value, set):
            assert 'data' in result
            result_ids = {r['id'] for r in result['data']['node'][attribute]}
            assert result_ids == value
        else:
            assert result == {
                'data': {
                    'node': {
                        'id': node_id,
                        attribute: value,
                    }
                }
            }


@pytest.mark.parametrize(
    'group_id,expected_user_ids',
    (
        (None, (9, 2, 7)),
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
    assert 'data' in result
    ids = {user['id'] for user in result['data']['users']}
    expected_relay_ids = {to_global_id('User', uid) for uid in
                          expected_user_ids}
    assert ids == expected_relay_ids

