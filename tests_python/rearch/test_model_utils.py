from evesrp.new_models import authorization as authz

def test_id_equality_eq():
    user = authz.User("User 1", 1)
    group = authz.Group("Group 1", 1)
    assert user == group


def test_id_equality_hash():
    user = authz.User("User 1", 1)
    group = authz.Group("Group 1", 1)
    assert hash(user) != hash(group)


