from graphql_relay.node.node import to_global_id, from_global_id
import pytest
from evesrp import new_models as models
from evesrp import search_filter


def test_empty_search(graphql_client):
    query = '''
    {
        requestsConnection {
            totalCount
            totalPayout
            edges {
                node {
                    id
                }
            }
        }
    }
    '''
    result = graphql_client.execute(query)
    connection_data = result['data']['requestsConnection']
    assert connection_data['totalCount'] == 5
    assert connection_data['totalPayout'] == '19050000'
    result_ids = [edge['node']['id'] for edge in connection_data['edges']]
    expected_ids = [
        to_global_id('Request', rid) for rid in
        [123, 456, 234, 345, 789]
    ]
    assert expected_ids == result_ids


@pytest.mark.parametrize('count', range(1, 6))
@pytest.mark.parametrize('first', (True, False), ids=('first', 'last'))
def test_limit_count(graphql_client, first, count):
    if first:
        direction = 'first'
    else:
        direction = 'last'
    query = '''
    query getRequests($count: Int!) {
        requestsConnection(%s: $count) {
            totalCount
            totalPayout
            edges {
                node {
                    id
                }
            }
        }
    }
    ''' % direction
    result = graphql_client.execute(
        query,
        variable_values={
            'count': count,
        }
    )
    connection_data = result['data']['requestsConnection']
    assert connection_data['totalCount'] == 5
    assert connection_data['totalPayout'] == '19050000'
    result_ids = [edge['node']['id'] for edge in connection_data['edges']]
    all_ids = [123, 456, 234, 345, 789]
    if first:
        expected_slice = slice(None, count)
    else:
        expected_slice = slice(-count, None)
    expected_ids = all_ids[expected_slice]
    expected_ids = [to_global_id('Request', rid) for rid in expected_ids]
    assert expected_ids == result_ids


@pytest.fixture(params=(True, False), ids=('should_match', 'should_not_match'))
def should_match(request):
    return request.param


@pytest.fixture(params=(True, False), ids=('equal', 'not_equal'))
def filter_equal(request):
    return request.param


class TestExactFilters(object):

    @pytest.fixture(
        params=(
            'requestId',
            'divisionId',
            'status',
            'killmailId',
            'userId',
            'characterId',
            'corporationId',
            'allianceId',
            'systemId',
            'constellationId',
            'regionId',
            'typeId',
            # TODO: 'url',
        )
    )
    def attribute(self, request):
        """Fixture for varying on which exact filtering attribute to test."""
        return request.param


    @pytest.fixture
    def filter_value(self, attribute, should_match):
        """Fixture for providing which value to filter on.

        This depends on the the attribute being tested, and wether or not this
        value should match an actual request.
        """
        values = {
            'requestId': 123,
            'divisionId': 10,
            'status': 'evaluating',
            'killmailId': 52861733,
            'userId': 2,
            'characterId': 570140137,
            'corporationId': 1018389948,
            'allianceId': 498125261,
            'systemId': 30000848,
            'constellationId': 20000124,
            'regionId': 10000010,
            'typeId': 593,
        }
        if should_match:
            return values[attribute]
        else:
            if attribute == 'status':
                return 'paid'
            else:
                return 0


    @pytest.fixture
    def matching_ids(self, attribute, should_match, filter_equal):
        """Fixture for providing which request IDs should be returned as matching.

        This depends on wether or not the value we're filtering on (from
        :py:func:`filter_value`\) is supposed to match against something in
        storage, and wether or not we're filtering for requests equal, or not equal
        to this value.
        """
        all_ids = [123, 456, 234, 345, 789]
        # If the value doesn't match something in the database, we're either
        # matching all requests, or none depending on wether or not we're filtering
        # for equality or inequality.
        if not should_match:
            if filter_equal:
                return []
            else:
                return all_ids
        matching_ids = {
            'requestId': [123],
            'divisionId': [123, 345],
            'status': [456],
            'killmailId': [123, 456],
            'userId': [789],
            'characterId': [123, 456, 234, 345],
            'corporationId': [123, 456, 234, 345],
            'allianceId': [123, 456, 234, 345],
            'systemId': [123, 456],
            'constellationId': [123, 456],
            'regionId': [123, 456],
            'typeId': [234, 345],
        }
        if filter_equal:
            return matching_ids[attribute]
        else:
            return [i for i in all_ids if i not in matching_ids[attribute]]


    def test_exact_filter(self, graphql_client, matching_ids, attribute,
                          filter_value, filter_equal):
        input_search = {}
        if filter_equal:
            attribute_name = attribute
        else:
            attribute_name = "{}__ne".format(attribute)
        input_search[attribute_name] = [filter_value]
        query = '''
        query getExactFilteredRequests($search: InputRequestSearch!) {
            requestsConnection(search: $search) {
                totalCount
                edges {
                    node {
                        id
                    }
                }
                search {
                    %s
                }
            }
        }
        ''' % attribute_name
        result = graphql_client.execute(
            query,
            variable_values={
                'search': input_search,
            }
        )
        connection_data = result['data']['requestsConnection']
        assert connection_data['totalCount'] == len(matching_ids)
        result_ids = [edge['node']['id'] for edge in connection_data['edges']]
        expected_ids = [to_global_id('Request', rid) for rid in matching_ids]
        assert expected_ids == result_ids
        assert len(connection_data['search'][attribute_name]) != 0


