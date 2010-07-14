from couchdbkit import Server
import couchdb
import pprint
from uuid import uuid4

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from forms import DocumentForm, UploadFileForm, get_form_for_document


def index(request):
    server = Server(settings.COUCHDB_SERVER)
    databases = [server.get_or_create_db(db).info() for db in server.all_dbs()]
    return render_to_response("cushion/index.html",
                              {"server": server,
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
            # Convert "_design/mydesigndoc" to "mydesigndoc".
            design_doc_name = design_doc["id"].split("/")[1]
            views_by_design_doc[design_doc_name] = sorted(doc["views"].keys())

    return render_to_response("cushion/database.html",
                              {"title": "Database: %s" % database_name,
                               "server": server,
                               "database_name": database.dbname,
                               "views_by_design_doc": views_by_design_doc})


def view(request, database_name, view_name, design_doc_name=None):
    server = Server(settings.COUCHDB_SERVER)
    database = server.get_or_create_db(database_name)
    documents_per_page = 10

    try:
        page = int(request.GET.get("page", "1"))
    except ValueError:
        page = 1

    request.session["last_couchdb_view"] = {
        "name": view_name,
        "design_doc_name": design_doc_name,
        "page": page
    }

    if design_doc_name:
        view_path = "%s/%s" % (design_doc_name, view_name)
    else:
        view_path = view_name

    start_value = (page - 1) * documents_per_page
    documents_list = database.view(
        view_path,
        limit=documents_per_page,
        skip=start_value
    )

    num_pages = documents_list.total_rows / documents_per_page

    if page > 1:
        previous_page = page - 1
    else:
        previous_page = None

    if page < num_pages:
        next_page = page + 1
    else:
        next_page = None

    documents = list(documents_list)

    return render_to_response("cushion/view.html",
                              {"title": "View: %s" % view_name,
                               "database_name": database_name,
                               "view": view_name,
                               "design_doc_name": design_doc_name,
                               "start_value": start_value,
                               "documents": documents,
                               "num_pages": num_pages,
                               "page": page,
                               "previous_page": previous_page,
                               "next_page": next_page})


def document(request, database_name, document_id, view_name=None):
    server = Server(settings.COUCHDB_SERVER)
    database = server.get_or_create_db(database_name)
    document = database.get(document_id)
    form_class = get_form_for_document(document)
    form = form_class(request.POST or None, initial=document)

    if form.is_valid():
        document.update(form.cleaned_data)
        database.save_doc(document)
        return HttpResponseRedirect(
            reverse(
                "cushion_document",
                args=(database_name, document_id)
            )
        )

    context = {
        "title": "Document: %s" % document_id,
        "database_name": database_name,
        "view_name": view_name,
        "document": document,
        "attachments": document.get("_attachments", {}),
        "form": form
    }

    return render_to_response(
        "cushion/document.html",
        context,
        context_instance=RequestContext(request)
    )


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
