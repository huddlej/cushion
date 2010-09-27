from couchdbkit import Server
import math
import urllib

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from forms import (
    AttachFileForm,
    CreateDatabaseForm,
    ImportDataForm,
    form_registry,
    get_form_for_document,
    view_form_registry
)


@login_required
def index(request):
    server = Server(settings.COUCHDB_SERVER)
    databases = [server.get_or_create_db(db).info() for db in server.all_dbs()]

    create_database_form = CreateDatabaseForm(request.POST or None)
    if create_database_form.is_valid():
        database_name = create_database_form.cleaned_data["name"]
        return HttpResponseRedirect(reverse("cushion_database",
                                            args=(database_name,)))

    return render_to_response("cushion/index.html",
                              {"title": "CouchDB",
                               "server": server,
                               "databases": databases,
                               "form": create_database_form},
                              context_instance=RequestContext(request))


def empty_database(server, database_name):
    """
    Deletes all non-design documents from the given database.
    """
    database = server.get_or_create_db(database_name)
    documents_per_delete = 1000
    documents_deleted = 0
    docs = []

    # Get all non-design document ids.
    for doc in database.all_docs(include_docs=True):
        # Ignore design documents.
        if doc["doc"]["_id"].startswith("_design"):
            continue

        # Mark each document as deleted.
        doc["doc"]["_deleted"] = True
        docs.append(doc["doc"])

        # If we've reached the maximum number of docs to store before a save,
        # save and reset the docs list.
        if len(docs) == documents_per_delete:
            database.bulk_save(docs)
            docs = []
            documents_deleted += documents_per_delete

    if len(docs) > 0:
        # Save all documents appended since the last save.
        database.bulk_save(docs)
        documents_deleted += len(docs)

    return documents_deleted


@login_required
def database(request, database_name):
    server = Server(settings.COUCHDB_SERVER)

    if request.GET.get("empty"):
        server.delete_db(database_name)
        server.get_or_create_db(database_name)
        messages.success(request, "Database '%s' has been emptied." % database_name)
        return HttpResponseRedirect(reverse("cushion_database", args=(database_name,)))

    if request.GET.get("delete"):
        server.delete_db(database_name)
        messages.success(request, "Database '%s' has been deleted." % database_name)
        return HttpResponseRedirect(reverse("cushion_index"))

    context = {}
    database = server.get_or_create_db(database_name)

    if request.GET.get("add"):
        context["add_forms"] = form_registry
        if "add_form" in request.GET and request.GET.get("add_form") in form_registry:
            add_form_cls = form_registry.get(request.GET.get("add_form"))
            add_form = add_form_cls(request.POST or None)
            if add_form.is_valid():
                document = add_form.save(commit=False)
                document.set_db(database)
                document.save()
                messages.success(
                    request,
                    "Document '%s' has been saved." % document.get_id
                )

                # Save and add another.
                if "add another" in request.POST["save"].lower():
                    redirect_url = "%s?add=1&add_form=%s" % (
                        reverse(
                            "cushion_database",
                            args=(database_name,)
                        ),
                        request.GET.get("add_form")
                    )
                # Save and view new document.
                else:
                    redirect_url = reverse(
                        "cushion_document",
                        args=(database_name, document.get_id,)
                    )

                return HttpResponseRedirect(redirect_url)

            context["add_form"] = add_form

    if request.GET.get("compact"):
        database.compact()
        messages.success(request, "Database '%s' has been compacted." % database_name)
        return HttpResponseRedirect(reverse("cushion_database", args=(database_name,)))

    form = ImportDataForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        errors = form.import_data(database, request.FILES["file"])
        if len(errors) > 0:
            messages.error(request, "There was a problem with one or more rows in your data. Please correct these rows and try uploading again.")
            context["errors"] = errors
        else:
            messages.success(request, "Your data was imported successfully.")
            return HttpResponseRedirect(reverse("cushion_database", args=(database_name,)))

    # Fetch all documents defining a key range that includes only design
    # documents.
    views_by_design_doc = {}
    for design_doc in database.all_docs(startkey="_design", endkey="_design0"):
        doc = database.get(design_doc["id"])
        if "views" in doc:
            # Convert "_design/mydesigndoc" to "mydesigndoc".
            design_doc_name = design_doc["id"].split("/")[1]
            views_by_design_doc[design_doc_name] = sorted(doc["views"].keys())

    context.update({
        "title": "Database: %s" % database_name,
        "server": server,
        "database_info": database.info(),
        "database_name": database.dbname,
        "views_by_design_doc": views_by_design_doc,
        "form": form
    })

    return render_to_response("cushion/database.html",
                              context,
                              context_instance=RequestContext(request))


