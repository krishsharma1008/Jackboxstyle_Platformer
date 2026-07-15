from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path

from . import views

urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + [
    path('party/new/', views.party_new, name='party_new'),
    re_path(r'^party/(?P<room_code>[A-Z0-9]{4,8})/host/?$', views.party_host, name='party_host'),
    re_path(r'^party/(?P<room_code>[A-Z0-9]{4,8})/choose-map/?$', views.party_choose_map, name='party_choose_map'),
    re_path(r'^party/(?P<room_code>[A-Z0-9]{4,8})/next-map/?$', views.party_next_map, name='party_next_map'),
    re_path(r'^party/(?P<room_code>[A-Z0-9]{4,8})/results/?$', views.party_save_results, name='party_save_results'),
    re_path(r'^party/(?P<room_code>[A-Z0-9]{4,8})/map/?$', views.party_update_map, name='party_update_map'),
    re_path(r'^party/(?P<room_code>[A-Z0-9]{4,8})/play/?$', views.party_play, name='party_play'),
    re_path(r'^join/(?P<room_code>[A-Z0-9]{4,8})/?$', views.party_join, name='party_join'),
    re_path(r'^party/(?P<room_code>[A-Z0-9]{4,8})/player/(?P<player_id>\d+)/lobby/?$', views.party_player_lobby, name='party_player_lobby'),
    re_path(r'^party/(?P<room_code>[A-Z0-9]{4,8})/player/(?P<player_id>\d+)/profile/?$', views.party_update_player, name='party_update_player'),
    re_path(r'^party/(?P<room_code>[A-Z0-9]{4,8})/player/(?P<player_id>\d+)/submission/(?P<submission_id>\d+)/map/?$', views.party_update_submission_map, name='party_update_submission_map'),
    re_path(r'^party/(?P<room_code>[A-Z0-9]{4,8})/controller/(?P<player_id>\d+)/?$', views.party_controller, name='party_controller'),
    re_path(r'^party/(?P<room_code>[A-Z0-9]{4,8})/controller/(?P<player_id>\d+)/upload/?$', views.party_upload_map, name='party_upload_map'),
    re_path(r'^play/(?P<map_name>\w{1,50})/updatescore/?$', views.update_score, name='update_score'),
    re_path(r'^play/(?P<map_name>\w{1,50})/?$', views.game, name='play_game'),
    path('vote/', views.vote, name='vote'),
    re_path(r'^discover/page/(?P<page>\d+)/?$', views.discover, name='discover'),
    path('discover/', views.discover_home, name='discover_home'),
    path('cv/upload/', views.upload_file, name='upload_compat'),
    path('', views.upload_file, name='upload'),
]
