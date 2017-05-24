import evesrp.graphql
import graphene.test
import pytest


@pytest.fixture
def graphql_client(memory_store):
    # TODO: Make use of the user argument in the resolver
    resolver = evesrp.graphql.Resolver(memory_store, None)
    test_client = graphene.test.Client(evesrp.graphql.schema,
                                       middleware=[resolver])
    return test_client