@login_required
def view(request, database_name, view_name, design_doc_name=None):
    server = Server(settings.COUCHDB_SERVER)
    database = server.get_or_create_db(database_name)

    get_data = dict([(str(key), value) for key, value in request.GET.items()])
    skip = int(get_data.pop("skip", "0"))
    limit = int(get_data.pop("limit", "10"))
    page = skip / limit + 1

    request.session["last_couchdb_view"] = {
        "name": view_name,
        "design_doc_name": design_doc_name,
        "page": page
    }

    if design_doc_name:
        view_path = "%s/%s" % (design_doc_name, view_name)
    else:
        view_path = view_name

    documents_list = database.view(
        view_path,
        limit=limit,
        skip=skip,
        **get_data
    )

    num_pages = int(math.ceil(documents_list.total_rows / float(limit)))
    last_page = (num_pages - 1) * limit

    if page > 1:
        previous_page = skip - limit
    else:
        previous_page = None

    if page < num_pages:
        next_page = skip + limit
    else:
        next_page = None

    # Find out if a form is registered with for this view and load the form if
    # it exists.
    form_cls = view_form_registry.get(view_path)
    if "key" in get_data and form_cls:
        form = form_cls(request.POST or None)
        form.prepare(database, view_path, get_data)
        if form.is_valid():
            form.process()

            # Redirect to this view with the same query parameters.
            return HttpResponseRedirect(
                "?".join([
                    reverse(
                        "cushion_view",
                        args=(database_name, design_doc_name, view_name)
                    ),
                    request.META["QUERY_STRING"]
                ])
            )
    else:
        form = None

    documents = list(documents_list)
    get_data["limit"] = limit
    query_string = urllib.urlencode(get_data)

    return render_to_response("cushion/view.html",
                              {"title": "View: %s" % view_name,
                               "database_name": database_name,
                               "view": view_name,
                               "design_doc_name": design_doc_name,
                               "documents": documents,
                               "form": form,
                               "num_pages": num_pages,
                               "page": page,
                               "previous_page": previous_page,
                               "next_page": next_page,
                               "last_page": last_page,
                               "limit": limit,
                               "query_string": query_string,
                               "key": get_data.get("key")},
                              context_instance=RequestContext(request))


@login_required
def document(request, database_name, document_id, view_name=None):
    server = Server(settings.COUCHDB_SERVER)
    database = server.get_or_create_db(database_name)
    document = database.get(document_id)

    # Delete this document.
    if request.GET.get("delete"):
        database.delete_doc(document_id)
        messages.success(request, "Document '%s' has been deleted." % document_id)
        return HttpResponseRedirect(reverse("cushion_database", args=(database_name,)))

    # Delete an attachment.
    if request.GET.get("delete_attachment"):
        attachment_name = request.GET.get("delete_attachment")
        attachment_deleted = database.delete_attachment(
            document,
            attachment_name
        )

        if attachment_deleted:
            messages.success(request, "Attachment '%s' has been deleted." % attachment_name)
        else:
            messages.error(request, "Attachment '%s' could not be deleted." % attachment_name)

        return HttpResponseRedirect(
            reverse(
                "cushion_document",
                args=(database_name, document_id)
            )
        )

    # Attach an uploaded file.
    attach_form = AttachFileForm(request.POST or None, request.FILES or None)
    if attach_form.is_valid():
        file = request.FILES["file"]
        database.put_attachment(document, file.read(), file.name)
        messages.success(
            request,
            "Attachment '%s' has been added to document '%s'." % (file.name, document_id)
        )
        return HttpResponseRedirect(
            reverse(
                "cushion_document",
                args=(database_name, document_id)
            )
        )

    # Determine which form to use for this document.
    form_class = get_form_for_document(document)
    form = form_class(request.POST or None, initial=document)

    # Save the contents of a valid document form.
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
        "couchdb_server": settings.COUCHDB_SERVER,
        "database_name": database_name,
        "view_name": view_name,
        "document_id": document_id,
        "document": document,
        "attachments": document.get("_attachments", {}),
        "form": form,
        "attach_form": attach_form
    }

    return render_to_response(
        "cushion/document.html",
        context,
        context_instance=RequestContext(request)
    )
