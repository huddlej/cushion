import couchdb
import pprint
from uuid import uuid4

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response

from forms import DocumentForm, UploadFileForm


def get_database():
    server = couchdb.Server(settings.COUCHDB_SERVER)
    db = server[settings.CUSHION_DATABASE]
    return db


def get_document_or_404(db, doc_id):
    try:
        doc = db[doc_id]
    except couchdb.client.ResourceNotFound, e:
        raise Http404("Couldn't find a document with id '%s'." % doc_id)

    return doc


def index(request):
    db = get_database()
    docs = [doc.doc
            for doc in db.view("_design/%s/_view/by_title" % settings.CUSHION_DATABASE,
                               include_docs=True)]
    return render_to_response("cushion/index.html", {"docs": docs})


def doc(request, doc_id):
    doc_id = doc_id.replace("/", "_")
    db = get_database()
    doc = get_document_or_404(db, doc_id)
    template_name = doc.pop("template_name", "cushion/default.html")
    return render_to_response(template_name, {"title": doc["title"], "doc": doc})


def edit(request, doc_id=None):
    db = get_database()
    if doc_id is not None:
        doc = get_document_or_404(db, doc_id)
    else:
        doc = None

    # Handle any requests to delete an attachment and return to editing the
    # document.
    delete_attachment = request.GET.get("delete_attachment")
    if delete_attachment and doc:
        db.delete_attachment(doc, delete_attachment)
        return HttpResponseRedirect(reverse("cushion_edit", args=(doc.id,)))

    data = request.POST or None
    files = request.FILES or None

    form = DocumentForm(data, initial=doc)
    upload_form = UploadFileForm(data, files)
    if form.is_valid():
        if doc_id:
            doc.update(form.cleaned_data)
        else:
            doc = couchdb.Document(**form.cleaned_data)
            doc.id = uuid4().hex

        db[doc_id] = doc

        # Add a file to the document.
        if upload_form.is_valid():
            file = request.FILES["file"]
            db.put_attachment(doc, file, file.name)

        return HttpResponseRedirect(reverse("cushion_edit", args=(doc.id,)))

    context = {"form": form,
               "upload_form": upload_form,
               "doc": doc}
    if doc:
        context["files"] = doc.get("_attachments")

    return render_to_response("cushion/edit.html", context)
