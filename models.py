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


class UniqueDocument(object):
    @property
    def get_id(self):
        """
        Create a document id from the SHA-1 hash of all non-empty unique field
        values for this document if unique fields are defined. Otherwise, return
        None.
        """
        if hasattr(self, "_unique_fields"):
            unique_field_strings = []
            for key in self._unique_fields:
                attr = getattr(self, key, None)
                if attr is not None:
                    if isinstance(attr, basestring):
                        # hashlib only works with ascii.
                        attr = attr.encode("utf-8")
                    unique_field_strings.append(str(attr))

            doc_id = hashlib.sha1("".join(unique_field_strings)).hexdigest()
            self._id = doc_id
        else:
            doc_id = getattr(self, "_id", None)

        return doc_id


class BadValueError(ValueError):
    pass


class CoercedDocument(schema.Document):
    """
    Adds a ``coerce`` method to a CouchDB document allowing document values to
    be coerced when possible.
    """
    class Meta:
        app_label = "cushion"

    @classmethod
    def coerce(cls, values):
        """
        Coerce a dictionary of values to the types specified for given names.

        Subclass this method to perform custom manipulation of the basic coerced
        values it returns.
        """
        for key, value in values.items():
            values[key] = value = value.decode("utf-8")
            if key in cls._properties:
                try:
                    values[key] = cls._properties[key].to_python(value)
                except ValueError, e:
                    raise BadValueError("Attribute '%s' with value '%s' couldn't be validated: %s"
                                        % (key, value, e.message))

        return values


class CoercedUniqueDocument(UniqueDocument, CoercedDocument):
    pass


class Label(CoercedDocument):
    @property
    def get_id(self):
        return getattr(self, "_id", None)

    @classmethod
    def coerce(cls, values):
        """
        Perform extra manipulation of coerced data.
        """
        # Define mapping of CSV column names to document attribute names.
        map_columns = {
            "Filename": "_id",
            "Site Name": "city",
            "State/Location": "state"
        }

        values = super(Label, cls).coerce(values)

        # Map column names and strip whitespace from values.
        values = dict([(map_columns.get(key, key.lower()), value.strip())
                       for key, value in values.items()])

        # Add a species.
        values["species"] = values["_id"].split("-")[0]

        # Parse out elevation from its units.
        if "elevation" in values:
            if values["elevation"].endswith("ft"):
                values["elevation"] = values["elevation"][:-2].strip()
                values["elevation_units"] = "ft."
            elif values["elevation"].endswith("m"):
                values["elevation"] = values["elevation"][:-1].strip()
                values["elevation_units"] = "m."

        # Parse out state/province abbreviation.
        if "state" in values and "Canada" in values["state"]:
            # Change "Canada: YT" into "YT".
            values["state"] = values["state"][-2:]

        # Change month from long name to decimal.
        if values.get("month"):
            values["month"] = str(datetime.datetime.strptime(values["month"], "%B").month)

        # Add a modification timestamp.
        values["date_modified"] = datetime.datetime.now().isoformat()

        # Add a type.
        values["type"] = "label"

        return values

registry.register("Label", Label)


class Specimen(CoercedUniqueDocument):
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
    notes = schema.StringProperty()

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

    @classmethod
    def coerce(cls, values):
        """
        Perform extra manipulation of coerced data.
        """
        values = super(Specimen, cls).coerce(values)

        # Convert meters to feet using a decimal conversion value and cast
        # result back to the same type.
        if "elevation" in values and values.get("elevation_units") == "m.":
            feet_per_meter = 3.280839895013123
            try:
                values["elevation"] = cls._properties["elevation"].to_python(values["elevation"] * feet_per_meter)
                values["elevation_units"] = "ft."
            except TypeError, e:
                # TODO: get rid of this special exception.
                raise BadValueError("Elevation can't be converted to meters: %s" % str(e.message))

        # Mark protected documents.
        if values.get("collection") in cls._protected_collections:
            values["is_protected"] = True

        # Add a modification timestamp.
        values["date_modified"] = datetime.datetime.now().isoformat()

        return values

registry.register("Specimen", Specimen)