class TestRangeFilters(object):

    @pytest.fixture(
        params=search_filter.PredicateType.range_comparisons,
        ids=lambda p: p.value
    )
    def operator(self, request):
        return request.param
        return search_filter.PredicateType(request.param)

    @pytest.fixture(
        params=(
            'killmailTimestamp',
            'requestTimestamp',
            'basePayout',
            'payout',
        )
    )
    def attribute(self, request):
        return request.param

    @pytest.fixture
    def filter_value(self, attribute):
        values = {
            'killmailTimestamp': '2016-04-04T17:58:45',
            'requestTimestamp': '2017-03-15T13:27:00',
            # It'd be nicer to have a better range of base_payout values in the
            # testing data set, as all but on are 5000000, and that one is
            # 7000000 but I don't want to have to rewrite a significant portion
            # of the already written tests to take that into acount.
            'basePayout': '5000000',
            'payout': '5000000',
        }
        return values[attribute]

    @pytest.fixture
    def matching_ids(self, attribute, operator):
        PredicateType = search_filter.PredicateType
        all_ids = [123, 456, 234, 345, 789]
        # Only specifying the minimum matching IDs, the rest of the predicates
        # can be generated by combining the other matches and all_ids
        matches = {
            'killmailTimestamp': {
                PredicateType.equal: {234, },
                PredicateType.less: {123, 456},
                PredicateType.greater: {789, 345},
            },
            'requestTimestamp': {
                PredicateType.equal: {789, },
                PredicateType.less: {123, 456},
                PredicateType.greater: {234, 345},
            },
            'basePayout': {
                PredicateType.equal: {123, 789, 234, 345},
                PredicateType.less: set(),
                PredicateType.greater: {456, },
            },
            'payout': {
                PredicateType.equal: {234, 345},
                PredicateType.less: {456, 789},
                PredicateType.greater: {123, }
            },
        }
        attribute_matches = matches[attribute]
        if operator in attribute_matches:
            matching_ids = attribute_matches[operator]
        elif operator == PredicateType.not_equal:
            matching_ids = set(all_ids).difference(
                attribute_matches[PredicateType.equal]
            )
        elif operator == PredicateType.less_equal:
            matching_ids = attribute_matches[PredicateType.equal].union(
                attribute_matches[PredicateType.less]
            )
        elif operator == PredicateType.greater_equal:
            matching_ids = attribute_matches[PredicateType.equal].union(
                attribute_matches[PredicateType.greater]
            )
        # Return with a list comprehension so we get the order right
        return [i for i in all_ids if i in matching_ids]

    def test_range_filters(self, graphql_client, attribute, filter_value,
                           matching_ids, operator):
        input_search = {}
        if operator == search_filter.PredicateType.equal:
            attribute_name = attribute
        else:
            attribute_name = "{}__{}".format(attribute, operator.value)
        input_search[attribute_name] = [filter_value]
        query = '''
        query getRangeFilteredRequests($search: InputRequestSearch!) {
            requestsConnection(search: $search) {
                totalCount
                edges {
                    node {
                        id
                    }
                }
                search {
                    %s
                }
            }
        }
        ''' % attribute_name
        result = graphql_client.execute(
            query,
            variable_values={
                'search': input_search,
            }
        )
        connection_data = result['data']['requestsConnection']
        assert connection_data['totalCount'] == len(matching_ids)
        result_ids = [edge['node']['id'] for edge in connection_data['edges']]
        expected_ids = [to_global_id('Request', rid) for rid in matching_ids]
        assert expected_ids == result_ids
        assert len(connection_data['search'][attribute_name]) != 0


