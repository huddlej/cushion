import couchdb
import pprint
from uuid import uuid4

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response

from forms import DocumentForm


def get_database():
    server = couchdb.Server(settings.COUCHDB_SERVER)
    db = server[settings.CUSHION_DATABASE]
    return db


def index(request):
    db = get_database()
    docs = [doc.doc
            for doc in db.view("_design/%s/_view/by_title" % settings.CUSHION_DATABASE,
                               include_docs=True)]
    return render_to_response("cushion/index.html", {"docs": docs})


def doc(request, doc_id):
    doc_id = doc_id.replace("/", "_")
    db = get_database()
    doc = db[doc_id]
    template_name = doc.pop("template_name", "cushion/default.html")
    return render_to_response(template_name, {"title": doc["title"], "doc": doc})


def edit(request, doc_id=None):
    db = get_database()
    if doc_id is not None:
        doc = db[doc_id]
    else:
        doc = None

    data = request.POST or None
    form = DocumentForm(data, initial=doc)
    if form.is_valid():
        if doc_id:
            doc.update(form.cleaned_data)
        else:
            doc = couchdb.Document(**form.cleaned_data)
            doc.id = uuid4().hex

        db[doc_id] = doc
        return HttpResponseRedirect(reverse("cushion_doc", args=(doc.id,)))
    return render_to_response("cushion/edit.html",
                              {"form": form,
                               "doc": doc})
