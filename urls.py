from django.conf.urls.defaults import patterns, url

from views import index, database, view, document


urlpatterns = patterns("",
    url(r"^$", index, name="cushion_index"),
    url(r"^(?P<database_name>\w+)/_design/(?P<design_doc_name>\w+)/_view/(?P<view_name>.+)/$", view, name="cushion_view"),
    url(r"^(?P<database_name>[-\w]+)/(?P<view_name>_all_docs)/$", view, name="cushion_view"),
    url(r"^(?P<database_name>.+)/(?P<document_id>.+)/$", document, name="cushion_document"),
    url(r"^(?P<database_name>.+)/$", database, name="cushion_database"),
#     url(r"^(?P<doc_id>.+)/edit/$", edit, name="cushion_edit"),
#     url(r"^(?P<doc_id>.+)/$", doc, name="cushion_doc")
)
