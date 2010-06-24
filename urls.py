from django.conf.urls.defaults import patterns, url

from views import index, database, view


urlpatterns = patterns("",
    url(r"^$", index, name="cushion_index"),
    url(r"^(?P<database_name>.+)/(?P<view>.+)/$", view, name="cushion_view"),
    url(r"^(?P<database_name>.+)/$", database, name="cushion_database"),
#     url(r"^(?P<doc_id>.+)/edit/$", edit, name="cushion_edit"),
#     url(r"^(?P<doc_id>.+)/$", doc, name="cushion_doc")
)
