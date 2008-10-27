from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Example:
    # (r'^migrationwizard/', include('migrationwizard.foo.urls')),
    (r'^wizard/$','migrationwizard.wizard.views.signin'),
#    (r'^wizard/migration/$','migrationwizard.wizard.views.migration'),
    (r'^wizard/logout/$','migrationwizard.wizard.views.logout_view'),
    (r'^wizard/queue/$','migrationwizard.wizard.views.addToQueue'),
#    (r'^wizard/login/$','django.contrib.auth.views.login' ),
    (r'(^|/)wizard_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'media', 'show_indexes': True}),
    (r'^wizard/migrate/$','migrationwizard.wizard.views.userWillMigrate'),
    (r'^wizard/fresh/$','migrationwizard.wizard.views.userWillStartFresh'),
    (r'^wizard/progress/$','migrationwizard.wizard.views.inProgressView'),
    (r'^wizard/start/$','migrationwizard.wizard.views.startMigration'),
    (r'^wizard/getupdate/(?P<last_datetime>[^/]+)/$','migrationwizard.wizard.views.getUpdate'),
    (r'^wizard/admin/search/(?P<page_number>[^/]*)/?(?P<search_name>[^/]*)/$','migrationwizard.wizard.views.search_user'),
    (r'^wizard/admin/list/(?P<page_number>[^/]*)/$','migrationwizard.wizard.views.list_all'),
    (r'^wizard/admin/fwd_add/(?P<page_number>[^/]*)/$','migrationwizard.wizard.views.fwd_add'),
    (r'^wizard/admin/done_state/(?P<page_number>[^/]*)/$','migrationwizard.wizard.views.done_state'),
    (r'^wizard/admin/failed_state/(?P<page_number>[^/]*)/?(?P<filter_type>[^/]*)/$','migrationwizard.wizard.views.failed_state'),
    (r'^wizard/admin/notstarted/(?P<page_number>[^/]*)/$','migrationwizard.wizard.views.not_started_state'),
    (r'^wizard/admin/inqueue/(?P<page_number>[^/]*)/$','migrationwizard.wizard.views.in_queue_state'),
    (r'^wizard/admin/inprogress/(?P<page_number>[^/]*)/$','migrationwizard.wizard.views.in_progress_state'),
    (r'^wizard/admin/change_state/$','migrationwizard.wizard.views.change_state'),
    (r'^wizard/admin/user/(?P<user_id>[^/]*)/$','migrationwizard.wizard.views.view_user'),
    (r'^wizard/getqueueplace/$','migrationwizard.wizard.views.getPlaceInQueue'),
    (r'^wizard/feedback/$','migrationwizard.wizard.views.feedback_view'),
    (r'^wizard/faqs/$','migrationwizard.wizard.views.faq_view'),
    (r'^wizard/submit_mobile/$','migrationwizard.wizard.views.submit_mobile'),

    # Uncomment this for admin:
#     (r'^admin/', include('django.contrib.admin.urls')),
)
