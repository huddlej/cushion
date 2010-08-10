import csv
import logging

from couchdbkit.ext.django.forms import DocumentForm
from django import forms
from django.utils.datastructures import SortedDict

from models import (
    registry as registered_models,
    Registry,
    Similar
)

log = logging.getLogger(__name__)
form_registry = Registry()


class CreateDatabaseForm(forms.Form):
    name = forms.CharField(help_text="Note that only lowercase characters (a-z), digits (0-9), or any of the characters _, $, (, ), +, -, and / are allowed.")


class ImportDataForm(forms.Form):
    """
    Imports the uploaded file of data into the selected database.
    """
    MODEL_CHOICES = [("", "-- Select a model --")]
    MODEL_CHOICES.extend([(name, name) for name, model in registered_models.items()])
    DELIMITER_CHOICES = (("comma", "comma (,)"),
                         ("tab", "tab (\\t)"),
                         ("space", "space ( )"))
    DELIMITER_STRING_MAP = {"comma": ',',
                            "tab": '\t',
                            "space": ' '}
    file = forms.FileField(label="Select a data file:")
    model = forms.ChoiceField(choices=MODEL_CHOICES, required=False)
    overwrite = forms.BooleanField(label="Overwrite existing records", required=False)
    delimiter = forms.ChoiceField(
        choices=DELIMITER_CHOICES,
        help_text="Optional delimiter for CSV records.",
        required=False,
    )

    def clean_delimiter(self):
        return self.DELIMITER_STRING_MAP[self.cleaned_data["delimiter"]]

    def import_data(self, database, file):
        """
        Parses the given file object as a CSV file and adds the contents to the
        given database using the first row as attribute names for each column.
        """
        reader = csv.reader(file, delimiter=self.cleaned_data["delimiter"])
        data = list(reader)
        errors = []
        if len(data) > 0:
            # Get all non-empty column names using the first row of the data.
            column_names = filter(lambda i: i, data.pop(0))

            column_range = xrange(len(column_names))
            docs = []
            for row in data:
                doc = {}
                # TODO: Replace this for loop with a zip.
                for i in column_range:
                    # Map row value to corresponding column name.
                    if len(row[i]) > 0:
                        doc[column_names[i]] = row[i]

                if self.cleaned_data["model"]:
                    model = registered_models.get(self.cleaned_data["model"])
                    try:
                        doc = model.coerce(doc)
                        doc = model(**doc)
                        # doc["type"] = self.cleaned_data["model"].lower()
                        docs.append(doc)
                    except ValueError, e:
                        errors.append((doc, e.message))
                else:
                    docs.append(doc)

        # Only try to save documents if there weren't any errors.
        if len(errors) == 0:
            # Check for existing documents with the same ids as the imported
            # documents.
            keys = [doc.get_id for doc in docs if doc.get_id]
            existing_docs = database.documents(keys=keys)
            existing_docs = filter(lambda x: "error" not in x, existing_docs)

            if len(existing_docs) > 0:
                if self.cleaned_data["overwrite"]:
                    # If the user approved document overwriting, update each
                    # document of imported data to the current revision of that
                    # document in the database.
                    revisions_by_id = dict([(doc["id"], doc["value"]["rev"])
                                            for doc in existing_docs])
                    for doc in docs:
                        if "_id" in doc and doc["_id"] in revisions_by_id:
                            doc._doc["_rev"] = revisions_by_id[doc["_id"]]
                else:
                    # If the user didn't approve document overwriting, return an
                    # error list for the conflicting documents.
                    docs_by_id = dict([(doc["_id"], doc) for doc in docs])
                    errors = [(docs_by_id[existing_doc["id"]]._doc, "Document already exists.")
                              for existing_doc in existing_docs]

            if len(errors) == 0:
                response = database.bulk_save([doc._doc for doc in docs])

        return errors


class AttachFileForm(forms.Form):
    """
    Attaches a file to a document in the database.
    """
    file = forms.FileField(label="Select a file:")


def get_form_for_document(document):
    """
    Returns a Django form with fields based on the data types of the given
    CouchDB document.
    """
    # Get the class name.
    class_name = str(document.get("type", document["_id"]))
    log.debug("class name: %s" % class_name)

    # Type to form field mappings.
    type_to_field = {
        int: forms.IntegerField,
        float: forms.FloatField,
        str: forms.CharField,
        unicode: forms.CharField,
        bool: forms.BooleanField
    }

    # Convert field types into Field objects.
    fields = SortedDict()
    for field_name, value in sorted(document.items()):
        field_type = type_to_field.get(type(value))

        if field_type is not None:
            # Special fields for CouchDB like _id and _rev get hidden fields.
            if field_name.startswith("_"):
                field = field_type(widget=forms.HiddenInput())
            else:
                field = field_type()

            fields[field_name] = field

    log.debug("fields: %s" % fields)

    # Create the form from the class name and Field objects.
    form = type(class_name, (forms.Form,), fields)
    log.debug("form: %s" % form)

    return form


class SimilarForm(DocumentForm):
    class Meta:
        document = Similar
form_registry.register("SimilarForm", SimilarForm)
