"""
Optional models for raw data being loaded into CouchDB.
"""

class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class Registry(object):
    def __init__(self):
        self._registry = {}

    def register(self, name, value):
        if name in self._registry:
            raise AlreadyRegistered("'%s' is already registered." % name)

        self._registry[name] = value

    def unregister(self, name):
        if name not in self._registry:
            raise NotRegistered("'%s' is not registered." % name)

        return self._registry.pop(name)

    def items(self):
        return self._registry.items()

    def get(self, key, default=None):
        return self._registry.get(key, default)
registry = Registry()


class BadValueError(ValueError):
    pass


class CoercedModel(dict):
    def __init__(self, **kwargs):
        super(CoercedModel, self).__init__()
        self.update(self.coerce(kwargs))

    def coerce(self, values):
        """
        Coerces a dictionary of values to the types specified for given names.
        """
        for key, value in values.items():
            if key in self._types:
                try:
                    values[key] = self._types[key](value)
                except ValueError, e:
                    raise BadValueError("Attribute '%s' with value '%s' couldn't be validated: %s"
                                        % (key, value, e.message))

        return values
                    

class Specimen(CoercedModel):
    _types = {
        "genus": unicode,
        "species": unicode,
        "latitude": float,
        "longitude": float,
        "year": unicode,
        "month": unicode,
        "day": unicode,
        "collector": unicode,
        "collection": unicode
    }
registry.register("Specimen", Specimen)

class SimilarSpecies(CoercedModel):
    _types = {
        "species": unicode,
        "similar_species": unicode
    }
registry.register("SimilarSpecies", SimilarSpecies)
