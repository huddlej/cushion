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