class TestSorting(object):

    @pytest.fixture(params=search_filter.SortDirection, ids=lambda d: d.name)
    def direction(self, request):
        return request.param

    @pytest.fixture(
        params=(
            'killmailId',
            'characterName',
            'corporationName',
            'allianceName',
            'systemName',
            'constellationName',
            'regionName',
            'killmailTimestamp',
            'typeName',
            'requestId',
            'divisionName',
            'requestTimestamp',
            'status',
            'basePayout',
            'payout',
        )
    )
    def attribute(self, request):
        return request.param

    @pytest.fixture
    def sorted_ids(self, direction, attribute):
        ascending = {
            # 52861733 (2), 53042210, 53042755, 60713776
            'killmailId': [123, 456, 234, 345, 789],
            # Paxswill (4), marssell kross
            'characterName': [789, 123, 456, 234, 345],
            # Dreddit (4), Imperial Academy
            'corporationName': [123, 456, 234, 345, 789],
            # (null), Test Alliance Please Ignore
            'allianceName': [789, 123, 456, 234, 345],
            # Aldranette, Innia, J000327, M-OEE8 (2)
            'systemName': [345, 234, 789, 123, 456],
            # 1P-VL2 (2), Amevync, H-C00332, Inolari
            'constellationName': [123, 456, 345, 789, 234],
            # Black Rise, H-R00032, Placid, Tribute (2)
            'regionName': [234, 789, 345, 123, 456],
            # killmail ID and timestamp are ordered the same (as far as I know)
            'killmailTimestamp': [123, 456, 234, 345, 789],
            # Heron, Tornado (2), Tristan (2)
            'typeName': [789, 123, 456, 234, 345],
            'requestId': [123, 234, 345, 456, 789],
            # 10, then 30
            # Testing Division (2), YATD... (3)
            'divisionName': [123, 345, 456, 234, 789],
            'requestTimestamp': [123, 456, 789, 345, 234],
            # evaluating, incomplete (2), approved, rejected
            'status': [456, 234, 345, 789, 123],
            # 5000000 (4), 7000000
            'basePayout': [123, 234, 345, 789, 456],
            # 50000, 3500000, 5000000 (2), 5500000
            'payout': [789, 456, 234, 345, 123],
        }
        # Because sort order stability is enforced by adding ascending
        # killmail ID and request ID sorts, we can't just do a straight
        # reverse of the ascending order for those sorts where the
        # order stability is actually affected by those 'hidden' sorts.
        descending = {
            'killmailId': [789, 345, 234, 123, 456],
            'characterName': [123, 456, 234, 345, 789],
            'corporationName': [789, 123, 456, 234, 345],
            'allianceName': [123, 456, 234, 345, 789],
            'systemName': [123, 456, 789, 234, 345],
            'constellationName': [234, 789, 345, 123, 456],
            'regionName': [123, 456, 345, 789, 234],
            'killmailTimestamp': [789, 345, 234, 123, 456],
            'typeName': [234, 345, 123, 456, 789],
            'requestId': [789, 456, 345, 234, 123],
            'divisionName': [456, 234, 789, 123, 345],
            'requestTimestamp': [234, 345, 789, 456, 123],
            'status': [123, 789, 234, 345, 456],
            'basePayout': [456, 123, 234, 345, 789],
            'payout': [123, 234, 345, 456, 789],
        }
        if direction == search_filter.SortDirection.ascending:
            return ascending[attribute]
        else:
            return descending[attribute]

    def test_sorting(self, graphql_client, attribute, direction, sorted_ids):
        input_search = {
            'sorts': [
                {
                    'key': attribute,
                    'direction': direction.name,
                }
            ]
        }
        query = '''
        query getSortedRequests($search: InputRequestSearch!) {
            requestsConnection(search: $search) {
                totalCount
                edges {
                    node {
                        id
                    }
                }
                search {
                    sorts {
                        key
                        direction
                    }
                }
            }
        }
        '''
        result = graphql_client.execute(
            query,
            variable_values={
                'search': input_search,
            }
        )
        connection_data = result['data']['requestsConnection']
        assert connection_data['totalCount'] == len(sorted_ids)
        result_ids = [edge['node']['id'] for edge in connection_data['edges']]
        expected_ids = [to_global_id('Request', rid) for rid in sorted_ids]
        assert expected_ids == result_ids
