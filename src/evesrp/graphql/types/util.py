import graphene


def get_node(cls, id, context, info):
    return cls(id=int(id))


def simple_get_node(klass):
    klass.get_node = classmethod(get_node)
    return klass


class Named(graphene.Interface):

    name = graphene.String(required=True)
