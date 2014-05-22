class Transformer(object):

    def __init__(self, name, slug):
        self.name = name
        self.slug = slug

    def __repr__(self):
        return "{x.__class__.__name__}('{x.name}', '{x.slug}')".format(x=self)

    def __str__(self):
        return self.name

    def __call__(self, **kwargs):
        pass

    def __hash__(self):
        return hash(self.name + self.slug) ^ hash(self.__class__)

    def __eq__(self, other):
        return hash(self) == hash(other)


class ShipTransformer(Transformer):

    def __call__(self, ship_id='', ship_name='', division=''):
        return self.slug.format(name=ship_name, id_=ship_id, division=division)


class PilotTransformer(Transformer):

    def __call__(self, pilot, division=''):
        return self.slug.format(name=pilot.name, id_=pilot.id,
                division=division)
