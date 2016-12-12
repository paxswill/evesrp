class IdEquality(object):

    def __hash__(self):
        return hash(self.id_) ^ hash(self.__class__.__name__)

    def __eq__(self, other):
        # Simplistic, not checking types here.
        return self.id_ == other.id_

