"""
Optional models for raw data being loaded into CouchDB.
"""
import datetime
import hashlib


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
        Coerce a dictionary of values to the types specified for given names.

        Subclass this method to perform custom manipulation of the basic coerced
        values it returns.
        """
        for key, value in values.items():
            if key in self._types:
                try:
                    values[key] = self._types[key](value)
                except ValueError, e:
                    raise BadValueError("Attribute '%s' with value '%s' couldn't be validated: %s"
                                        % (key, value, e.message))

        return values

    def get_id(self):
        """
        Create a document id from the SHA-1 hash of all non-empty unique field
        values for this document if unique fields are defined. Otherwise, return
        None.
        """
        doc_id = None
        if hasattr(self, "_unique_together"):
            doc_id = hashlib.sha1("".join(
                [str(self.get(key))
                 for key in self._unique_together
                 if self.get(key) is not None]
            )).hexdigest()

        return doc_id


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
        "collection": unicode,
        "elevation": int
    }
    _unique_together = (
        "genus",
        "species",
        "latitude",
        "longitude",
        "year",
        "month",
        "day",
        "collector",
        "collection"
    )
    _protected_collections = ("RBC",)

    def coerce(self, values):
        """
        Perform extra manipulation of coerced data such as merging columns.
        """
        values = super(Specimen, self).coerce(values)

        # Convert meters to feet using a decimal conversion value and cast
        # result back to the same type.
        if values.get("elevation_units") == "m.":
            feet_per_meter = 3.280839895013123
            try:
                values["elevation"] = self._types["elevation"](values["elevation"] * feet_per_meter)
                values["elevation_units"] = "ft."
            except TypeError, e:
                raise BadValueError("Elevation can't be converted to meters: %s" % str(e.message))

        # Mark protected documents.
        if values.get("collection") in self._protected_collections:
            values["is_protected"] = True

        # Add a modification timestamp.
        values["date_modified"] = datetime.datetime.now().isoformat()

        return values

registry.register("Specimen", Specimen)


class SimilarSpecies(CoercedModel):
    _types = {
        "species": unicode,
        "similar_species": unicode
    }
registry.register("SimilarSpecies", SimilarSpecies)
