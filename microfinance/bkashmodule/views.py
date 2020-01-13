#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.db.models import Count, Q
from django.http import (
    HttpResponseRedirect, HttpResponse)
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext, loader
from django.contrib.auth.models import User
from datetime import date, timedelta, datetime
# from django.utils import simplejson
import json
import logging
import sys
import operator
import pandas
from django.shortcuts import render
import numpy
import time
import datetime
import decimal
from django.core.files.storage import FileSystemStorage

from django.core.urlresolvers import reverse


from django.db import (IntegrityError, transaction)
from django.db.models import ProtectedError
from django.shortcuts import redirect
# from onadata.apps.main.models.user_profile import UserProfile
# from onadata.apps.usermodule.forms import UserForm, UserProfileForm, ChangePasswordForm, UserEditForm, OrganizationForm, \
#     OrganizationDataAccessForm, ResetPasswordForm
# from onadata.apps.usermodule.models import UserModuleProfile, UserPasswordHistory, UserFailedLogin, Organizations, \
#     OrganizationDataAccess

from django.contrib.auth.decorators import login_required, user_passes_test
from django import forms
# Menu imports
# from onadata.apps.usermodule.forms import MenuForm
# from onadata.apps.usermodule.models import MenuItem
# Unicef Imports
# from onadata.apps.logger.models import Instance, XForm
# Organization Roles Import
# from onadata.apps.usermodule.models import OrganizationRole, MenuRoleMap, UserRoleMap
# from onadata.apps.usermodule.forms import OrganizationRoleForm, RoleMenuMapForm, UserRoleMapForm, UserRoleMapfForm
from django.forms.models import inlineformset_factory, modelformset_factory
from django.forms.formsets import formset_factory

from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from collections import OrderedDict
from project_data.models import Complain, ComplainStatusLog, Branch, Notification, Region
from project_data.forms import ComplainForm, BranchForm, NotificationForm

from usermodule.models import UserModuleProfile, Organizations, UserSecurityCode, Task, TaskRolePermissionMap, \
    UserRoleMap, UserAccessLog
from usermodule.forms import TaskForm, TaskRolePermissionMapForm
from usermodule.helpers import BKASH_EXEC_ROLE_ID
from usermodule.views import admin_check

from project_data.helpers import send_push_msg
from microfinance.settings import WALLET_API_SECURITY_KEY, SMS_API_TOKEN, TIME_ZONE, USE_TZ
import xlwt
import os
from django.utils import *

