from django.conf.urls import include, url # patterns,
from django.contrib import admin
from usermodule import views,views_project

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^register/$', views.register, name='register'),
    url(r'^error/$', views.error_page, name='error_page'),
    url(r'^add-organization/$', views.add_organization, name='add_organization'),
    url(r'^organizations/$', views.organization_index, name='organization_index'),
    url(r'^edit-organization/(?P<org_id>\d+)/$', views.edit_organization, name='edit_organization'),
    # url(r'^organization-mapping/$', views.organization_mapping, name='organization_mapping'),
    url(r'^organization-delete/(?P<org_id>\d+)/$', views.delete_organization, name='organization_delete'),
    # url(r'^organization-delete-mapping/(?P<org_id>\d+)/$', views.delete_organization_mapping, name='delete_organization_mapping'),
    url(r'^edit/(?P<user_id>\d+)/$', views.edit_profile, name='edit_profile'),
    url(r'^delete/(?P<user_id>\d+)/$', views.delete_user, name='delete_user'),
    url(r'^reset-password/(?P<reset_user_id>\d+)/$', views.reset_password, name='reset_password'),
    url(r'^login/$', views.user_login, name='login'),
    url(r'^logout/$', views.user_logout, name='logout'),
    url(r'^change-password/$', views.change_password, name='change_password'),
    url(r'^locked-users/$', views.locked_users, name='locked_users'),
    url(r'^unlock/$', views.unlock, name='unlock'),
    url(r'^organization-access-list/$', views.organization_access_list, name='organization_access_list'),
    # menu item urls 
    url(r'^add-menu/$', views.add_menu, name='add_menu'),
    url(r'^menu-list/$', views.menu_index, name='menu_index'),
    url(r'^edit-menu/(?P<menu_id>\d+)/$', views.edit_menu, name='edit_menu'),
    url(r'^delete-menu/(?P<menu_id>\d+)/$', views.delete_menu, name='delete_menu'),

    # role items urls
    url(r'^add-role/$', views.add_role, name='add_role'),
    url(r'^roles-list/$', views.roles_index, name='roles_index'),
    url(r'^edit-role/(?P<role_id>\d+)/$', views.edit_role, name='edit_role'),
    url(r'^delete-role/(?P<role_id>\d+)/$', views.delete_role, name='delete_role'),
    
    # role menu map urls
    url(r'^add-role-menu-map/$', views.add_role_menu_map, name='add_role_menu_map'),
    url(r'^role-menu-map-list/$', views.role_menu_map_index, name='role_menu_map_index'),
    url(r'^edit-role-menu-map/(?P<item_id>\d+)/$', views.edit_role_menu_map, name='edit_role_menu_map'),
    url(r'^delete-role-menu-map/(?P<item_id>\d+)/$', views.delete_role_menu_map, name='delete_role_menu_map'),
    
    # user role map urls
    url(r'^organization-roles/$', views.organization_roles, name='organization_roles'),
    url(r'^timeconfig-view/$', views.timeconfig_view, name='timeconfig_view'),
    url(r'^time-list/$', views.timeconfig_view, name='time_list'),
    url(r'^edit-time/(?P<org_id>\d+)/$', views.edit_time, name='edit_time'),
    url(r'^user-role-map/(?P<org_id>\d+)/$', views.user_role_map, name='user_role_map'),
    url(r'^adjust-user-role-map/(?P<org_id>\d+)/$', views.adjust_user_role_map, name='adjust_user_role_map'),
    url(r'^insert_sla_time/$', views.insert_sla_time, name='insert_sla_time'),
    url(r'^getBranches/$', views.getBranches, name='getBranches'),
    url(r'^send_token_to_email/$', views.send_token_to_email, name='send_token_to_email'),
    url(r'^token_verification/$', views.token_verification, name='token_verification'),
    url(r'^user_password_reset_mobile/$', views.user_password_reset_mobile, name='user_password_reset_mobile'),

    # url(r'^user-viewable-projects/$', views_project.user_viewable_projects, name='user_viewable_projects'),
    # url(r'^adjust-user-project-map/(?P<id_string>[^/]+)/(?P<form_owner_user>[^/]+)$', views_project.adjust_user_project_map, name='adjust_user_project_map'),
    
    # new project view url
    # url(r'^(?P<username>\w+)/projects-views/(?P<id_string>[^/]+)/$', views_project.custom_project_window, name='custom_project_window'),
    # url(r'^test/$', views_project.test, name='test'),
    
    # url(r"^(?P<username>\w+)/forms/(?P<id_string>[^/]+)/view-data",
    #     'onadata.apps.viewer.views.data_view'),

    #chart related ajax query url
    # url(r'^chartview/$', views_project.chart_view, name='chart_view'),
    # )
    ]