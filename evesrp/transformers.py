class Transformer(object):

    def __init__(self, name, slug):
        self.name = name
        self.slug = slug

    def __repr__(self):
        return u"{x.__class__.__name__}('{x.name}', '{x.slug}')".format(x=self)

    def __str__(self):
        return self.name

    def __call__(self, *args, **kwargs):
        return self.slug.format(*args, **kwargs)

    def __hash__(self):
        return hash(self.name + self.slug) ^ hash(self.__class__)

    def __eq__(self, other):
        return hash(self) == hash(other)
