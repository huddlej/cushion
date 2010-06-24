from couchdbkit import Server
import couchdb
import pprint
from uuid import uuid4

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response

from forms import DocumentForm, UploadFileForm


def get_document_or_404(db, doc_id):
    try:
        doc = db[doc_id]
    except couchdb.client.ResourceNotFound, e:
        raise Http404("Couldn't find a document with id '%s'." % doc_id)

    return doc


def index(request):
    server = Server(settings.COUCHDB_SERVER)
    databases = [server.get_or_create_db(db).info() for db in server.all_dbs()]
    return render_to_response("cushion/index.html",
                              {"title": "CouchDB",
                               "server": server,
                               "databases": databases})


def database(request, database_name):
    server = Server(settings.COUCHDB_SERVER)
    database = server.get_or_create_db(database_name)
    views_by_design_doc = {}

    # Fetch all documents defining a key range that includes only design
    # documents.
    for design_doc in database.all_docs(startkey="_design", endkey="_design0"):
        doc = database.get(design_doc["id"])
        if "views" in doc:
            views_by_design_doc[design_doc["id"]] = sorted(doc["views"].keys())

    return render_to_response("cushion/database.html",
                              {"title": "Database: %s" % database_name,
                               "server": server,
                               "database_name": database.dbname,
                               "views_by_design_doc": views_by_design_doc})


def view(request, database_name, view="_all_docs"):
    server = Server(settings.COUCHDB_SERVER)
    database = server.get_or_create_db(database_name)
    documents = database.view(view, limit=10)
    return render_to_response("cushion/view.html",
                              {"title": "View: %s" % view,
                               "database_name": database_name,
                               "view": view,
                               "documents": documents})


def document(request, database_name, document_id):
    server = Server(settings.COUCHDB_SERVER)
    database = server.get_or_create_db(database_name)
    document = database.get(document_id)
    return render_to_response("cushion/document.html",
                              {"title": "Document: %s" % document_id,
                               "database_name": database_name,
                               "document": document})


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
