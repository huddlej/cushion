"""
Optional models for raw data being loaded into CouchDB.
"""
from couchdbkit.ext.django import schema
import datetime
import hashlib


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class Registry(dict):
    def register(self, name, value):
        if name in self:
            raise AlreadyRegistered("'%s' is already registered." % name)

        self[name] = value

    def unregister(self, name):
        if name not in self:
            raise NotRegistered("'%s' is not registered." % name)

        return self.pop(name)
registry = Registry()


class BadValueError(ValueError):
    pass


class Specimen(object):
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
    _unique_fields = (
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


class SimilarSpecies(object):
    _types = {
        "species": unicode,
        "similar_species": unicode
    }
registry.register("SimilarSpecies", SimilarSpecies)


class UniqueDocument(object):
    @property
    def get_id(self):
        """
        Create a document id from the SHA-1 hash of all non-empty unique field
        values for this document if unique fields are defined. Otherwise, return
        None.
        """
        if hasattr(self, "_unique_fields"):
            doc_id = hashlib.sha1("".join(
                [str(getattr(self, key))
                 for key in self._unique_fields
                 if getattr(self, key, None) is not None]
            )).hexdigest()
            self._id = doc_id
        else:
            doc_id = getattr(self, "_id", None)

        return doc_id


class CoercedDocument(schema.Document):
    """
    Adds a ``coerce`` method to a CouchDB document allowing document values to
    be coerced when possible.
    """
    @classmethod
    def coerce(cls, values):
        """
        Coerce a dictionary of values to the types specified for given names.

        Subclass this method to perform custom manipulation of the basic coerced
        values it returns.
        """
        for key, value in values.items():
            if key in cls._properties:
                try:
                    values[key] = cls._properties[key].to_python(value)
                except ValueError, e:
                    raise BadValueError("Attribute '%s' with value '%s' couldn't be validated: %s"
                                        % (key, value, e.message))

        return values


class CoercedUniqueDocument(UniqueDocument, CoercedDocument):
    pass


class Similar(schema.Document):
    species = schema.StringProperty()
    similar_species = schema.StringProperty()


class SpecimenModel(CoercedUniqueDocument):
    genus = schema.StringProperty()
    species = schema.StringProperty()
    latitude = schema.FloatProperty()
    longitude = schema.FloatProperty()
    year = schema.StringProperty()
    month = schema.StringProperty()
    day = schema.StringProperty()
    collector = schema.StringProperty()
    collection = schema.StringProperty()
    elevation = schema.IntegerProperty()

    _unique_fields = (
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

registry.register("SpecimenModel", SpecimenModel)
