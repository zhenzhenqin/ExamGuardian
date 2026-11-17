from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path

from evidence import api, views

urlpatterns = [
    path("", views.home, name="home"),
    path("admin/", admin.site.urls),
    path("login/", auth.LoginView.as_view(), name="login"),
    path("logout/", auth.LogoutView.as_view(), name="logout"),
    path("demo/", views.demo, name="demo"),
    path("demo/capture.js", views.demo_script, name="demo_script"),
    path("demo/session/", views.demo_session, name="demo_session"),
    path("demo/end/", views.demo_end, name="demo_end"),
    path("health/", api.health),
    path("internal/moodle/start/", api.moodle_start),
    path("internal/moodle/end/", api.moodle_end),
    path("eg-ingest/<uuid:session_id>/status/", api.status, name="evidence_status"),
    path("eg-ingest/<uuid:session_id>/segments/", api.segment, name="evidence_segment"),
    path("eg-ingest/<uuid:session_id>/events/", api.event, name="evidence_event"),
    path("review/", views.review_list, name="review_list"),
    path("review/<uuid:session_id>/", views.review_detail, name="review_detail"),
    path("review/<uuid:session_id>/analysis/", views.queue_analysis, name="queue_analysis"),
    path("review/media/<int:segment_id>/", views.media, name="media"),
]