def __db_fetch_values(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = cursor.fetchall()
    cursor.close()
    return fetchVal


def __db_fetch_single_value(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = cursor.fetchone()
    cursor.close()
    return fetchVal[0]


def __db_fetch_values_dict(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = dictfetchall(cursor)
    cursor.close()
    return fetchVal


def __db_commit_query(query):
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    cursor.close()


def dictfetchall(cursor):
    desc = cursor.description
    return [
        OrderedDict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()]


def decimal_date_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        return obj
    raise TypeError


def index(request):
    return render(request, 'bkashmodule/index.html')


@login_required
def comment_list(request):
    query = "select * from comments"
    comment_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return render(request, 'bkashmodule/comment_list.html', {
        'comment_list': comment_list
    })


@login_required
def add_comment_form(request):
    return render(request, 'bkashmodule/add_comment_form.html')


@login_required
def insert_comment_form(request):
    if request.POST:
        service_type = request.POST.get('service_type')
        execution_status = request.POST.get('execution_status')
        comment_text = request.POST.get('comment_text').encode('utf-8').strip()
        insert_query = "INSERT INTO public.comments (service_type, execution_status, comment_text) VALUES('" + str(
            service_type) + "', '" + str(execution_status) + "', '" + str(comment_text) + "')"
        __db_commit_query(insert_query)
        messages.success(request, '<i class="fa fa-check-circle"></i> New Comment has been added successfully!',
                             extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/bkash/comment_list/")

@login_required
def edit_comment_form(request, comment_id):
    query = "select * from comments where id=" + str(comment_id) + ""
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    service_type = df.service_type.tolist()[0]
    execution_status = df.execution_status.tolist()[0]
    comment_text = df.comment_text.tolist()[0]
    return render(request, 'bkashmodule/edit_comment_form.html',
                  {'comment_id':comment_id, 'service_type':service_type, 'execution_status':execution_status, 'comment_text':comment_text})


@login_required
def update_comment_form(request):
    if request.POST:
        service_type = request.POST.get('service_type')
        execution_status = request.POST.get('execution_status')
        comment_text = request.POST.get('comment_text').encode('utf-8').strip()
        comment_id = request.POST.get('comment_id')

        update_query = "UPDATE public.comments SET service_type='" + str(
            service_type) + "', execution_status='" + str(execution_status) + "', comment_text='" + str(
            comment_text) + "' WHERE id=" + str(comment_id)
        __db_commit_query(update_query)
        messages.success(request, '<i class="fa fa-check-circle"></i> Comment has been updated successfully!',
                             extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/bkash/comment_list/")


@login_required
def delete_comment_form(request, comment_id):
    delete_query = "delete from comments where id = " + str(comment_id) + ""
    __db_commit_query(delete_query)
    messages.success(request, '<i class="fa fa-check-circle"></i> Comment has been deleted successfully!',
                             extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/bkash/comment_list/")

@login_required
def region_list(request):
    query = "select * from project_data_region"
    region_list = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return render(request, 'bkashmodule/region_list.html', {
        'region_list': region_list,'region_mgt': 'region_mgt'
    })

@login_required
def add_region_form(request):
    return render(request, 'bkashmodule/add_region_form.html',{'region_mgt': 'region_mgt'})


@login_required
def insert_region_form(request):
    if request.POST:
        region_name = request.POST.get('region_name')
        insert_query = "INSERT INTO public.project_data_region (name) VALUES('" + str(region_name) + "')"
        __db_commit_query(insert_query)
        messages.success(request, '<i class="fa fa-check-circle"></i> New Region has been added successfully!',
                             extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/bkash/region_list/")

@login_required
def edit_region_form(request, region_id):
    query = "select * from project_data_region where id=" + str(region_id) + ""
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    region_name = df.name.tolist()[0]
    return render(request, 'bkashmodule/edit_region_form.html',
                  {'region_id':region_id, 'region_name':region_name,'region_mgt': 'region_mgt'})


@login_required
def update_region_form(request):
    if request.POST:
        region_name = request.POST.get('region_name')
        region_id = request.POST.get('region_id')

        update_query = "UPDATE public.project_data_region SET name='" + str(region_name) + "' WHERE id=" + str(region_id)
        __db_commit_query(update_query)
        messages.success(request, '<i class="fa fa-check-circle"></i> Region has been updated successfully!',
                             extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/bkash/region_list/")


@login_required
def delete_region_form(request, region_id):
    delete_query = "delete from project_data_region where id = " + str(region_id) + ""
    __db_commit_query(delete_query)
    messages.success(request, '<i class="fa fa-check-circle"></i> Region has been deleted successfully!',
                             extra_tags='alert-success crop-both-side')
    return HttpResponseRedirect("/bkash/region_list/")


def report_services(request):
    for_region = "select * from project_data_region"
    df = pandas.DataFrame()
    df = pandas.read_sql(for_region,connection)
    region = zip(df.id.tolist(),df.name.tolist())

    from_date = datetime.datetime.now().date()- timedelta(days=30)
    to_date = datetime.datetime.now().date()
    return render(request,'bkashmodule/report_services.html', {'reports': 'reports', 'service': 'service','region':region,'from_date':from_date,'to_date':to_date})



@csrf_exempt
def get_report_services(request):
    from_date = str(request.POST.get('from_date')) + ' 00:00:00'
    to_date = str(request.POST.get('to_date')) + ' 23:59:59'
    region = request.POST.get('region')
    branch = request.POST.get('branch')
    stat = request.POST.get('stat')

    user_id = request.user.id
    role_check_query = "select role_id from usermodule_userrolemap where user_id = (select id from usermodule_usermoduleprofile where user_id = " + str(
        user_id) + ")"
    df = pandas.DataFrame()
    df = pandas.read_sql(role_check_query, connection)
    # stat for whether export or data filter. if 0, data filter else export
    if stat=='0':
        if not df.empty:
            role_id = df.role_id.tolist()[0]
            # bkash agent
            if role_id == 3:
                query = "WITH _mat AS(SELECT * FROM project_data_complain WHERE pin_id = ANY (SELECT user_id FROM usermodule_usermoduleprofile WHERE region_id :: text LIKE '" + str(region) + "' AND branch_id :: text LIKE '" + str( branch) + "') AND reply_by = "+str(user_id)+" AND ticket_close_time BETWEEN '" + str(from_date) + "' AND '" + str( to_date) + "'), total_tbl AS (SELECT service_type, Count(*) total_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}') GROUP BY service_type), aht_tbl AS (SELECT _mat.service_type, total_cnt, Coalesce(To_char(( ( SUM(Extract(epoch FROM sla :: interval) :: INT) / total_cnt ) || ' second' ) :: interval, 'HH24:MI:SS'), '00:00:00' ) aht FROM _mat, total_tbl WHERE _mat.service_type = total_tbl.service_type AND execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) GROUP BY _mat.service_type, total_cnt), solved AS (SELECT service_type, Count(*) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) GROUP BY service_type), solved_aht AS (SELECT aht_tbl.*, Coalesce(solved_cnt, 0) solved_cnt FROM aht_tbl left join solved ON aht_tbl.service_type = solved.service_type), closed AS (SELECT service_type, Count(*) closed_cnt FROM _mat WHERE execution_status = 'Closed' GROUP BY service_type), solved_aht_closed AS (SELECT solved_aht.*, Coalesce(closed_cnt, 0) closed_cnt FROM solved_aht left join closed ON solved_aht.service_type = closed.service_type), within_sla AS (SELECT service_type, Count(*) within_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT BETWEEN 0 AND Extract( epoch FROM given_sla_time) :: INT GROUP BY service_type), solved_aht_closed_withinsla AS (SELECT solved_aht_closed.*, Coalesce(within_cnt, 0) within_cnt FROM solved_aht_closed left join within_sla ON solved_aht_closed.service_type = within_sla.service_type), without_sla AS (SELECT service_type, Count(*) without_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT > Extract(epoch FROM given_sla_time) :: INT GROUP BY service_type) SELECT solved_aht_closed_withinsla.*, Coalesce(without_cnt, 0) without_cnt FROM solved_aht_closed_withinsla left join without_sla ON solved_aht_closed_withinsla.service_type = without_sla.service_type "
            else:
                query = "WITH _mat AS(SELECT * FROM project_data_complain WHERE pin_id = ANY (SELECT user_id FROM usermodule_usermoduleprofile WHERE region_id :: text LIKE '" + str(region) + "' AND branch_id :: text LIKE '" + str(branch) + "') AND ticket_close_time BETWEEN '" + str(from_date) + "' AND '" + str(to_date) + "'), total_tbl AS (SELECT service_type, Count(*) total_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}') GROUP BY service_type), aht_tbl AS (SELECT _mat.service_type, total_cnt, Coalesce(To_char(( ( SUM(Extract(epoch FROM sla::interval) :: INT) / total_cnt ) || ' second' ) :: interval, 'HH24:MI:SS'), '00:00:00' ) aht FROM _mat, total_tbl WHERE _mat.service_type = total_tbl.service_type AND execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) GROUP BY _mat.service_type, total_cnt), solved AS (SELECT service_type, Count(*) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) GROUP BY service_type), solved_aht AS (SELECT aht_tbl.*, Coalesce(solved_cnt, 0) solved_cnt FROM aht_tbl left join solved ON aht_tbl.service_type = solved.service_type), closed AS (SELECT service_type, Count(*) closed_cnt FROM _mat WHERE execution_status = 'Closed' GROUP BY service_type), solved_aht_closed AS (SELECT solved_aht.*, Coalesce(closed_cnt, 0) closed_cnt FROM solved_aht left join closed ON solved_aht.service_type = closed.service_type), within_sla AS (SELECT service_type, Count(*) within_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla::interval) ::INT BETWEEN 0 AND Extract(epoch FROM given_sla_time) :: INT GROUP BY service_type), solved_aht_closed_withinsla AS (SELECT solved_aht_closed.*, Coalesce(within_cnt, 0) within_cnt FROM solved_aht_closed left join within_sla ON solved_aht_closed.service_type = within_sla.service_type), without_sla AS (SELECT service_type, Count(*) without_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla::interval) :: INT > Extract(epoch FROM given_sla_time) :: INT GROUP BY service_type) SELECT solved_aht_closed_withinsla.*, Coalesce(without_cnt, 0) without_cnt FROM solved_aht_closed_withinsla left join without_sla ON solved_aht_closed_withinsla.service_type = without_sla.service_type "
            print(query)
        else:
            query = "WITH _mat AS(SELECT * FROM project_data_complain WHERE pin_id = ANY (SELECT user_id FROM usermodule_usermoduleprofile WHERE region_id :: text LIKE '" + str(region) + "' AND branch_id :: text LIKE '" + str(branch) + "') AND ticket_close_time BETWEEN '" + str(from_date) + "' AND '" + str(to_date) + "'), total_tbl AS (SELECT service_type, Count(*) total_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) GROUP BY service_type), aht_tbl AS (SELECT _mat.service_type, total_cnt, Coalesce(To_char(( ( SUM(Extract(epoch FROM sla::interval) :: INT) / total_cnt ) || ' second' ) :: interval, 'HH24:MI:SS'), '00:00:00' ) aht FROM _mat, total_tbl WHERE _mat.service_type = total_tbl.service_type AND execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) GROUP BY _mat.service_type, total_cnt), solved AS (SELECT service_type, Count(*) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) GROUP BY service_type), solved_aht AS (SELECT aht_tbl.*, Coalesce(solved_cnt, 0) solved_cnt FROM aht_tbl left join solved ON aht_tbl.service_type = solved.service_type), closed AS (SELECT service_type, Count(*) closed_cnt FROM _mat WHERE execution_status = 'Closed' GROUP BY service_type), solved_aht_closed AS (SELECT solved_aht.*, Coalesce(closed_cnt, 0) closed_cnt FROM solved_aht left join closed ON solved_aht.service_type = closed.service_type), within_sla AS (SELECT service_type, Count(*) within_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla::interval) :: INT BETWEEN 0 AND Extract(epoch FROM given_sla_time) :: INT GROUP BY service_type), solved_aht_closed_withinsla AS (SELECT solved_aht_closed.*, Coalesce(within_cnt, 0) within_cnt FROM solved_aht_closed left join within_sla ON solved_aht_closed.service_type = within_sla.service_type), without_sla AS (SELECT service_type, Count(*) without_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla::interval) :: INT > Extract(epoch FROM given_sla_time) :: INT GROUP BY service_type) SELECT solved_aht_closed_withinsla.*, Coalesce(without_cnt, 0) without_cnt FROM solved_aht_closed_withinsla left join without_sla ON solved_aht_closed_withinsla.service_type = without_sla.service_type "
            print(query)
        data = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
        return HttpResponse(data)
    else:
        if not df.empty:
            role_id = df.role_id.tolist()[0]
            # bkash agent
            if role_id == 3:
                query = """ WITH _mat AS(SELECT * FROM project_data_complain WHERE pin_id = ANY (SELECT user_id FROM usermodule_usermoduleprofile WHERE region_id :: text LIKE '""" + str(region) + """' AND branch_id :: text LIKE '""" + str( branch) + """') AND reply_by = """+str(user_id)+""" AND ticket_close_time BETWEEN '""" + str(from_date) + """' AND '""" + str(to_date) + """') , total_tbl AS (SELECT service_type, Count(*) total_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) GROUP BY service_type), aht_tbl AS (SELECT _mat.service_type, total_cnt, Coalesce(To_char(( ( SUM(Extract(epoch FROM sla :: interval):: INT) /total_cnt)|| ' second' ) :: interval, 'HH24:MI:SS'),'00:00:00') aht FROM _mat, total_tbl WHERE _mat.service_type = total_tbl.service_type AND execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) GROUP BY _mat.service_type, total_cnt), solved AS (SELECT service_type, Count(*) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) GROUP BY service_type), solved_aht AS (SELECT aht_tbl.*, Coalesce(solved_cnt, 0) solved_cnt FROM aht_tbl left join solved ON aht_tbl.service_type = solved.service_type), closed AS (SELECT service_type, Count(*) closed_cnt FROM _mat WHERE execution_status = 'Closed' GROUP BY service_type), solved_aht_closed AS (SELECT solved_aht.*, Coalesce(closed_cnt, 0) closed_cnt FROM solved_aht left join closed ON solved_aht.service_type = closed.service_type), within_sla AS (SELECT service_type, Count(*) within_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT BETWEEN 0 AND Extract(epoch FROM given_sla_time) :: INT GROUP BY service_type), solved_aht_closed_withinsla AS (SELECT solved_aht_closed.*, Coalesce(within_cnt, 0) within_cnt FROM solved_aht_closed left join within_sla ON solved_aht_closed.service_type = within_sla.service_type), without_sla AS (SELECT service_type, Count(*) without_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT > Extract(epoch FROM given_sla_time) :: INT GROUP BY service_type) SELECT solved_aht_closed_withinsla.service_type as "Service Type", solved_aht_closed_withinsla.total_cnt AS "Account Served", solved_aht_closed_withinsla.solved_cnt AS "Solved", solved_aht_closed_withinsla.closed_cnt AS "Closed", solved_aht_closed_withinsla.aht AS "AHT", solved_aht_closed_withinsla.within_cnt AS "Within SLA", Coalesce(without_cnt, 0) AS "Without SLA" FROM solved_aht_closed_withinsla left join without_sla ON solved_aht_closed_withinsla.service_type = without_sla.service_type  """
            else:
                query = """ WITH _mat AS(SELECT * FROM project_data_complain WHERE pin_id = ANY (SELECT user_id FROM usermodule_usermoduleprofile WHERE region_id :: text LIKE '""" + str(region) + """' AND branch_id :: text LIKE '""" + str(branch) + """') AND ticket_close_time BETWEEN '""" + str(from_date) + """' AND '""" + str(to_date) + """'), total_tbl AS (SELECT service_type, Count(*) total_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) GROUP BY service_type), aht_tbl AS (SELECT _mat.service_type, total_cnt, Coalesce(To_char(( ( SUM(Extract(epoch FROM sla :: interval) :: INT) / total_cnt ) || ' second' ) :: interval, 'HH24:MI:SS'), '00:00:00' ) aht FROM _mat, total_tbl WHERE _mat.service_type = total_tbl.service_type AND execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) GROUP BY _mat.service_type, total_cnt), solved AS (SELECT service_type, Count(*) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) GROUP BY service_type), solved_aht AS (SELECT aht_tbl.*, Coalesce(solved_cnt, 0) solved_cnt FROM aht_tbl left join solved ON aht_tbl.service_type = solved.service_type), closed AS (SELECT service_type, Count(*) closed_cnt FROM _mat WHERE execution_status = 'Closed' GROUP BY service_type), solved_aht_closed AS (SELECT solved_aht.*, Coalesce(closed_cnt, 0) closed_cnt FROM solved_aht left join closed ON solved_aht.service_type = closed.service_type), within_sla AS (SELECT service_type, Count(*) within_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT BETWEEN 0 AND Extract(epoch FROM given_sla_time) :: INT GROUP BY service_type), solved_aht_closed_withinsla AS (SELECT solved_aht_closed.*, Coalesce(within_cnt, 0) within_cnt FROM solved_aht_closed left join within_sla ON solved_aht_closed.service_type = within_sla.service_type), without_sla AS (SELECT service_type, Count(*) without_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT > Extract(epoch FROM given_sla_time) :: INT GROUP BY service_type) SELECT solved_aht_closed_withinsla.service_type as "Service Type", solved_aht_closed_withinsla.total_cnt AS "Account Served", solved_aht_closed_withinsla.solved_cnt AS "Solved", solved_aht_closed_withinsla.closed_cnt AS "Closed", solved_aht_closed_withinsla.aht AS "AHT", solved_aht_closed_withinsla.within_cnt AS "Within SLA", Coalesce(without_cnt, 0) AS "Without SLA" FROM solved_aht_closed_withinsla left join without_sla ON solved_aht_closed_withinsla.service_type = without_sla.service_type """
        else:
            query = """ WITH _mat AS(SELECT * FROM project_data_complain WHERE pin_id = ANY (SELECT user_id FROM usermodule_usermoduleprofile WHERE region_id :: text LIKE '""" + str(region) + """' AND branch_id :: text LIKE '""" + str(branch) + """') AND ticket_close_time BETWEEN '""" + str(from_date) + """' AND '""" + str(to_date) + """'), total_tbl AS (SELECT service_type, Count(*) total_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) GROUP BY service_type), aht_tbl AS (SELECT _mat.service_type, total_cnt, Coalesce(To_char(( ( SUM(Extract(epoch FROM sla :: interval) :: INT) / total_cnt ) || ' second' ) :: interval, 'HH24:MI:SS'), '00:00:00' ) aht FROM _mat, total_tbl WHERE _mat.service_type = total_tbl.service_type AND execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) GROUP BY _mat.service_type, total_cnt), solved AS (SELECT service_type, Count(*) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) GROUP BY service_type), solved_aht AS (SELECT aht_tbl.*, Coalesce(solved_cnt, 0) solved_cnt FROM aht_tbl left join solved ON aht_tbl.service_type = solved.service_type), closed AS (SELECT service_type, Count(*) closed_cnt FROM _mat WHERE execution_status = 'Closed' GROUP BY service_type), solved_aht_closed AS (SELECT solved_aht.*, Coalesce(closed_cnt, 0) closed_cnt FROM solved_aht left join closed ON solved_aht.service_type = closed.service_type), within_sla AS (SELECT service_type, Count(*) within_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT BETWEEN 0 AND Extract(epoch FROM given_sla_time) :: INT GROUP BY service_type), solved_aht_closed_withinsla AS (SELECT solved_aht_closed.*, Coalesce(within_cnt, 0) within_cnt FROM solved_aht_closed left join within_sla ON solved_aht_closed.service_type = within_sla.service_type), without_sla AS (SELECT service_type, Count(*) without_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT > Extract(epoch FROM given_sla_time) :: INT GROUP BY service_type) SELECT solved_aht_closed_withinsla.service_type as "Service Type", solved_aht_closed_withinsla.total_cnt AS "Account Served", solved_aht_closed_withinsla.solved_cnt AS "Solved", solved_aht_closed_withinsla.closed_cnt AS "Closed", solved_aht_closed_withinsla.aht AS "AHT", solved_aht_closed_withinsla.within_cnt AS "Within SLA", Coalesce(without_cnt, 0) AS "Without SLA" FROM solved_aht_closed_withinsla left join without_sla ON solved_aht_closed_withinsla.service_type = without_sla.service_type """
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        writer = pandas.ExcelWriter("static/media/uploaded_files/output.xls")
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        writer.save()
        f = open('static/media/uploaded_files/output.xls', 'r')
        response = HttpResponse(f, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=Service.xls'
        return response



def report_bkash_agents(request):
    for_agents = "select id,first_name from auth_user where id = any(select user_id from usermodule_usermoduleprofile where account_type_id = 3)"
    df = pandas.DataFrame()
    df = pandas.read_sql(for_agents,connection)
    agents = zip(df.id.tolist(),df.first_name.tolist())
    from_date = datetime.datetime.now().date()- timedelta(days=30)
    to_date = datetime.datetime.now().date()
    return render(request,'bkashmodule/report_bkash_agents.html', {'reports': 'reports', 'agent': 'agent','agents':agents,'from_date':from_date,'to_date':to_date})

@csrf_exempt
def get_bkash_agents_report(request):
    request_from_date = request.POST.get('request_from_date')
    request_to_date = request.POST.get('request_to_date')
    reply_from_date = request.POST.get('reply_from_date')
    reply_to_date = request.POST.get('reply_to_date')
    agent = request.POST.get('agent')
    stat = request.POST.get('stat')
    user_id = request.user.id
    role_check_query = "select role_id from usermodule_userrolemap where user_id = (select id from usermodule_usermoduleprofile where user_id = " + str(user_id) + ")"
    df = pandas.DataFrame()
    df = pandas.read_sql(role_check_query, connection)
    if stat == '0':
        if not df.empty:
            role_id = df.role_id.tolist()[0]
            # bkash agent
            if role_id == 3:
                    query = "WITH _mat AS(SELECT * FROM project_data_complain WHERE  reply_by = " + str(user_id) + "  AND received_time BETWEEN '" + str(request_from_date) + "' AND '" + str(request_to_date) + "' AND ticket_close_time BETWEEN '" + str(reply_from_date) + "' AND '" + str(reply_to_date) + "'), total_tbl AS (SELECT reply_by, Count(*) total_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}') GROUP BY reply_by),aht_tbl AS (SELECT _mat.reply_by, total_cnt, Coalesce(To_char(( ( SUM(Extract(epoch FROM sla :: interval) :: INT) / total_cnt)|| ' second' ) :: interval, 'HH24:MI:SS'),'00:00:00') aht FROM _mat, total_tbl WHERE _mat.reply_by = total_tbl.reply_by AND execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) GROUP BY _mat.reply_by, total_cnt), solved AS (SELECT reply_by, Count(*) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) GROUP BY reply_by), solved_aht AS (SELECT aht_tbl.*, Coalesce(solved_cnt, 0) solved_cnt FROM aht_tbl left join solved ON aht_tbl.reply_by = solved.reply_by), closed AS (SELECT reply_by, Count(*) closed_cnt FROM _mat WHERE execution_status = 'Closed' GROUP BY reply_by), solved_aht_closed AS (SELECT solved_aht.*, Coalesce(closed_cnt, 0) closed_cnt FROM solved_aht left join closed ON solved_aht.reply_by = closed.reply_by), within_sla AS (SELECT reply_by, Count(*) within_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT BETWEEN 0 AND Extract(epoch FROM given_sla_time) :: INT GROUP BY reply_by), solved_aht_closed_withinsla AS (SELECT solved_aht_closed.*, Coalesce(within_cnt, 0) within_cnt FROM solved_aht_closed left join within_sla ON solved_aht_closed.reply_by = within_sla.reply_by), without_sla AS (SELECT reply_by, Count(*) without_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT > Extract(epoch FROM given_sla_time) :: INT GROUP BY reply_by) SELECT solved_aht_closed_withinsla.reply_by,(SELECT username FROM auth_user WHERE id = solved_aht_closed_withinsla.reply_by) emp_id, (SELECT first_name FROM auth_user WHERE id = solved_aht_closed_withinsla.reply_by) emp_name ,total_cnt,aht, solved_cnt,closed_cnt,within_cnt, Coalesce(without_cnt, 0) without_cnt FROM solved_aht_closed_withinsla left join without_sla ON solved_aht_closed_withinsla.reply_by = without_sla.reply_by"
            else:
                query = "WITH _mat AS(SELECT * FROM project_data_complain WHERE reply_by = ANY (SELECT user_id FROM usermodule_usermoduleprofile WHERE user_id :: text LIKE '"+str(agent)+"' AND account_type_id = 3) AND received_time BETWEEN '" + str(request_from_date) + "' AND '" + str(request_to_date) + "' AND ticket_close_time BETWEEN '" + str(reply_from_date) + "' AND '" + str(reply_to_date) + "'), total_tbl AS (SELECT reply_by, Count(*) total_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}') GROUP BY reply_by),aht_tbl AS (SELECT _mat.reply_by, total_cnt, Coalesce(To_char(( ( SUM(Extract(epoch FROM sla :: interval) :: INT) / total_cnt)|| ' second' ) :: interval, 'HH24:MI:SS'),'00:00:00') aht FROM _mat, total_tbl WHERE _mat.reply_by = total_tbl.reply_by AND execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) GROUP BY _mat.reply_by, total_cnt), solved AS (SELECT reply_by, Count(*) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) GROUP BY reply_by), solved_aht AS (SELECT aht_tbl.*, Coalesce(solved_cnt, 0) solved_cnt FROM aht_tbl left join solved ON aht_tbl.reply_by = solved.reply_by), closed AS (SELECT reply_by, Count(*) closed_cnt FROM _mat WHERE execution_status = 'Closed' GROUP BY reply_by), solved_aht_closed AS (SELECT solved_aht.*, Coalesce(closed_cnt, 0) closed_cnt FROM solved_aht left join closed ON solved_aht.reply_by = closed.reply_by), within_sla AS (SELECT reply_by, Count(*) within_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT BETWEEN 0 AND Extract(epoch FROM given_sla_time) :: INT GROUP BY reply_by), solved_aht_closed_withinsla AS (SELECT solved_aht_closed.*, Coalesce(within_cnt, 0) within_cnt FROM solved_aht_closed left join within_sla ON solved_aht_closed.reply_by = within_sla.reply_by), without_sla AS (SELECT reply_by, Count(*) without_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT > Extract(epoch FROM given_sla_time) :: INT GROUP BY reply_by) SELECT solved_aht_closed_withinsla.reply_by,(SELECT username FROM auth_user WHERE id = solved_aht_closed_withinsla.reply_by) emp_id, (SELECT first_name FROM auth_user WHERE id = solved_aht_closed_withinsla.reply_by) emp_name ,total_cnt,aht, solved_cnt,closed_cnt,within_cnt, Coalesce(without_cnt, 0) without_cnt FROM solved_aht_closed_withinsla left join without_sla ON solved_aht_closed_withinsla.reply_by = without_sla.reply_by "
        else:
            query = " WITH _mat AS(SELECT * FROM project_data_complain WHERE reply_by = ANY (SELECT user_id FROM usermodule_usermoduleprofile WHERE user_id :: text LIKE '"+str(agent)+"' AND account_type_id = 3) AND received_time BETWEEN '" + str(request_from_date) + "' AND '" + str(request_to_date) + "' AND ticket_close_time BETWEEN '" + str(reply_from_date) + "' AND '" + str(reply_to_date) + "'), total_tbl AS (SELECT reply_by, Count(*) total_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}') GROUP BY reply_by),aht_tbl AS (SELECT _mat.reply_by, total_cnt, Coalesce(To_char(( ( SUM(Extract(epoch FROM sla :: interval) :: INT) / total_cnt)|| ' second' ) :: interval, 'HH24:MI:SS'),'00:00:00') aht FROM _mat, total_tbl WHERE _mat.reply_by = total_tbl.reply_by AND execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) GROUP BY _mat.reply_by, total_cnt), solved AS (SELECT reply_by, Count(*) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) GROUP BY reply_by), solved_aht AS (SELECT aht_tbl.*, Coalesce(solved_cnt, 0) solved_cnt FROM aht_tbl left join solved ON aht_tbl.reply_by = solved.reply_by), closed AS (SELECT reply_by, Count(*) closed_cnt FROM _mat WHERE execution_status = 'Closed' GROUP BY reply_by), solved_aht_closed AS (SELECT solved_aht.*, Coalesce(closed_cnt, 0) closed_cnt FROM solved_aht left join closed ON solved_aht.reply_by = closed.reply_by), within_sla AS (SELECT reply_by, Count(*) within_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT BETWEEN 0 AND Extract(epoch FROM given_sla_time) :: INT GROUP BY reply_by), solved_aht_closed_withinsla AS (SELECT solved_aht_closed.*, Coalesce(within_cnt, 0) within_cnt FROM solved_aht_closed left join within_sla ON solved_aht_closed.reply_by = within_sla.reply_by), without_sla AS (SELECT reply_by, Count(*) without_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT > Extract(epoch FROM given_sla_time) :: INT GROUP BY reply_by) SELECT solved_aht_closed_withinsla.reply_by,(SELECT username FROM auth_user WHERE id = solved_aht_closed_withinsla.reply_by) emp_id, (SELECT first_name FROM auth_user WHERE id = solved_aht_closed_withinsla.reply_by) emp_name ,total_cnt,aht, solved_cnt,closed_cnt,within_cnt, Coalesce(without_cnt, 0) without_cnt FROM solved_aht_closed_withinsla left join without_sla ON solved_aht_closed_withinsla.reply_by = without_sla.reply_by "
        print(query)
        data = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
        return HttpResponse(data)
    else:
        if not df.empty:
            role_id = df.role_id.tolist()[0]
            # bkash agent
            if role_id == 3:
                query = """ WITH _mat AS(SELECT * FROM project_data_complain WHERE reply_by = """ + str(user_id) + """ AND received_time BETWEEN '""" + str(request_from_date) + """' AND '""" + str(request_to_date) + """' AND ticket_close_time BETWEEN '""" + str(reply_from_date) + """' AND '""" + str(reply_to_date) + """'), total_tbl AS (SELECT reply_by, Count(*) total_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}') GROUP BY reply_by), aht_tbl AS (SELECT _mat.reply_by, total_cnt, Coalesce(To_char(( ( SUM(Extract(epoch FROM sla :: interval) :: INT) / total_cnt ) || ' second' ) :: interval, 'HH24:MI:SS'), '00:00:00' ) aht FROM _mat, total_tbl WHERE _mat.reply_by = total_tbl.reply_by AND execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) GROUP BY _mat.reply_by, total_cnt), solved AS (SELECT reply_by, Count(*) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) GROUP BY reply_by), solved_aht AS (SELECT aht_tbl.*, Coalesce(solved_cnt, 0) solved_cnt FROM aht_tbl left join solved ON aht_tbl.reply_by = solved.reply_by), closed AS (SELECT reply_by, Count(*) closed_cnt FROM _mat WHERE execution_status = 'Closed' GROUP BY reply_by), solved_aht_closed AS (SELECT solved_aht.*, Coalesce(closed_cnt, 0) closed_cnt FROM solved_aht left join closed ON solved_aht.reply_by = closed.reply_by), within_sla AS (SELECT reply_by, Count(*) within_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT BETWEEN 0 AND Extract(epoch FROM given_sla_time) :: INT GROUP BY reply_by), solved_aht_closed_withinsla AS (SELECT solved_aht_closed.*, Coalesce(within_cnt, 0) within_cnt FROM solved_aht_closed left join within_sla ON solved_aht_closed.reply_by = within_sla.reply_by), without_sla AS (SELECT reply_by, Count(*) without_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT > Extract(epoch FROM given_sla_time) :: INT GROUP BY reply_by) SELECT (SELECT username FROM auth_user WHERE id = solved_aht_closed_withinsla.reply_by) as "Employee ID", (SELECT first_name FROM auth_user WHERE id = solved_aht_closed_withinsla.reply_by) as "Employee Name", total_cnt as "Ticket Served", solved_cnt as "Solved", closed_cnt as "Closed", aht as "AHT", within_cnt as "Within SLA", Coalesce(without_cnt, 0) as "Beyond SLA" FROM solved_aht_closed_withinsla left join without_sla ON solved_aht_closed_withinsla.reply_by = without_sla.reply_by """
            else:
                query = """ WITH _mat AS(SELECT * FROM project_data_complain WHERE reply_by = ANY (SELECT user_id FROM usermodule_usermoduleprofile WHERE user_id :: text LIKE '"""+str(agent)+"""' AND account_type_id = 3) AND received_time BETWEEN '""" + str(request_from_date) + """' AND '""" + str(request_to_date) + """' AND ticket_close_time BETWEEN '""" + str(reply_from_date) + """' AND '""" + str(reply_to_date) + """'), total_tbl AS (SELECT reply_by, Count(*) total_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}') GROUP BY reply_by), aht_tbl AS (SELECT _mat.reply_by, total_cnt, Coalesce(To_char(( ( SUM(Extract(epoch FROM sla :: interval) :: INT) / total_cnt ) || ' second' ) :: interval, 'HH24:MI:SS'), '00:00:00' ) aht FROM _mat, total_tbl WHERE _mat.reply_by = total_tbl.reply_by AND execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) GROUP BY _mat.reply_by, total_cnt), solved AS (SELECT reply_by, Count(*) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) GROUP BY reply_by), solved_aht AS (SELECT aht_tbl.*, Coalesce(solved_cnt, 0) solved_cnt FROM aht_tbl left join solved ON aht_tbl.reply_by = solved.reply_by), closed AS (SELECT reply_by, Count(*) closed_cnt FROM _mat WHERE execution_status = 'Closed' GROUP BY reply_by), solved_aht_closed AS (SELECT solved_aht.*, Coalesce(closed_cnt, 0) closed_cnt FROM solved_aht left join closed ON solved_aht.reply_by = closed.reply_by), within_sla AS (SELECT reply_by, Count(*) within_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT BETWEEN 0 AND Extract(epoch FROM given_sla_time) :: INT GROUP BY reply_by), solved_aht_closed_withinsla AS (SELECT solved_aht_closed.*, Coalesce(within_cnt, 0) within_cnt FROM solved_aht_closed left join within_sla ON solved_aht_closed.reply_by = within_sla.reply_by), without_sla AS (SELECT reply_by, Count(*) without_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT > Extract(epoch FROM given_sla_time) :: INT GROUP BY reply_by) SELECT (SELECT username FROM auth_user WHERE id = solved_aht_closed_withinsla.reply_by) as "Employee ID", (SELECT first_name FROM auth_user WHERE id = solved_aht_closed_withinsla.reply_by) as "Employee Name", total_cnt as "Ticket Served", solved_cnt as "Solved", closed_cnt as "Closed", aht as "AHT", within_cnt as "Within SLA", Coalesce(without_cnt, 0) as "Beyond SLA" FROM solved_aht_closed_withinsla left join without_sla ON solved_aht_closed_withinsla.reply_by = without_sla.reply_by """
        else:
            query = """ WITH _mat AS(SELECT * FROM project_data_complain WHERE reply_by = ANY (SELECT user_id FROM usermodule_usermoduleprofile WHERE user_id :: text LIKE '"""+str(agent)+"""' AND account_type_id = 3) AND received_time BETWEEN '""" + str(request_from_date) + """' AND '""" + str(request_to_date) + """' AND ticket_close_time BETWEEN '""" + str(reply_from_date) + """' AND '""" + str(reply_to_date) + """'), total_tbl AS (SELECT reply_by, Count(*) total_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}') GROUP BY reply_by), aht_tbl AS (SELECT _mat.reply_by, total_cnt, Coalesce(To_char(( ( SUM(Extract(epoch FROM sla :: interval) :: INT) / total_cnt ) || ' second' ) :: interval, 'HH24:MI:SS'), '00:00:00' ) aht FROM _mat, total_tbl WHERE _mat.reply_by = total_tbl.reply_by AND execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) GROUP BY _mat.reply_by, total_cnt), solved AS (SELECT reply_by, Count(*) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) GROUP BY reply_by), solved_aht AS (SELECT aht_tbl.*, Coalesce(solved_cnt, 0) solved_cnt FROM aht_tbl left join solved ON aht_tbl.reply_by = solved.reply_by), closed AS (SELECT reply_by, Count(*) closed_cnt FROM _mat WHERE execution_status = 'Closed' GROUP BY reply_by), solved_aht_closed AS (SELECT solved_aht.*, Coalesce(closed_cnt, 0) closed_cnt FROM solved_aht left join closed ON solved_aht.reply_by = closed.reply_by), within_sla AS (SELECT reply_by, Count(*) within_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT BETWEEN 0 AND Extract(epoch FROM given_sla_time) :: INT GROUP BY reply_by), solved_aht_closed_withinsla AS (SELECT solved_aht_closed.*, Coalesce(within_cnt, 0) within_cnt FROM solved_aht_closed left join within_sla ON solved_aht_closed.reply_by = within_sla.reply_by), without_sla AS (SELECT reply_by, Count(*) without_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed,Closed}' ) AND Extract(epoch FROM sla :: interval) :: INT > Extract(epoch FROM given_sla_time) :: INT GROUP BY reply_by) SELECT (SELECT username FROM auth_user WHERE id = solved_aht_closed_withinsla.reply_by) as "Employee ID", (SELECT first_name FROM auth_user WHERE id = solved_aht_closed_withinsla.reply_by) as "Employee Name", total_cnt as "Ticket Served", solved_cnt as "Solved", closed_cnt as "Closed", aht as "AHT", within_cnt as "Within SLA", Coalesce(without_cnt, 0) as "Beyond SLA" FROM solved_aht_closed_withinsla left join without_sla ON solved_aht_closed_withinsla.reply_by = without_sla.reply_by """

        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        writer = pandas.ExcelWriter("static/media/uploaded_files/output.xls")
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        writer.save()
        f = open('static/media/uploaded_files/output.xls', 'r')
        response = HttpResponse(f, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=bKash Agent Report.xls'
        return response

def account_rpt(request):
    for_agents = "select id,first_name from auth_user where id = any(select user_id from usermodule_usermoduleprofile where account_type_id = 3)"
    df = pandas.DataFrame()
    df = pandas.read_sql(for_agents, connection)
    bkash_agents = zip(df.id.tolist(), df.first_name.tolist())
    for_agents = "select id,first_name,username from auth_user where id = any(select user_id from usermodule_usermoduleprofile where account_type_id = 2)"
    df = pandas.DataFrame()
    df = pandas.read_sql(for_agents, connection)
    brac_agents = zip(df.id.tolist(), df.first_name.tolist())
    for_region = "select * from project_data_region"
    df = pandas.DataFrame()
    df = pandas.read_sql(for_region, connection)
    region = zip(df.id.tolist(), df.name.tolist())
    user_id = request.user.id
    query_role = "select role_id from usermodule_userrolemap where user_id = (select id from usermodule_usermoduleprofile where user_id = " + str(
        user_id) + ")"
    df = pandas.DataFrame()
    df = pandas.read_sql(query_role, connection)
    if not df.empty:
        role_id = df.role_id.tolist()[0]
    else:
        role_id = 0
    from_date = datetime.datetime.now().date() - timedelta(days=30)
    to_date = datetime.datetime.now().date()
    return render(request, 'bkashmodule/account_rpt.html',
                  {'reports': 'reports', 'account': 'account', 'bkash_agents': bkash_agents,'brac_agents':brac_agents,'region':region,'role_id':role_id, 'from_date': from_date,
                   'to_date': to_date})

@csrf_exempt
def get_account_rpt(request):
    request_from_date = request.POST.get('request_from_date')
    request_to_date = request.POST.get('request_to_date')
    reply_from_date = request.POST.get('reply_from_date')
    reply_to_date = request.POST.get('reply_to_date')
    brac_agent = request.POST.get('brac_agent')
    bkash_agent = request.POST.get('bkash_agent')
    action = request.POST.get('action')
    service_type = request.POST.get('service_type')
    region = request.POST.get('region')
    branch = request.POST.get('branch')
    stat = request.POST.get('stat')
    user_id = request.user.id
    role_check_query = "select role_id from usermodule_userrolemap where user_id = (select id from usermodule_usermoduleprofile where user_id = " + str(user_id) + ")"
    df = pandas.DataFrame()
    df = pandas.read_sql(role_check_query, connection)
    if stat == '0':
        if not df.empty:
            role_id = df.role_id.tolist()[0]
            # bkash agent
            if role_id == 3:
                    query = "with t as( select * from project_data_complain WHERE pin_id = ANY (SELECT user_id FROM usermodule_usermoduleprofile WHERE region_id :: text LIKE '" + str(region) + "' AND branch_id :: text LIKE '" + str(branch) + "' AND user_id :: text LIKE '"+str(brac_agent)+"') AND received_time BETWEEN '" + str(request_from_date) + "' AND '" + str(request_to_date) + "' AND ticket_close_time BETWEEN '" + str(reply_from_date) + "' AND '" + str(reply_to_date) + "' AND service_type LIKE '"+str(service_type)+"' and execution_status like '"+str(action)+"' AND reply_by :: text LIKE '"+ str(user_id) +"' order by ticket_id) select ROW_NUMBER () OVER () serial_no,ticket_id,account_no,service_type,execution_status category,(select (select name from project_data_region where id = region_id limit 1)region_id from usermodule_usermoduleprofile where user_id = pin_id limit 1) region,(select (select name from project_data_branch where id = usermodule_usermoduleprofile.branch_id::int limit 1)branch_id from usermodule_usermoduleprofile where user_id = pin_id limit 1) branch ,(select username from auth_user where id = pin_id limit 1)csa_agent_id,(select first_name from auth_user where id = pin_id limit 1) csa_agent_name,to_char(calculated_sla_time,'dd-MON-yyyy hh12:mi AM') request_date_time,coalesce(to_char(ticket_close_time,'dd-MON-yyyy hh12:mi AM'),'') reply_date_time ,coalesce((select username from auth_user where id = reply_by::int limit 1),'')bkash_agent_id,coalesce((select first_name from auth_user where id = reply_by::int limit 1),'') bkash_agent_name ,case when id_no is not null then 'NID: ' || id_no else '' end || case when transaction_id is not null then '<br>Transaction ID: ' || transaction_id else '' end || case when transaction_date_time is not null then '<br>Transaction Date: ' || transaction_date_time::date else '' end || case when transaction_amount is not null then '<br>Transaction Amount: ' || transaction_amount else '' end || case when remarks_of_csa_customer is not null then '<br>CSA Remarks: ' || remarks_of_csa_customer else '' end || case when date_of_birth is not null then '<br>Birth Date: ' || date_of_birth::date else '' end || case when account_balance is not null then '<br>Account Balance: ' || account_balance else '' end || case when escalate_to is not null then '<br>Escalate/Forward To: ' || (select first_name from auth_user where id = escalate_to) else '' end || case when transaction_type is not null then '<br>Transaction Type: ' || transaction_type else '' end || '' poes ,coalesce(to_char((extract(epoch FROM sla::interval) || ' second')::interval, 'HH24:MI:SS'),'') tht,coalesce(note,'') note ,case when comment_text is null then '' when other_comment is not null or other_comment != '' then comment_text || '. ' || other_comment else comment_text end as comments from t"
            else:
                query = "with t as( select * from project_data_complain WHERE pin_id = ANY (SELECT user_id FROM usermodule_usermoduleprofile WHERE region_id :: text LIKE '" + str(region) + "' AND branch_id :: text LIKE '" + str(branch) + "' AND user_id :: text LIKE '"+str(brac_agent)+"') AND received_time BETWEEN '" + str(request_from_date) + "' AND '" + str(request_to_date) + "' AND ticket_close_time BETWEEN '" + str(reply_from_date) + "' AND '" + str(reply_to_date) + "' AND service_type LIKE '"+str(service_type)+"' and execution_status like '"+str(action)+"' AND reply_by :: text LIKE '"+str(bkash_agent)+"' order by ticket_id) select ROW_NUMBER () OVER () serial_no,ticket_id,account_no,service_type,execution_status category,(select (select name from project_data_region where id = region_id limit 1)region_id from usermodule_usermoduleprofile where user_id = pin_id limit 1) region,(select (select name from project_data_branch where id = usermodule_usermoduleprofile.branch_id::int limit 1)branch_id from usermodule_usermoduleprofile where user_id = pin_id limit 1) branch ,(select username from auth_user where id = pin_id limit 1)csa_agent_id,(select first_name from auth_user where id = pin_id limit 1) csa_agent_name,to_char(calculated_sla_time,'dd-MON-yyyy hh12:mi AM') request_date_time,coalesce(to_char(ticket_close_time,'dd-MON-yyyy hh12:mi AM'),'') reply_date_time ,coalesce((select username from auth_user where id = reply_by::int limit 1),'')bkash_agent_id,coalesce((select first_name from auth_user where id = reply_by::int limit 1),'') bkash_agent_name ,case when id_no is not null then 'NID: ' || id_no else '' end || case when transaction_id is not null then '<br>Transaction ID: ' || transaction_id else '' end || case when transaction_date_time is not null then '<br>Transaction Date: ' || transaction_date_time::date else '' end || case when transaction_amount is not null then '<br>Transaction Amount: ' || transaction_amount else '' end || case when remarks_of_csa_customer is not null then '<br>CSA Remarks: ' || remarks_of_csa_customer else '' end || case when date_of_birth is not null then '<br>Birth Date: ' || date_of_birth::date else '' end || case when account_balance is not null then '<br>Account Balance: ' || account_balance else '' end || case when escalate_to is not null then '<br>Escalate/Forward To: ' || (select first_name from auth_user where id = escalate_to) else '' end || case when transaction_type is not null then '<br>Transaction Type: ' || transaction_type else '' end || '' poes ,coalesce(to_char((extract(epoch FROM sla::interval) || ' second')::interval, 'HH24:MI:SS'),'') tht,coalesce(note,'') note ,case when comment_text is null then '' when other_comment is not null or other_comment != '' then comment_text || '. ' || other_comment else comment_text end as comments from t"
        else:
            query = "with t as( select * from project_data_complain WHERE pin_id = ANY (SELECT user_id FROM usermodule_usermoduleprofile WHERE region_id :: text LIKE '" + str(region) + "' AND branch_id :: text LIKE '" + str(branch) + "' AND user_id :: text LIKE '"+str(brac_agent)+"') AND received_time BETWEEN '" + str(request_from_date) + "' AND '" + str(request_to_date) + "' AND ticket_close_time BETWEEN '" + str(reply_from_date) + "' AND '" + str(reply_to_date) + "' AND service_type LIKE '"+str(service_type)+"' and execution_status like '"+str(action)+"' AND reply_by :: text LIKE '"+str(bkash_agent)+"' order by ticket_id) select ROW_NUMBER () OVER () serial_no,ticket_id,account_no,service_type,execution_status category,(select (select name from project_data_region where id = region_id limit 1)region_id from usermodule_usermoduleprofile where user_id = pin_id limit 1) region,(select (select name from project_data_branch where id = usermodule_usermoduleprofile.branch_id::int limit 1)branch_id from usermodule_usermoduleprofile where user_id = pin_id limit 1) branch ,(select username from auth_user where id = pin_id limit 1)csa_agent_id,(select first_name from auth_user where id = pin_id limit 1) csa_agent_name,to_char(calculated_sla_time,'dd-MON-yyyy hh12:mi AM') request_date_time,coalesce(to_char(ticket_close_time,'dd-MON-yyyy hh12:mi AM'),'') reply_date_time ,coalesce((select username from auth_user where id = reply_by::int limit 1),'')bkash_agent_id,coalesce((select first_name from auth_user where id = reply_by::int limit 1),'') bkash_agent_name ,case when id_no is not null then 'NID: ' || id_no else '' end || case when transaction_id is not null then '<br>Transaction ID: ' || transaction_id else '' end || case when transaction_date_time is not null then '<br>Transaction Date: ' || transaction_date_time::date else '' end || case when transaction_amount is not null then '<br>Transaction Amount: ' || transaction_amount else '' end || case when remarks_of_csa_customer is not null then '<br>CSA Remarks: ' || remarks_of_csa_customer else '' end || case when date_of_birth is not null then '<br>Birth Date: ' || date_of_birth::date else '' end || case when account_balance is not null then '<br>Account Balance: ' || account_balance else '' end || case when escalate_to is not null then '<br>Escalate/Forward To: ' || (select first_name from auth_user where id = escalate_to) else '' end || case when transaction_type is not null then '<br>Transaction Type: ' || transaction_type else '' end || '' poes ,coalesce(to_char((extract(epoch FROM sla::interval) || ' second')::interval, 'HH24:MI:SS'),'') tht,coalesce(note,'') note ,case when comment_text is null then '' when other_comment is not null or other_comment != '' then comment_text || '. ' || other_comment else comment_text end as comments from t"
        data = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
        return HttpResponse(data)
    else:
        if not df.empty:
            role_id = df.role_id.tolist()[0]
            # bkash agent
            if role_id == 3:
                query = """ with t as( select * from project_data_complain WHERE pin_id = ANY (SELECT user_id FROM usermodule_usermoduleprofile WHERE region_id :: text LIKE '""" + str(region) + """' AND branch_id :: text LIKE '""" + str(branch) + """' AND user_id :: text LIKE '"""+str(brac_agent)+"""') AND received_time BETWEEN '""" + str(request_from_date) + """' AND '""" + str(request_to_date) + """' AND ticket_close_time BETWEEN '""" + str(reply_from_date) + """' AND '""" + str(reply_to_date) + """' AND service_type LIKE '"""+str(service_type)+"""' and execution_status like '"""+str(action)+"""' AND reply_by :: text LIKE '"""+ str(user_id) +"""' order by ticket_id) select ROW_NUMBER () OVER () as "Serial No.",ticket_id as "Ticket ID",account_no as "Account No",service_type as "Service Type",execution_status as "Category",(select (select name from project_data_region where id = region_id limit 1)region_id from usermodule_usermoduleprofile where user_id = pin_id limit 1) as "Region(of CSA)",(select (select name from project_data_branch where id = usermodule_usermoduleprofile.branch_id::int limit 1)branch_id from usermodule_usermoduleprofile where user_id = pin_id limit 1) as "Branch(of CSA)" ,(select username from auth_user where id = pin_id limit 1) as "Request by: Emp ID (CSA Agent)" ,(select first_name from auth_user where id = pin_id limit 1) as "Request By: Name (CSA Agent)" ,to_char(calculated_sla_time,'dd-MON-yyyy hh12:mi AM') as "Request Date & Time" ,coalesce(to_char(ticket_close_time,'dd-MON-yyyy hh12:mi AM'),'') as "Reply Date & Time" ,coalesce((select username from auth_user where id = reply_by::int limit 1),'') as "Reply by: Emp ID (bKash Employee)" ,coalesce((select first_name from auth_user where id = reply_by::int limit 1),'') as "Reply By: Name (bKash Employee)" ,case when id_no is not null then 'NID: ' || id_no else '' end || case when transaction_id is not null then '\nTransaction ID: ' || transaction_id else '' end || case when transaction_date_time is not null then '\nTransaction Date: ' || transaction_date_time::date else '' end || case when transaction_amount is not null then '\nTransaction Amount: ' || transaction_amount else '' end || case when remarks_of_csa_customer is not null then '\nCSA Remarks: ' || remarks_of_csa_customer else '' end || case when date_of_birth is not null then '\nBirth Date: ' || date_of_birth::date else '' end || case when account_balance is not null then '\nAccount Balance: ' || account_balance else '' end || case when escalate_to is not null then '\nEscalate/Forward To: ' || (select first_name from auth_user where id = escalate_to) else '' end || case when transaction_type is not null then '\nTransaction Type: ' || transaction_type else '' end || '' as "POEs (of a ticket/form of that ticket)" ,coalesce(to_char((extract(epoch FROM sla::interval) || ' second')::interval, 'HH24:MI:SS'),'') as "THT",coalesce(note,'') as "Note (Forward/ Escalate)" ,case when comment_text is null then '' when other_comment is not null or other_comment != '' then comment_text || '. ' || other_comment else comment_text end as "Comments (Solved/Closed/Correction Needed)" from t """
            else:
                query = """ with t as( select * from project_data_complain WHERE pin_id = ANY (SELECT user_id FROM usermodule_usermoduleprofile WHERE region_id :: text LIKE '""" + str(region) + """' AND branch_id :: text LIKE '""" + str(branch) + """' AND user_id :: text LIKE '"""+str(brac_agent)+"""') AND received_time BETWEEN '""" + str(request_from_date) + """' AND '""" + str(request_to_date) + """' AND ticket_close_time BETWEEN '""" + str(reply_from_date) + """' AND '""" + str(reply_to_date) + """' AND service_type LIKE '"""+str(service_type)+"""' and execution_status like '"""+str(action)+"""' AND reply_by :: text LIKE '"""+ str(bkash_agent) +"""' order by ticket_id) select ROW_NUMBER () OVER () as "Serial No.",ticket_id as "Ticket ID",account_no as "Account No",service_type as "Service Type",execution_status as "Category",(select (select name from project_data_region where id = region_id limit 1)region_id from usermodule_usermoduleprofile where user_id = pin_id limit 1) as "Region(of CSA)",(select (select name from project_data_branch where id = usermodule_usermoduleprofile.branch_id::int limit 1)branch_id from usermodule_usermoduleprofile where user_id = pin_id limit 1) as "Branch(of CSA)" ,(select username from auth_user where id = pin_id limit 1) as "Request by: Emp ID (CSA Agent)" ,(select first_name from auth_user where id = pin_id limit 1) as "Request By: Name (CSA Agent)" ,to_char(calculated_sla_time,'dd-MON-yyyy hh12:mi AM') as "Request Date & Time" ,coalesce(to_char(ticket_close_time,'dd-MON-yyyy hh12:mi AM'),'') as "Reply Date & Time" ,coalesce((select username from auth_user where id = reply_by::int limit 1),'') as "Reply by: Emp ID (bKash Employee)" ,coalesce((select first_name from auth_user where id = reply_by::int limit 1),'') as "Reply By: Name (bKash Employee)" ,case when id_no is not null then 'NID: ' || id_no else '' end || case when transaction_id is not null then '\nTransaction ID: ' || transaction_id else '' end || case when transaction_date_time is not null then '\nTransaction Date: ' || transaction_date_time::date else '' end || case when transaction_amount is not null then '\nTransaction Amount: ' || transaction_amount else '' end || case when remarks_of_csa_customer is not null then '\nCSA Remarks: ' || remarks_of_csa_customer else '' end || case when date_of_birth is not null then '\nBirth Date: ' || date_of_birth::date else '' end || case when account_balance is not null then '\nAccount Balance: ' || account_balance else '' end || case when escalate_to is not null then '\nEscalate/Forward To: ' || (select first_name from auth_user where id = escalate_to) else '' end || case when transaction_type is not null then '\nTransaction Type: ' || transaction_type else '' end || '' as "POEs (of a ticket/form of that ticket)" ,coalesce(to_char((extract(epoch FROM sla::interval) || ' second')::interval, 'HH24:MI:SS'),'') as "THT",coalesce(note,'') as "Note (Forward/ Escalate)" ,case when comment_text is null then '' when other_comment is not null or other_comment != '' then comment_text || '. ' || other_comment else comment_text end as "Comments (Solved/Closed/Correction Needed)" from t """
        else:
            query = """ with t as( select * from project_data_complain WHERE pin_id = ANY (SELECT user_id FROM usermodule_usermoduleprofile WHERE region_id :: text LIKE '""" + str(region) + """' AND branch_id :: text LIKE '""" + str(branch) + """' AND user_id :: text LIKE '"""+str(brac_agent)+"""') AND received_time BETWEEN '""" + str(request_from_date) + """' AND '""" + str(request_to_date) + """' AND ticket_close_time BETWEEN '""" + str(reply_from_date) + """' AND '""" + str(reply_to_date) + """' AND service_type LIKE '"""+str(service_type)+"""' and execution_status like '"""+str(action)+"""' AND reply_by :: text LIKE '"""+ str(bkash_agent) +"""' order by ticket_id) select ROW_NUMBER () OVER () as "Serial No.",ticket_id as "Ticket ID",account_no as "Account No",service_type as "Service Type",execution_status as "Category",(select (select name from project_data_region where id = region_id limit 1)region_id from usermodule_usermoduleprofile where user_id = pin_id limit 1) as "Region(of CSA)",(select (select name from project_data_branch where id = usermodule_usermoduleprofile.branch_id::int limit 1)branch_id from usermodule_usermoduleprofile where user_id = pin_id limit 1) as "Branch(of CSA)" ,(select username from auth_user where id = pin_id limit 1) as "Request by: Emp ID (CSA Agent)" ,(select first_name from auth_user where id = pin_id limit 1) as "Request By: Name (CSA Agent)" ,to_char(calculated_sla_time,'dd-MON-yyyy hh12:mi AM') as "Request Date & Time" ,coalesce(to_char(ticket_close_time,'dd-MON-yyyy hh12:mi AM'),'') as "Reply Date & Time" ,coalesce((select username from auth_user where id = reply_by::int limit 1),'') as "Reply by: Emp ID (bKash Employee)" ,coalesce((select first_name from auth_user where id = reply_by::int limit 1),'') as "Reply By: Name (bKash Employee)" ,case when id_no is not null then 'NID: ' || id_no else '' end || case when transaction_id is not null then '\nTransaction ID: ' || transaction_id else '' end || case when transaction_date_time is not null then '\nTransaction Date: ' || transaction_date_time::date else '' end || case when transaction_amount is not null then '\nTransaction Amount: ' || transaction_amount else '' end || case when remarks_of_csa_customer is not null then '\nCSA Remarks: ' || remarks_of_csa_customer else '' end || case when date_of_birth is not null then '\nBirth Date: ' || date_of_birth::date else '' end || case when account_balance is not null then '\nAccount Balance: ' || account_balance else '' end || case when escalate_to is not null then '\nEscalate/Forward To: ' || (select first_name from auth_user where id = escalate_to) else '' end || case when transaction_type is not null then '\nTransaction Type: ' || transaction_type else '' end || '' as "POEs (of a ticket/form of that ticket)" ,coalesce(to_char((extract(epoch FROM sla::interval) || ' second')::interval, 'HH24:MI:SS'),'') as "THT",coalesce(note,'') as "Note (Forward/ Escalate)" ,case when comment_text is null then '' when other_comment is not null or other_comment != '' then comment_text || '. ' || other_comment else comment_text end as "Comments (Solved/Closed/Correction Needed)" from t """
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        writer = pandas.ExcelWriter("static/media/uploaded_files/output.xls")
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        writer.save()
        f = open('static/media/uploaded_files/output.xls', 'r')
        response = HttpResponse(f, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=Account Report.xls'
        return response


def report_bkash_activity(request):
    for_agents = "select id,first_name,username from auth_user where id = any(select user_id from usermodule_usermoduleprofile where account_type_id = 3)"
    df = pandas.DataFrame()
    df = pandas.read_sql(for_agents,connection)
    agents = zip(df.id.tolist(),df.first_name.tolist())
    agents_id = zip(df.id.tolist(),df.username.tolist())
    return render(request,'bkashmodule/report_bkash_activity.html', {'reports': 'reports', 'activity': 'activity','agents':agents,'agents_id':agents_id})

@csrf_exempt
def get_bkash_activity_report(request):
    login_from_date = request.POST.get('login_from_date')
    login_to_date = request.POST.get('login_to_date')
    logout_from_date = request.POST.get('logout_from_date')
    logout_to_date = request.POST.get('logout_to_date')
    agent = request.POST.get('agent')
    agent_id = request.POST.get('agent_id')
    stat = request.POST.get('stat')
    user_id = request.user.id
    role_check_query = "select role_id from usermodule_userrolemap where user_id = (select id from usermodule_usermoduleprofile where user_id = " + str(user_id) + ")"
    df = pandas.DataFrame()
    df = pandas.read_sql(role_check_query, connection)
    if stat == '0':
        if not df.empty:
            role_id = df.role_id.tolist()[0]
            # bkash agent
            if role_id == 3:
                query = "select(select username from auth_user where id = user_id)emp_id,(select first_name from auth_user where id = user_id) emp_name,to_char(login_time,'YYYY-MM-DD HH24:MI:SS') login_time,to_char(logout_time,'YYYY-MM-DD HH24:MI:SS') logout_time  from usermodule_useraccesslog where user_id = any(select user_id from usermodule_usermoduleprofile where account_type_id = 3) and user_id = " + str(user_id) + " and login_time between '" + str(login_from_date) + "' and '" + str(login_to_date) + "' and logout_time between '" + str(logout_from_date) + "' and '" + str(logout_to_date) + "'"
            else:
                query = "select(select username from auth_user where id = user_id)emp_id,(select first_name from auth_user where id = user_id) emp_name,to_char(login_time,'YYYY-MM-DD HH24:MI:SS') login_time,to_char(logout_time,'YYYY-MM-DD HH24:MI:SS') logout_time from usermodule_useraccesslog where user_id = any(select user_id from usermodule_usermoduleprofile where account_type_id = 3 and user_id::text like '"+str(agent)+"' and user_id::text like '"+str(agent_id)+"') and login_time between '" + str(login_from_date) + "' and '" + str(login_to_date) + "' and logout_time between '" + str(logout_from_date) + "' and '" + str(logout_to_date) + "'"
        else:
            query = "select(select username from auth_user where id = user_id)emp_id,(select first_name from auth_user where id = user_id) emp_name,to_char(login_time,'YYYY-MM-DD HH24:MI:SS') login_time,to_char(logout_time,'YYYY-MM-DD HH24:MI:SS') logout_time from usermodule_useraccesslog where user_id = any(select user_id from usermodule_usermoduleprofile where account_type_id = 3 and user_id::text like '"+str(agent)+"' and user_id::text like '"+str(agent_id)+"') and login_time between '" + str(login_from_date) + "' and '" + str(login_to_date) + "' and logout_time between '" + str(logout_from_date) + "' and '" + str(logout_to_date) + "'"
        data = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
        return HttpResponse(data)
    else:
        if not df.empty:
            role_id = df.role_id.tolist()[0]
            # bkash agent
            if role_id == 3:
                query = "select(select username from auth_user where id = user_id) as \"Employee ID\",(select first_name from auth_user where id = user_id) as \"Employee Name\",to_char(login_time,'YYYY-MM-DD HH24:MI:SS') as \"Login Time\",to_char(logout_time,'YYYY-MM-DD HH24:MI:SS') as \"Logout Time\"  from usermodule_useraccesslog where user_id = any(select user_id from usermodule_usermoduleprofile where account_type_id = 3) and user_id = " + str(user_id) + " and login_time between '" + str(login_from_date) + "' and '" + str(login_to_date) + "' and logout_time between '" + str(logout_from_date) + "' and '" + str(logout_to_date) + "'"
            else:
                query = "select(select username from auth_user where id = user_id) as \"Employee ID\",(select first_name from auth_user where id = user_id) as \"Employee Name\",to_char(login_time,'YYYY-MM-DD HH24:MI:SS') as \"Login Time\",to_char(logout_time,'YYYY-MM-DD HH24:MI:SS') as \"Logout Time\" from usermodule_useraccesslog where user_id = any(select user_id from usermodule_usermoduleprofile where account_type_id = 3 and user_id::text like '"+str(agent)+"' and user_id::text like '"+str(agent_id)+"') and login_time between '" + str(login_from_date) + "' and '" + str(login_to_date) + "' and logout_time between '" + str(logout_from_date) + "' and '" + str(logout_to_date) + "'"
        else:
            query = "select(select username from auth_user where id = user_id) as \"Employee ID\",(select first_name from auth_user where id = user_id)  as \"Employee Name\",to_char(login_time,'YYYY-MM-DD HH24:MI:SS') as \"Login Time\",to_char(logout_time,'YYYY-MM-DD HH24:MI:SS') as \"Logout Time\" from usermodule_useraccesslog where user_id = any(select user_id from usermodule_usermoduleprofile where account_type_id = 3 and user_id::text like '"+str(agent)+"' and user_id::text like '"+str(agent_id)+"') and login_time between '" + str(login_from_date) + "' and '" + str(login_to_date) + "' and logout_time between '" + str(logout_from_date) + "' and '" + str(logout_to_date) + "'"
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        writer = pandas.ExcelWriter("static/media/uploaded_files/output.xls")
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        writer.save()
        f = open('static/media/uploaded_files/output.xls', 'r')
        response = HttpResponse(f, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=bKash Agent Activity Report.xls'
        return response

def report_brac_performance(request):
    for_agents = "select id,first_name,username from auth_user where id = any(select user_id from usermodule_usermoduleprofile where account_type_id = 2)"
    df = pandas.DataFrame()
    df = pandas.read_sql(for_agents,connection)
    agents = zip(df.id.tolist(),df.first_name.tolist())
    agents_id = zip(df.id.tolist(),df.username.tolist())
    for_region = "select * from project_data_region"
    df = pandas.DataFrame()
    df = pandas.read_sql(for_region, connection)
    region = zip(df.id.tolist(), df.name.tolist())
    return render(request,'bkashmodule/report_brac_performance.html', {'reports': 'reports', 'agent_performance': 'agent_performance','agents':agents,'agents_id':agents_id,'region':region})


def get_brac_performance_report(request):
    request_from_date = request.POST.get('request_from_date')
    request_to_date = request.POST.get('request_to_date')
    reply_from_date = request.POST.get('reply_from_date')
    reply_to_date = request.POST.get('reply_to_date')
    agent = request.POST.get('agent')
    agent_id = request.POST.get('agent_id')
    region = request.POST.get('region')
    branch = request.POST.get('branch')
    stat = request.POST.get('stat')
    user_id = request.user.id
    role_check_query = "select role_id from usermodule_userrolemap where user_id = (select id from usermodule_usermoduleprofile where user_id = " + str(user_id) + ")"
    df = pandas.DataFrame()
    df = pandas.read_sql(role_check_query, connection)
    if stat == '0':
        if not df.empty:
            role_id = df.role_id.tolist()[0]
            # bkash agent
            if role_id == 3:
                query = "WITH _mat AS(SELECT * FROM project_data_complain where pin_id = any(select user_id from usermodule_usermoduleprofile where region_id::text like '"+str(region)+"' and branch_id::text like '"+str(branch)+"')and pin_id::text like '"+str(agent)+"' and pin_id::text like '"+str(agent_id)+"' and reply_by = " + str(user_id) + " AND received_time BETWEEN '" + str(request_from_date) + "' AND '" + str(request_to_date) + "' AND ticket_close_time BETWEEN '" + str(reply_from_date) + "' AND '" + str(reply_to_date) + "' ), ful_req as( select distinct first_value(id)over(PARTITION by substring(ticket_id for length(ticket_id)-2) ORDER by ticket_id desc) id from _mat) ,solved AS (SELECT pin_id, count(distinct substring(ticket_id for length(ticket_id)-2 )) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) and id = any(select id from ful_req) group by pin_id), closed AS (SELECT pin_id, count(distinct substring(ticket_id for length(ticket_id)-2 )) closed_cnt FROM _mat WHERE execution_status = 'Closed' and id = any(select id from ful_req) GROUP BY pin_id) SELECT (SELECT username FROM auth_user WHERE id = solved.pin_id) emp_id, (SELECT first_name FROM auth_user WHERE id = solved.pin_id) AS emp_name, (SELECT (SELECT name FROM project_data_region WHERE id = region_id :: INT) FROM usermodule_usermoduleprofile WHERE user_id = solved.pin_id) region, (SELECT name FROM project_data_branch WHERE id = (SELECT branch_id FROM usermodule_usermoduleprofile WHERE user_id = solved.pin_id)) branch, coalesce(solved_cnt,0) + coalesce(closed_cnt,0) AS total_cnt, coalesce(solved_cnt,0)  AS solved_cnt, coalesce(closed_cnt,0) AS closed_cnt FROM solved full outer join closed on solved.pin_id = closed.pin_id GROUP BY solved.pin_id, solved_cnt, closed_cnt"
            else:
                query = "WITH _mat AS(SELECT * FROM project_data_complain where pin_id = any(select user_id from usermodule_usermoduleprofile where region_id::text like '"+str(region)+"' and branch_id::text like '"+str(branch)+"')and pin_id::text like '"+str(agent)+"' and pin_id::text like '"+str(agent_id)+"' AND received_time BETWEEN '" + str(request_from_date) + "' AND '" + str(request_to_date) + "' AND ticket_close_time BETWEEN '" + str(reply_from_date) + "' AND '" + str(reply_to_date) + "' ), ful_req as( select distinct first_value(id)over(PARTITION by substring(ticket_id for length(ticket_id)-2) ORDER by ticket_id desc) id from _mat) ,solved AS (SELECT pin_id, count(distinct substring(ticket_id for length(ticket_id)-2 )) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) and id = any(select id from ful_req) group by pin_id), closed AS (SELECT pin_id, count(distinct substring(ticket_id for length(ticket_id)-2 )) closed_cnt FROM _mat WHERE execution_status = 'Closed' and id = any(select id from ful_req) GROUP BY pin_id) SELECT (SELECT username FROM auth_user WHERE id = solved.pin_id) emp_id, (SELECT first_name FROM auth_user WHERE id = solved.pin_id) AS emp_name, (SELECT (SELECT name FROM project_data_region WHERE id = region_id :: INT) FROM usermodule_usermoduleprofile WHERE user_id = solved.pin_id) region, (SELECT name FROM project_data_branch WHERE id = (SELECT branch_id FROM usermodule_usermoduleprofile WHERE user_id = solved.pin_id)) branch, coalesce(solved_cnt,0) + coalesce(closed_cnt,0) AS total_cnt, coalesce(solved_cnt,0)  AS solved_cnt, coalesce(closed_cnt,0) AS closed_cnt FROM solved full outer join  closed on solved.pin_id = closed.pin_id GROUP BY solved.pin_id, solved_cnt, closed_cnt"
        else:
            query = "WITH _mat AS(SELECT * FROM project_data_complain where pin_id = any(select user_id from usermodule_usermoduleprofile where region_id::text like '"+str(region)+"' and branch_id::text like '"+str(branch)+"')and pin_id::text like '"+str(agent)+"' and pin_id::text like '"+str(agent_id)+"'  AND received_time BETWEEN '" + str(request_from_date) + "' AND '" + str(request_to_date) + "' AND ticket_close_time BETWEEN '" + str(reply_from_date) + "' AND '" + str(reply_to_date) + "' ), ful_req as( select distinct first_value(id)over(PARTITION by substring(ticket_id for length(ticket_id)-2) ORDER by ticket_id desc) id from _mat) ,solved AS (SELECT pin_id, count(distinct substring(ticket_id for length(ticket_id)-2 )) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) and id = any(select id from ful_req) group by pin_id), closed AS (SELECT pin_id, count(distinct substring(ticket_id for length(ticket_id)-2 )) closed_cnt FROM _mat WHERE execution_status = 'Closed' and id = any(select id from ful_req) GROUP BY pin_id) SELECT (SELECT username FROM auth_user WHERE id = solved.pin_id) emp_id, (SELECT first_name FROM auth_user WHERE id = solved.pin_id) AS emp_name, (SELECT (SELECT name FROM project_data_region WHERE id = region_id :: INT) FROM usermodule_usermoduleprofile WHERE user_id = solved.pin_id) region, (SELECT name FROM project_data_branch WHERE id = (SELECT branch_id FROM usermodule_usermoduleprofile WHERE user_id = solved.pin_id)) branch, coalesce(solved_cnt,0) + coalesce(closed_cnt,0) AS total_cnt, coalesce(solved_cnt,0) AS solved_cnt, coalesce(closed_cnt,0) AS closed_cnt FROM solved full outer join closed on solved.pin_id = closed.pin_id GROUP BY solved.pin_id, solved_cnt, closed_cnt"
            print(query)
        data = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
        return HttpResponse(data)
    else:
        if not df.empty:
            role_id = df.role_id.tolist()[0]
            # bkash agent
            if role_id == 3:
                query = "WITH _mat AS(SELECT * FROM project_data_complain where pin_id = any(select user_id from usermodule_usermoduleprofile where region_id::text like '"+str(region)+"' and branch_id::text like '"+str(branch)+"')and pin_id::text like '"+str(agent)+"' and pin_id::text like '"+str(agent_id)+"' and reply_by = " + str(user_id) + " AND received_time BETWEEN '" + str(request_from_date) + "' AND '" + str(request_to_date) + "' AND ticket_close_time BETWEEN '" + str(reply_from_date) + "' AND '" + str(reply_to_date) + "' ), ful_req as( select distinct first_value(id)over(PARTITION by substring(ticket_id for length(ticket_id)-2) ORDER by ticket_id desc) id from _mat) ,solved AS (SELECT pin_id, count(distinct substring(ticket_id for length(ticket_id)-2 )) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) and id = any(select id from ful_req) group by pin_id), closed AS (SELECT pin_id, count(distinct substring(ticket_id for length(ticket_id)-2 )) closed_cnt FROM _mat WHERE execution_status = 'Closed' and id = any(select id from ful_req) GROUP BY pin_id)  SELECT (select username from auth_user where id = solved.pin_id) as \"Employee ID\",(select first_name from auth_user where id = solved.pin_id) as \"Employee Name\", (select (select name from project_data_region where id = region_id::int) from usermodule_usermoduleprofile where user_id = solved.pin_id) as \"Region\", (select name from project_data_branch where id = (select branch_id from usermodule_usermoduleprofile where user_id = solved.pin_id)) as \"Branch\", coalesce(solved_cnt,0) + coalesce(closed_cnt,0)  as \"Customer Served\", coalesce(solved_cnt,0) as \"Solved\", coalesce(closed_cnt,0) as \"Closed\" FROM solved full outer join closed on solved.pin_id = closed.pin_id GROUP BY solved.pin_id, solved_cnt, closed_cnt"
            else:
                query = "WITH _mat AS(SELECT * FROM project_data_complain where pin_id = any(select user_id from usermodule_usermoduleprofile where region_id::text like '"+str(region)+"' and branch_id::text like '"+str(branch)+"')and pin_id::text like '"+str(agent)+"' and pin_id::text like '"+str(agent_id)+"' AND received_time BETWEEN '" + str(request_from_date) + "' AND '" + str(request_to_date) + "' AND ticket_close_time BETWEEN '" + str(reply_from_date) + "' AND '" + str(reply_to_date) + "' ), ful_req as( select distinct first_value(id)over(PARTITION by substring(ticket_id for length(ticket_id)-2) ORDER by ticket_id desc) id from _mat) ,solved AS (SELECT pin_id, count(distinct substring(ticket_id for length(ticket_id)-2 )) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) and id = any(select id from ful_req) group by pin_id), closed AS (SELECT pin_id, count(distinct substring(ticket_id for length(ticket_id)-2 )) closed_cnt FROM _mat WHERE execution_status = 'Closed' and id = any(select id from ful_req) GROUP BY pin_id)  SELECT (select username from auth_user where id = solved.pin_id) as \"Employee ID\",(select first_name from auth_user where id = solved.pin_id) as \"Employee Name\", (select (select name from project_data_region where id = region_id::int) from usermodule_usermoduleprofile where user_id = solved.pin_id) as \"Region\", (select name from project_data_branch where id = (select branch_id from usermodule_usermoduleprofile where user_id = solved.pin_id)) as \"Branch\", coalesce(solved_cnt,0) + coalesce(closed_cnt,0)  as \"Customer Served\", coalesce(solved_cnt,0) as \"Solved\", coalesce(closed_cnt,0) as \"Closed\" FROM solved full outer join closed on solved.pin_id = closed.pin_id GROUP BY solved.pin_id, solved_cnt, closed_cnt"
        else:
            query = "WITH _mat AS(SELECT * FROM project_data_complain where pin_id = any(select user_id from usermodule_usermoduleprofile where region_id::text like '"+str(region)+"' and branch_id::text like '"+str(branch)+"')and pin_id::text like '"+str(agent)+"' and pin_id::text like '"+str(agent_id)+"'  AND received_time BETWEEN '" + str(request_from_date) + "' AND '" + str(request_to_date) + "' AND ticket_close_time BETWEEN '" + str(reply_from_date) + "' AND '" + str(reply_to_date) + "' ), ful_req as( select distinct first_value(id)over(PARTITION by substring(ticket_id for length(ticket_id)-2) ORDER by ticket_id desc) id from _mat) ,solved AS (SELECT pin_id, count(distinct substring(ticket_id for length(ticket_id)-2 )) solved_cnt FROM _mat WHERE execution_status = ANY ( '{Solved,Correction Needed}' ) and id = any(select id from ful_req) group by pin_id), closed AS (SELECT pin_id, count(distinct substring(ticket_id for length(ticket_id)-2 )) closed_cnt FROM _mat WHERE execution_status = 'Closed' and id = any(select id from ful_req) GROUP BY pin_id)  SELECT (select username from auth_user where id = solved.pin_id) as \"Employee ID\",(select first_name from auth_user where id = solved.pin_id) as \"Employee Name\", (select (select name from project_data_region where id = region_id::int) from usermodule_usermoduleprofile where user_id = solved.pin_id) as \"Region\", (select name from project_data_branch where id = (select branch_id from usermodule_usermoduleprofile where user_id = solved.pin_id)) as \"Branch\", coalesce(solved_cnt,0) + coalesce(closed_cnt,0)  as \"Customer Served\", coalesce(solved_cnt,0) as \"Solved\", coalesce(closed_cnt,0) as \"Closed\" FROM solved full outer join closed on solved.pin_id = closed.pin_id GROUP BY solved.pin_id, solved_cnt, closed_cnt"
        df = pandas.DataFrame()
        df = pandas.read_sql(query, connection)
        writer = pandas.ExcelWriter("static/media/uploaded_files/output.xls")
        df.to_excel(writer, sheet_name='Sheet1', index=False)
        writer.save()
        f = open('static/media/uploaded_files/output.xls', 'r')
        response = HttpResponse(f, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=BRAC Agent Report.xls'
        return response

@csrf_exempt
def getBranches(request):
    region = request.POST.get('region')
    query = "select id,name from project_data_branch where region_id =  "+str(region)
    data = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return HttpResponse(data)



