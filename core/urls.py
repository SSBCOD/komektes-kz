from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('set-ui-lang/', views.set_ui_language, name='set_ui_language'),
    path('news/', views.public_news, name='news'),
    path('about/', views.public_about, name='about'),
    path('help/', views.public_help, name='help'),
    path('become-volunteer/', views.public_become_volunteer, name='become_volunteer'),
    path('sign/', views.sign_view, name='sign'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard routes
    path('dashboard/', views.volunteer_dashboard, name='volunteer_dashboard'),
    path('dashboard/tasks/', views.volunteer_tasks, name='volunteer_tasks'),
    path('dashboard/applications/', views.volunteer_applications, name='volunteer_applications'),
    path('dashboard/opportunities/', views.volunteer_opportunities, name='volunteer_opportunities'),
    path('dashboard/opportunities/<int:task_id>/claim/', views.volunteer_claim_task, name='volunteer_claim_task'),
    path('dashboard/tasks/<int:task_id>/complete/', views.volunteer_complete_task, name='volunteer_complete_task'),
    path('dashboard/edit-profile/', views.edit_volunteer_profile, name='edit_volunteer_profile'),
    path('client-dashboard/', views.client_dashboard, name='client_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-clients/', views.admin_clients, name='admin_clients'),
    path('admin-volunteers/', views.admin_volunteers, name='admin_volunteers'),
    path('admin-tasks/', views.admin_tasks, name='admin_tasks'),
    path('admin-analytics/', views.admin_analytics, name='admin_analytics'),
    path('moderator/', views.moderator_login_view, name='moderator_login'),
    path('admin-news/', views.admin_news, name='admin_news'),
    path('admin-contentpages/', views.admin_contentpages, name='admin_contentpages'),
    path('admin-users/', views.admin_users, name='admin_users'),
]
