import graphene

from . import decimal, types


class EdgeNodes(graphene.Union):

    class Meta(object):
        types = (types.Killmail,
                 types.Request)


class Edge(graphene.ObjectType):

    node = EdgeNodes()

    cursor = graphene.ID(required=True)


class PageInfo(graphene.ObjectType):

    end_cursor = graphene.ID(required=True)

    has_next = graphene.Boolean()


class Pager(graphene.ObjectType):

    edges = graphene.List(Edge)

    total_count = graphene.Int()

    total_payout = decimal.Decimal()

    page_info = PageInfo()
