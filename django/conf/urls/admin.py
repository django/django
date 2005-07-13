from django.conf.urls.defaults import *
from django.conf.settings import INSTALLED_APPS

urlpatterns = (
    ('^/?$', 'django.views.admin.main.index'),
    ('^logout/$', 'django.views.admin.main.logout'),
    ('^password_change/$', 'django.views.registration.passwords.password_change'),
    ('^password_change/done/$', 'django.views.registration.passwords.password_change_done'),
    ('^template_validator/$', 'django.views.admin.template.template_validator'),

    # Documentation
    ('^doc/$', 'django.views.admin.doc.doc_index'),
    ('^doc/bookmarklets/$', 'django.views.admin.doc.bookmarklets'),
    ('^doc/tags/$', 'django.views.admin.doc.template_tag_index'),
    ('^doc/filters/$', 'django.views.admin.doc.template_filter_index'),
    ('^doc/views/$', 'django.views.admin.doc.view_index'),
    ('^doc/views/jump/$', 'django.views.admin.doc.jump_to_view'),
    ('^doc/views/(?P<view>[^/]+)/$', 'django.views.admin.doc.view_detail'),
    ('^doc/models/$', 'django.views.admin.doc.model_index'),
    ('^doc/models/(?P<model>[^/]+)/$', 'django.views.admin.doc.model_detail'),
)

if 'ellington.events' in INSTALLED_APPS:
    urlpatterns += (
        ("^events/usersubmittedevents/(?P<object_id>\d+)/$", 'ellington.events.views.admin.user_submitted_event_change_stage'),
        ("^events/usersubmittedevents/(?P<object_id>\d+)/delete/$", 'ellington.events.views.admin.user_submitted_event_delete_stage'),
    )

if 'ellington.news' in INSTALLED_APPS:
    urlpatterns += (
        ("^stories/preview/$", 'ellington.news.views.admin.story_preview'),
        ("^stories/js/inlinecontrols/$", 'ellington.news.views.admin.inlinecontrols_js'),
        ("^stories/js/inlinecontrols/(?P<label>[-\w]+)/$", 'ellington.news.views.admin.inlinecontrols_js_specific'),
    )

if 'ellington.alerts' in INSTALLED_APPS:
    urlpatterns += (
        ("^alerts/send/$", 'ellington.alerts.views.admin.send_alert_form'),
        ("^alerts/send/do/$", 'ellington.alerts.views.admin.send_alert_action'),
    )

if 'ellington.media' in INSTALLED_APPS:
    urlpatterns += (
        ('^media/photos/caption/(?P<photo_id>\d+)/$', 'ellington.media.views.admin.get_exif_caption'),
    )

urlpatterns += (
    # Metasystem admin pages
    ('^(?P<app_label>[^/]+)/(?P<module_name>[^/]+)/$', 'django.views.admin.main.change_list'),
    ('^(?P<app_label>[^/]+)/(?P<module_name>[^/]+)/add/$', 'django.views.admin.main.add_stage'),
    ('^(?P<app_label>[^/]+)/(?P<module_name>[^/]+)/(?P<object_id>\d+)/$', 'django.views.admin.main.change_stage'),
    ('^(?P<app_label>[^/]+)/(?P<module_name>[^/]+)/(?P<object_id>\d+)/delete/$', 'django.views.admin.main.delete_stage'),
    ('^(?P<app_label>[^/]+)/(?P<module_name>[^/]+)/(?P<object_id>\d+)/history/$', 'django.views.admin.main.history'),
    ('^(?P<app_label>[^/]+)/(?P<module_name>[^/]+)/jsvalidation/$', 'django.views.admin.jsvalidation.jsvalidation'),
)
urlpatterns = patterns('', *urlpatterns)
