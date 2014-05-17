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


class ShipTransformer(Transformer):

    def __call__(self, ship_id='', ship_name='', division=''):
        return self.slug.format(name=ship_name, id_=ship_id, division=division)


class PilotTransformer(Transformer):

    def __call__(self, pilot, division=''):
        return self.slug.format(name=pilot.name, id_=pilot.id,
                division=division)
