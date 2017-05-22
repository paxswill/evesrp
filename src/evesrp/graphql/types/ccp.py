import graphene


class CcpType(graphene.ObjectType):

    id = graphene.Int(required=True)

    name = graphene.String(required=True)
