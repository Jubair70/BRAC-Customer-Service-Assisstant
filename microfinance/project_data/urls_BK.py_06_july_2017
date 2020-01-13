from django.conf.urls import include, url
from project_data import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^new-complain/$', views.new_complain, name='new_complain'),
    url(r'^get-last-id/$', views.getLastId, name='get-last-id'),
    url(r'^reload-complains/$', views.reloadComplains, name='reload-complains'),
    url(r'^all-complain/$', views.all_complain, name='all_complain'),
    url(r'^add-complain/$', views.add_complain, name='add_complain'),
    url(r'^add-complain-mobile/$', views.add_complain_mobile, name='add_complain_mobile'),
    url(r'^complain-filter-list/$', views.complain_filter_list, name='complain_filter_list'),
    url(r'^unlock-complain/(?P<complain_id>\d+)/(?P<user_id>\d+)/$', views.complain_unlock, name='complain_unlock'),
    url(r'^unlock-complain-home/(?P<complain_id>\d+)/(?P<user_id>\d+)/$', views.complain_unlock_home, name='complain_unlock_home'),
    url(r'^logout-view/$',views.logout_view, name='logout_view'),


    url(r'^authentication-mobile/$', views.mobile_registration, name='mobile_registration'),
    url(r'^activate-mobile-user/$', views.mobile_user_activate, name='mobile_user_activate'),
    url(r'^mobile-change-password/$', views.mobile_change_password, name='mobile_change_password'),
    url(r'^mobile-reset-token/$', views.mobile_reset_token, name='mobile_reset_token'),
    url(r'^mobile-reset-password/$', views.mobile_reset_password, name='mobile_reset_password'),

    url(r'^login-mobile/$', views.user_login, name='user_login'),
    url(r'^view-complain/(?P<complain_id>\d+)/$', views.edit_complain, name='edit_complain'),

    url(r'^branch-list/$', views.branch_list, name='branch_list'),
    url(r'^add-branch/$', views.add_branch, name='add_branch'),
    url(r'^mobile-branch-verify/$', views.mobile_branch_verify, name='mobile_branch_verify'),
    url(r'^edit-branch/(?P<branch_id>\d+)/$', views.edit_branch, name='edit_task'),
    url(r'^branch-delete/(?P<branch_id>\d+)/$', views.delete_branch, name='delete_task'),
    
    url(r'^report/accounts$', views.report_accounts, name='report_accounts'),
    url(r'^report/services$', views.report_services, name='report_services'),
    url(r'^report/agents$', views.report_agents, name='report_agents'),
    url(r'^report/agents-performance$', views.report_agents_performance, name='report_agents_performance'),
    url(r'^report/customer-service$', views.report_customer_service_status, name='report_customer_service_status'),
    url(r'^report/agents-activity$', views.report_agents_activity, name='report_agents_activity'),
    
    url(r'^add-task/$', views.add_task, name='add_task'),
    url(r'^task-list/$', views.task_list, name='task_list'),
    url(r'^edit-task/(?P<task_id>\d+)/$', views.edit_task, name='edit_task'),
    url(r'^task-delete/(?P<task_id>\d+)/$', views.delete_task, name='delete_task'),
    
    url(r'^add-task-role-permission/$', views.add_role_task_permission, name='add_role_task_permission'),
    url(r'^task-role-permission-list/$', views.role_task_permission_list, name='role_task_permission_list'),
    url(r'^edit-task-role-permission/(?P<tast_role_id>\d+)/$', views.edit_role_task_permission, name='edit_role_task_permission'),
    url(r'^task-role-delete/(?P<tast_role_id>\d+)/$', views.delete_task_role, name='delete_task_role'),
    
    url(r'^send-global-message/$', views.send_global_message, name='send_global_message'),
    url(r'^global-message-history/$', views.global_message_history, name='global_message_history'),

    url(r'^sms-test/$', views.sms_test, name='sms_test'),
    url(r'^sms-status/$', views.sms_status, name='sms_status'),
    url(r'^wallet-check/$', views.wallet_check, name='wallet_check'),
    url(r'^dashboard/$', views.dashboard, name='dashboard'),
    
    ]
