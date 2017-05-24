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
