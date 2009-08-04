from django.conf.urls.defaults import patterns, url

from views import doc, edit, index


urlpatterns = patterns("",
    url(r"^$", index, name="cushion_index"),
    url(r"^(?P<doc_id>.+)/edit/$", edit, name="cushion_edit"),
    url(r"^(?P<doc_id>.+)/$", doc, name="cushion_doc")
)
