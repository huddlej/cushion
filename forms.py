import csv
import logging

from django import forms
from django.utils.datastructures import SortedDict

log = logging.getLogger(__name__)


class CreateDatabaseForm(forms.Form):
    name = forms.CharField(help_text="Note that only lowercase characters (a-z), digits (0-9), or any of the characters _, $, (, ), +, -, and / are allowed.")


class DocumentForm(forms.Form):
    title = forms.CharField()
    content = forms.CharField(widget=forms.Textarea(attrs={"cols": 80,
                                                           "rows": 20}))


class UploadFileForm(forms.Form):
    file = forms.FileField(label="Attach a file:")


class ImportDataForm(forms.Form):
    """
    Imports the uploaded file of data into the selected database.
    """
    file = forms.FileField(label="Select a data file:")

    def import_data(self, database, file):
        """
        Parses the given file object as a CSV file and adds the contents to the
        given database using the first row as attribute names for each column.
        """
        reader = csv.reader(file)
        data = list(reader)
        if len(data) > 0:
            # Get all non-empty column names.
            column_names = filter(lambda i: i, data.pop(0))
            column_range = xrange(len(column_names))
            docs = []
            for row in data:
                doc = {}
                for i in column_range:
                    doc[column_names[i]] = row[i]
                docs.append(doc)

        return database.bulk_save(docs)


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

