from graphql_relay.node.node import to_global_id
import pytest


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

