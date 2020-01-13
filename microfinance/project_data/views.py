#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
from datetime import date, timedelta
import datetime
import random
import decimal
import calendar
import operator
from django.utils import timezone
from operator import truediv
from user_agents import parse
from django.shortcuts import render, render_to_response, get_object_or_404
from django.http import (HttpResponseRedirect, HttpResponse, Http404)
from django.core import serializers
from django.template import RequestContext, loader
from django.views.decorators.csrf import csrf_exempt

from django.contrib.sessions.models import Session
from django.contrib.auth import authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.utils.timezone import get_current_timezone, make_aware, utc
from django.utils.timezone import activate
from django.utils import formats
import time
from datetime import datetime, timedelta

from django.db import IntegrityError, connection
from django.db.models import Count, Q
from project_data.models import Complain, ComplainStatusLog, Branch, Notification, Region
from project_data.forms import ComplainForm, BranchForm, NotificationForm

from usermodule.models import UserModuleProfile, Organizations, UserSecurityCode, Task, TaskRolePermissionMap, \
    UserRoleMap, UserAccessLog
from usermodule.forms import TaskForm, TaskRolePermissionMapForm
from usermodule.helpers import BKASH_EXEC_ROLE_ID
from usermodule.views import admin_check,error_page

from project_data.helpers import send_push_msg
from microfinance.settings import WALLET_API_SECURITY_KEY, SMS_API_TOKEN, TIME_ZONE, USE_TZ
import xlwt
from collections import OrderedDict

# from urllib.parse import urlencode
# from urllib.request import Request, urlopen
import urllib
import urllib2
import decimal
import os
from django.core.files.storage import FileSystemStorage
from django.db.models import Q
from pyfcm import FCMNotification

push_service = FCMNotification(
    api_key="AIzaSyAjMh0NVF5SOE_U5xEgLKO6H9qwoCrr10Y")

def __db_commit_query(query):
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    cursor.close()

@csrf_exempt
def update_token(data):
    mac_address = data['mac_address']
    firebase_token = data['firebase_token']
    # check query if this mac addr exists
    check_query = "select id from user_device_map where mac_address = '"+str(mac_address)+"'"
    df = pandas.DataFrame()
    df = pandas.read_sql(check_query,connection)
    if df.empty:
        query = "INSERT INTO public.user_device_map( mac_address, firebase_token, created_at) VALUES ( '" + str(mac_address) + "', '" + str(firebase_token) + "', now())"
    else:
        id = df.id.tolist()[0]
        query = "update user_device_map set firebase_token='" + str(firebase_token) +  "', created_at = now() where mac_address = '" + str(mac_address) + "'"
    __db_commit_query(query)
    return HttpResponse(json.dumps('Token updated'), status=200)


def send_push_notification(mac_address,service_type,complain_id,status,comment,other_comment,customer_name):
    print(mac_address,service_type,complain_id,status,comment,other_comment,customer_name)
    query = "select firebase_token from user_device_map where mac_address = '"+str(mac_address)+"'"
    df = pandas.DataFrame()
    df = pandas.read_sql(query,connection)
    if df.empty:
        return HttpResponse(json.dumps('Token Not Found'), status=404)
    else:
        firebase_token = df.firebase_token.tolist()[0]
        registration_id = []

        registration_id.append(firebase_token)
        message_title = str(service_type) + ', ' + str(status)
        # print(comment )
        # print(other_comment)
        message_body = (comment + ', ' + other_comment).encode('utf-8').strip()+' for ' + str(customer_name) if len(other_comment) else comment.encode('utf-8').strip()+' for ' + str(customer_name)
        data_message = {
            "service_type": service_type,
            "title": message_title,
            "message": message_body,
            "service_id": complain_id
        }


        result = push_service.notify_multiple_devices(registration_ids=registration_id, data_message=data_message)
        if result['success']:
            return HttpResponse(json.dumps('Notification Sent Successfully '), status=200)
        else:
            return HttpResponse(json.dumps('Notification Sent Failed '), status=22)



# Create your views here.

def decimal_date_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        return obj
    raise TypeError

def datetime_handler(x):
    if isinstance(x, datetime):
        return x.isoformat()
    raise TypeError("Unknown type")


def index(request):
    send_push_msg(topic='/CSA/1/22222', payload="Test Payload")
    return HttpResponse("asdasdsad")


@login_required
def new_complain(request):
    context = RequestContext(request)
    start_time = (timezone.now() - timedelta(days=7)).date()
    end_time = (timezone.now() + timedelta(days=1)).date()
    complains = Complain.objects.none()  # filter(Q(received_time__range=(start_time, end_time)) & (
    # Q(execution_status='Read') | Q(execution_status='New'))).order_by("received_time")
    success = request.GET.get("status", False)
    locker = request.GET.get("locker", False)
    unlock = request.GET.get("unlock", False)
    branches = Branch.objects.filter(status='active')  # .order_by("pk")
    last_id = getLastIdInner()
    return render_to_response(
        'project_data/complain_list.html',
        {'complains': complains, 'complain_mgt': 'complain_mgt',
         'new_complain': 'new_complain', 'branches': branches,
         'page_header': 'New Requests', 'success': success,
         'locker': locker, 'unlock': unlock, 'last_id': last_id
         },
        context)


def reloadComplains(request):
    start_time = (timezone.now() - timedelta(days=7)).date().strftime('%Y-%m-%d')
    end_time = (timezone.now() + timedelta(days=1)).date().strftime('%Y-%m-%d')
    # print start_time
    # print end_time
    # complains = Complain.objects.filter(Q(received_time__range=(start_time, end_time)) & (Q(execution_status='Read') | Q(execution_status='New'))).order_by("received_time")
    # complains = Complain.objects.filter(Q(received_time__range=(start_time, end_time))).order_by("received_time")
    complain_query = "(SELECT ticket_id, To_char(received_time, 'Dy dd Mon YYYY HH24:MI') AS received_time, account_no, service_type, execution_status, transaction_id, To_char(transaction_date_time, 'Dy dd Mon YYYY HH24:MI') AS transaction_date_time,id FROM project_data_complain where execution_status = any('{Open,New,Corrected}') and received_time > '" + str(start_time) + "' and received_time < '" + end_time + "' order by received_time DESC) union all (select ticket_id,To_char(received_time, 'Dy dd Mon YYYY HH24:MI') AS received_time, account_no, service_type, execution_status, transaction_id, To_char(transaction_date_time, 'Dy dd Mon YYYY HH24:MI') AS transaction_date_time,id FROM project_data_complain where execution_status = any('{Escalate,Forward}') and escalate_to = '"+str(request.user.id)+"' and received_time > '" + str(start_time) + "' and received_time < '" + end_time + "' order by received_time DESC)"
    print(complain_query)
    complains = json.dumps(__db_fetch_values(complain_query), default=date_handler)

    return HttpResponse(complains)

@csrf_exempt
def getNewRequests(request):
    from_date           = str(request.POST.get('from_date')) + ' 00:00:00'
    to_date             = str(request.POST.get('to_date')) + ' 23:59:59'
    service_type        = request.POST.get('problem_type')
    branch              = request.POST.get('branch')
    execution_status    = request.POST.get('execution_status')
    user_id             = request.user.id

    role_check_query = "select role_id from usermodule_userrolemap where user_id = (select id from usermodule_usermoduleprofile where user_id = "+str(user_id)+")"
    df = pandas.DataFrame()
    df = pandas.read_sql(role_check_query,connection)

    if not df.empty:
        user_role = df.role_id.tolist()[0]
        # bkash agent
        if user_role == 3:
            query = "WITH rev AS( SELECT ( SELECT branch_id FROM usermodule_usermoduleprofile WHERE user_id = pin_id limit 1) branch_id, ticket_id, received_time, account_no, service_type, execution_status, transaction_id, transaction_date_time, id , case when ticket_close_time is null then to_char((getworkingtime(received_time,now()) || ' second') :: interval, 'HH24:MI:SS') else to_char((getworkingtime(received_time,ticket_close_time) || ' second' ) :: interval, 'HH24:MI:SS') end as sla, calculated_sla_time FROM project_data_complain WHERE execution_status = ANY ( '{Open,New,Corrected}') UNION ALL SELECT ( SELECT branch_id FROM usermodule_usermoduleprofile WHERE user_id = pin_id limit 1) branch_id, ticket_id, received_time, account_no, service_type, execution_status, transaction_id, transaction_date_time, id, case when ticket_close_time is null then to_char((getworkingtime(received_time,now()) || ' second' ) :: interval, 'HH24:MI:SS') else to_char((getworkingtime(received_time,ticket_close_time) || ' second' ) :: interval, 'HH24:MI:SS') end as sla, calculated_sla_time FROM project_data_complain WHERE execution_status = ANY ( '{Escalate,Forward}') AND escalate_to = '" + str( user_id) + "') SELECT ticket_id, to_char(received_time, 'Dy dd Mon YYYY HH24:MI') AS received_time, account_no, service_type, execution_status, COALESCE(transaction_id::text,'') transaction_id, COALESCE(transaction_date_time::text,'') transaction_date_time, sla, id FROM rev WHERE execution_status LIKE '" + str( execution_status) + "' AND received_time::date BETWEEN '" + str(from_date) + "' AND '" + str( to_date) + "' AND service_type LIKE '" + str(service_type) + "' AND branch_id::text LIKE '" + str( branch) + "' ORDER BY received_time"
            data = json.dumps(__db_fetch_values_dict(query), default=date_handler)
            cnt_query = " WITH t AS(SELECT * FROM project_data_complain WHERE execution_status LIKE '"+str(execution_status)+"' AND received_time :: DATE BETWEEN '"+str(from_date)+"' AND '"+str(to_date)+"' AND service_type LIKE '"+str(service_type)+"' AND pin_id IN (SELECT user_id FROM usermodule_usermoduleprofile WHERE branch_id :: text LIKE '"+str(branch)+"')) , new_correct AS (SELECT Count(*) cnt_new FROM t WHERE execution_status = ANY ( '{New,Corrected}')), open_cnt AS (SELECT Count(*) cnt_open FROM t WHERE execution_status = 'Open' AND locker_id = "+str(user_id)+"), forwarded_cnt AS (SELECT Count(*) cnt_forward FROM t WHERE execution_status = 'Forward' AND reply_by = "+str(user_id)+"), escalated_cnt AS (SELECT Count(*) cnt_escalate FROM t WHERE execution_status = 'Escalate' AND escalate_to = "+str(user_id)+"), tot AS (SELECT Count(*) tot FROM t WHERE execution_status = ANY ( '{Solved,Closed,Correction Needed}' ) AND reply_by = "+str(user_id)+"), total_solved_cnt AS (SELECT *, tot cnt_solved FROM new_correct, open_cnt, forwarded_cnt, escalated_cnt, tot), aht_table AS (WITH a AS (SELECT Coalesce(To_char(( ( SUM(Extract( epoch FROM sla::interval) :: INT) / cnt_solved ) || ' second' ) :: interval, 'HH24:MI:SS') , '00:00:00' ) aht, Coalesce(To_char(( ( SUM(Extract( epoch FROM sla::interval + ( csa_ticket_close_time - csa_ticket_open_time ) ) :: INT) / cnt_solved ) || ' second' ) :: interval, 'HH24:MI:SS') , '00:00:00' ) awt FROM t, total_solved_cnt WHERE cnt_solved > 0 AND reply_by = "+str(user_id)+" GROUP BY cnt_solved) SELECT aht, awt FROM a) SELECT *, cnt_solved cnt_total FROM total_solved_cnt, aht_table"
        # bkash manager
        elif user_role == 4:
            query = "WITH rev AS( SELECT ( SELECT branch_id FROM usermodule_usermoduleprofile WHERE user_id = pin_id limit 1) branch_id, ticket_id, received_time, account_no, service_type, execution_status, transaction_id, transaction_date_time, id , case when ticket_close_time is null then to_char((getworkingtime(received_time,now()) || ' second') :: interval, 'HH24:MI:SS') else to_char((getworkingtime(received_time,ticket_close_time) || ' second' ) :: interval, 'HH24:MI:SS') end as sla, calculated_sla_time FROM project_data_complain WHERE execution_status = ANY ( '{Open,New,Corrected}') UNION ALL SELECT ( SELECT branch_id FROM usermodule_usermoduleprofile WHERE user_id = pin_id limit 1) branch_id, ticket_id, received_time, account_no, service_type, execution_status, transaction_id, transaction_date_time, id, case when ticket_close_time is null then to_char((getworkingtime(received_time,now()) || ' second' ) :: interval, 'HH24:MI:SS') else to_char((getworkingtime(received_time,ticket_close_time) || ' second' ) :: interval, 'HH24:MI:SS') end as sla, calculated_sla_time FROM project_data_complain WHERE execution_status = ANY ( '{Escalate,Forward}') AND escalate_to = '" + str( user_id) + "') SELECT ticket_id, to_char(received_time, 'Dy dd Mon YYYY HH24:MI') AS received_time, account_no, service_type, execution_status, COALESCE(transaction_id::text,'') transaction_id, COALESCE(transaction_date_time::text,'') transaction_date_time, sla, id FROM rev WHERE execution_status LIKE '" + str( execution_status) + "' AND received_time::date BETWEEN '" + str(from_date) + "' AND '" + str( to_date) + "' AND service_type LIKE '" + str(service_type) + "' AND branch_id::text LIKE '" + str( branch) + "' ORDER BY received_time"
            data = json.dumps(__db_fetch_values_dict(query), default=date_handler)
            cnt_query = "WITH t AS(SELECT * FROM project_data_complain WHERE execution_status LIKE '"+str(execution_status)+"' AND received_time :: DATE BETWEEN '"+str(from_date)+"' AND '"+str(to_date)+"' AND service_type LIKE '"+str(service_type)+"' AND pin_id IN (SELECT user_id FROM usermodule_usermoduleprofile WHERE branch_id :: text LIKE '"+str(branch)+"')) , new_correct AS (SELECT Count(*) cnt_new FROM t WHERE execution_status = ANY ( '{New,Corrected}')), open_cnt AS (SELECT Count(*) cnt_open FROM t WHERE execution_status = 'Open'), forwarded_cnt AS (SELECT Count(*) cnt_forward FROM t WHERE execution_status = 'Forward'), escalated_cnt AS (SELECT Count(*) cnt_escalate FROM t WHERE execution_status = 'Escalate'), tot AS (SELECT Count(*) tot FROM t WHERE execution_status = ANY ( '{Solved,Closed,Correction Needed}' )), total_solved_cnt AS (SELECT *, tot cnt_solved FROM new_correct, open_cnt, forwarded_cnt, escalated_cnt, tot), aht_table AS (WITH a AS (SELECT Coalesce(To_char(( ( SUM(Extract( epoch FROM sla::interval) :: INT) / cnt_solved ) || ' second' ) :: interval, 'HH24:MI:SS') , '00:00:00' ) aht, Coalesce(To_char(( ( SUM(Extract( epoch FROM sla::interval + ( csa_ticket_close_time - csa_ticket_open_time ) ) :: INT) / cnt_solved ) || ' second' ) :: interval, 'HH24:MI:SS') , '00:00:00' ) awt FROM t, total_solved_cnt WHERE cnt_solved > 0 GROUP BY cnt_solved) SELECT aht, awt FROM a) SELECT *, cnt_solved cnt_total FROM total_solved_cnt, aht_table "
    else:
        query = "WITH rev AS( SELECT ( SELECT branch_id FROM usermodule_usermoduleprofile WHERE user_id = pin_id limit 1) branch_id, ticket_id, received_time, account_no, service_type, execution_status, transaction_id, transaction_date_time, id , case when ticket_close_time is null then to_char((getworkingtime(received_time,now()) || ' second') :: interval, 'HH24:MI:SS') else to_char((getworkingtime(received_time,ticket_close_time) || ' second' ) :: interval, 'HH24:MI:SS') end as sla, calculated_sla_time FROM project_data_complain WHERE execution_status = ANY ( '{Open,New,Corrected}') UNION ALL SELECT ( SELECT branch_id FROM usermodule_usermoduleprofile WHERE user_id = pin_id limit 1) branch_id, ticket_id, received_time, account_no, service_type, execution_status, transaction_id, transaction_date_time, id, case when ticket_close_time is null then to_char((getworkingtime(received_time,now()) || ' second' ) :: interval, 'HH24:MI:SS') else to_char((getworkingtime(received_time,ticket_close_time) || ' second' ) :: interval, 'HH24:MI:SS') end as sla, calculated_sla_time FROM project_data_complain WHERE execution_status = ANY ( '{Escalate,Forward}') ) SELECT ticket_id, to_char(received_time, 'Dy dd Mon YYYY HH24:MI') AS received_time, account_no, service_type, execution_status, COALESCE(transaction_id::text,'') transaction_id, COALESCE(transaction_date_time::text,'') transaction_date_time, sla, id FROM rev WHERE execution_status LIKE '" + str( execution_status) + "' AND received_time::date BETWEEN '" + str(from_date) + "' AND '" + str( to_date) + "' AND service_type LIKE '" + str(service_type) + "' AND branch_id::text LIKE '" + str( branch) + "' ORDER BY received_time"
        data = json.dumps(__db_fetch_values_dict(query), default=date_handler)
        cnt_query = "WITH t AS(SELECT * FROM project_data_complain WHERE execution_status LIKE '"+str(execution_status)+"' AND received_time :: DATE BETWEEN '"+str(from_date)+"' AND '"+str(to_date)+"' AND service_type LIKE '"+str(service_type)+"' AND pin_id IN (SELECT user_id FROM usermodule_usermoduleprofile WHERE branch_id :: text LIKE '"+str(branch)+"')) , new_correct AS (SELECT Count(*) cnt_new FROM t WHERE execution_status = ANY ( '{New,Corrected}')), open_cnt AS (SELECT Count(*) cnt_open FROM t WHERE execution_status = 'Open'), forwarded_cnt AS (SELECT Count(*) cnt_forward FROM t WHERE execution_status = 'Forward'), escalated_cnt AS (SELECT Count(*) cnt_escalate FROM t WHERE execution_status = 'Escalate'), tot AS (SELECT Count(*) tot FROM t WHERE execution_status = ANY ( '{Solved,Closed,Correction Needed}' )), total_solved_cnt AS (SELECT *, tot cnt_solved FROM new_correct, open_cnt, forwarded_cnt, escalated_cnt, tot), aht_table AS (WITH a AS (SELECT Coalesce(To_char(( ( SUM(Extract( epoch FROM sla::interval) :: INT) / cnt_solved ) || ' second' ) :: interval, 'HH24:MI:SS') , '00:00:00' ) aht, Coalesce(To_char(( ( SUM(Extract( epoch FROM sla::interval + ( csa_ticket_close_time - csa_ticket_open_time ) ) :: INT) / cnt_solved ) || ' second' ) :: interval, 'HH24:MI:SS') , '00:00:00' ) awt FROM t, total_solved_cnt WHERE cnt_solved > 0 GROUP BY cnt_solved) SELECT aht, awt FROM a) SELECT *, cnt_solved cnt_total FROM total_solved_cnt, aht_table "
    print(query)
    print("******************")
    print(cnt_query)
    cnt_data = json.dumps(__db_fetch_values_dict(cnt_query), default=date_handler)
    return HttpResponse( json.dumps({'data':data,'cnt_data':cnt_data}, default=date_handler))


@login_required
def all_complain(request):
    context = RequestContext(request)
    start_time = (timezone.now() - timedelta(days=7)).date()
    end_time = (timezone.now() + timedelta(days=1)).date()

    # complains = Complain.objects.filter().order_by("-pk")
    complains = Complain.objects.filter(Q(received_time__range=(start_time, end_time)) & (Q(execution_status='Solved') | Q(execution_status='Closed')  | Q(execution_status='Closed'))).order_by("received_time")
    branches = Branch.objects.filter(status='active').order_by("name")
    # print ('timezone::',timezone.now())
    activate(TIME_ZONE)
    # print TIME_ZONE
    # print ('timezone::',timezone.now())
    # print  USE_TZ
    return render_to_response(
        'project_data/all_complain_list.html',
        {'complains': complains, 'complain_mgt': 'complain_mgt',
         'branches': branches, 'all_complain': 'all_complain',
         'page_header': 'All Requests'},
        context)

@login_required
def executed_list(request):
    context = RequestContext(request)
    start_time = (timezone.now() - timedelta(days=7)).date()
    end_time = (timezone.now() + timedelta(days=1)).date()
    complains = Complain.objects.none()
    branches = Branch.objects.filter(status='active')  # .order_by("pk")
    last_id = getLastIdInner()
    return render_to_response(
        'project_data/executed_list.html',
        {'complains': complains, 'complain_mgt': 'complain_mgt',
         'all_complain': 'all_complain', 'branches': branches,
         'page_header': 'Executed Requests',
          'last_id': last_id
         },context)


@csrf_exempt
def getExecutedRequests(request):
    from_date = str(request.POST.get('from_date')) + ' 00:00:00'
    to_date = str(request.POST.get('to_date'))+' 23:59:59'
    service_type = request.POST.get('problem_type')
    branch = request.POST.get('branch')
    execution_status = request.POST.get('execution_status')

    user_id = request.user.id
    role_check_query = "select role_id from usermodule_userrolemap where user_id = (select id from usermodule_usermoduleprofile where user_id = "+str(user_id)+")"
    df = pandas.DataFrame()
    df = pandas.read_sql(role_check_query,connection)
    if not df.empty:
        user_role = df.role_id.tolist()[0]
        if user_role == 3 or user_role == 4:
            query = "WITH rev AS( SELECT ( SELECT branch_id FROM usermodule_usermoduleprofile WHERE user_id = pin_id limit 1) branch_id, ticket_id, received_time, account_no, service_type, execution_status, transaction_id, transaction_date_time, id , sla,calculated_sla_time FROM project_data_complain WHERE reply_by = "+str(user_id)+" and execution_status = ANY ( '{Solved,Closed,Correction Needed}')) SELECT ticket_id, to_char(received_time, 'Dy dd Mon YYYY HH24:MI') AS received_time, account_no, service_type, execution_status, COALESCE(transaction_id::text,'') transaction_id, COALESCE(transaction_date_time::text,'') transaction_date_time, sla, id FROM rev where execution_status like '" + str(
                execution_status) + "' and calculated_sla_time between '" + str(from_date) + "' and '" + str(
                to_date) + "' and service_type like '" + str(service_type) + "' and branch_id::text like '" + str(
                branch) + "' order by rev.id desc"
            data = json.dumps(__db_fetch_values_dict(query), default=date_handler)
            cnt_query = "with t as( select * from project_data_complain where reply_by = "+str(user_id)+" and execution_status LIKE '" + str(
                execution_status) + "' AND calculated_sla_time BETWEEN '" + str(from_date) + "' AND '" + str(
                to_date) + "' AND service_type LIKE '" + str(
                service_type) + "' and pin_id in (SELECT user_id FROM usermodule_usermoduleprofile where branch_id::text like '" + str(
                branch) + "')), correction_cnt AS(SELECT Count(*) cnt_correction FROM t WHERE execution_status = 'Correction Needed'), solved_cnt AS (SELECT Count(*) cnt_solved FROM t WHERE execution_status = 'Solved'), closed_cnt AS (SELECT Count(*) cnt_closed FROM t WHERE execution_status = 'Closed') SELECT *, cnt_correction+cnt_solved+cnt_closed as total_solved FROM correction_cnt, solved_cnt, closed_cnt"
        else:
            query = "WITH rev AS( SELECT ( SELECT branch_id FROM usermodule_usermoduleprofile WHERE user_id = pin_id limit 1) branch_id, ticket_id, received_time, account_no, service_type, execution_status, transaction_id, transaction_date_time, id , sla,calculated_sla_time FROM project_data_complain WHERE execution_status = ANY ( '{Solved,Closed,Correction Needed}')) SELECT ticket_id, to_char(received_time, 'Dy dd Mon YYYY HH24:MI') AS received_time, account_no, service_type, execution_status, COALESCE(transaction_id::text,'') transaction_id, COALESCE(transaction_date_time::text,'') transaction_date_time, sla, id FROM rev where  execution_status like '" + str(
                execution_status) + "' and calculated_sla_time between '" + str(from_date) + "' and '" + str(
                to_date) + "' and service_type like '" + str(service_type) + "' and branch_id::text like '" + str(
                branch) + "' order by rev.id desc"
            data = json.dumps(__db_fetch_values_dict(query), default=date_handler)
            cnt_query = "with t as( select * from project_data_complain where  execution_status LIKE '" + str(
                execution_status) + "' AND calculated_sla_time BETWEEN '" + str(from_date) + "' AND '" + str(
                to_date) + "' AND service_type LIKE '" + str(
                service_type) + "' and pin_id in (SELECT user_id FROM usermodule_usermoduleprofile where branch_id::text like '" + str(
                branch) + "')), correction_cnt AS(SELECT Count(*) cnt_correction FROM t WHERE execution_status = 'Correction Needed'), solved_cnt AS (SELECT Count(*) cnt_solved FROM t WHERE execution_status = 'Solved'), closed_cnt AS (SELECT Count(*) cnt_closed FROM t WHERE execution_status = 'Closed') SELECT *, cnt_correction+cnt_solved+cnt_closed as total_solved FROM correction_cnt, solved_cnt, closed_cnt"

    else:
        query = "WITH rev AS( SELECT ( SELECT branch_id FROM usermodule_usermoduleprofile WHERE user_id = pin_id limit 1) branch_id, ticket_id, received_time, account_no, service_type, execution_status, transaction_id, transaction_date_time, id ,sla,calculated_sla_time FROM project_data_complain WHERE execution_status = ANY ( '{Solved,Closed,Correction Needed}')) SELECT ticket_id, to_char(received_time, 'Dy dd Mon YYYY HH24:MI') AS received_time, account_no, service_type, execution_status, COALESCE(transaction_id::text,'') transaction_id, COALESCE(transaction_date_time::text,'') transaction_date_time, sla, id FROM rev where  execution_status like '" + str(
            execution_status) + "' and calculated_sla_time between '" + str(from_date) + "' and '" + str(
            to_date) + "' and service_type like '" + str(service_type) + "' and branch_id::text like '" + str(
            branch) + "' order by rev.id desc"
        data = json.dumps(__db_fetch_values_dict(query), default=date_handler)
        cnt_query = "with t as( select * from project_data_complain where  execution_status LIKE '" + str(
            execution_status) + "' AND calculated_sla_time BETWEEN '" + str(from_date) + "' AND '" + str(
            to_date) + "' AND service_type LIKE '" + str(
            service_type) + "' and pin_id in (SELECT user_id FROM usermodule_usermoduleprofile where branch_id::text like '" + str(
            branch) + "')), correction_cnt AS(SELECT Count(*) cnt_correction FROM t WHERE execution_status = 'Correction Needed'), solved_cnt AS (SELECT Count(*) cnt_solved FROM t WHERE execution_status = 'Solved'), closed_cnt AS (SELECT Count(*) cnt_closed FROM t WHERE execution_status = 'Closed') SELECT *, cnt_correction+cnt_solved+cnt_closed as total_solved FROM correction_cnt, solved_cnt, closed_cnt"


    cnt_data = json.dumps(__db_fetch_values_dict(cnt_query), default=date_handler)
    return HttpResponse( json.dumps({'data':data,'cnt_data':cnt_data}, default=date_handler))

@login_required
def complain_unlock(request, complain_id, user_id):
    context = RequestContext(request)
    complain = Complain.objects.filter(pk=complain_id).first()
    if complain:
        # if request user is django superuser can unlock
        # if request user is locker then can unlock
        # if request user's role can over ride lock then can unlock
        # otherwise just redirect to complain page without doin anything
        if request.user.is_superuser:
            complain.locker = None
            complain.save(update_fields=["locker"])
            # complain.save()
            return HttpResponseRedirect('/project/new-complain/?unlock=unlock')
        current_user = UserModuleProfile.objects.filter(user=request.user).first()
        can_change_status = False
        can_override_lock = False
        if current_user:
            can_change_status = TaskRolePermissionMap.objects.filter(name__name='Change Complain Status',
                                                                     role=current_user.account_type).first()
            can_override_lock = TaskRolePermissionMap.objects.filter(name__name='Override Complain Lock',
                                                                     role=current_user.account_type).first()
        # print(can_change_status,can_override_lock)
        if can_change_status or can_override_lock:
            complain.locker = None
            complain.save(update_fields=["locker"])
            # complain.save()
            return HttpResponseRedirect('/project/new-complain/?unlock=unlock')

    return HttpResponseRedirect('/project/new-complain/')


@login_required
def complain_unlock_home(request, complain_id, user_id):
    context = RequestContext(request)
    complain = Complain.objects.filter(pk=complain_id).first()
    if complain:
        # if request user is django superuser can unlock
        # if request user is locker then can unlock
        # if request user's role can over ride lock then can unlock
        # otherwise just redirect to complain page without doin anything
        if request.user.is_superuser:
            complain.locker = None
            complain.save(update_fields=["locker"])
            # complain.save()
            return HttpResponseRedirect('/project/new-complain/?unlock=unlock')
        current_user = UserModuleProfile.objects.filter(user=request.user).first()
        can_change_status = False
        can_override_lock = False
        if current_user:
            can_change_status = TaskRolePermissionMap.objects.filter(name__name='Change Complain Status',
                                                                     role=current_user.account_type).first()
            can_override_lock = TaskRolePermissionMap.objects.filter(name__name='Override Complain Lock',
                                                                     role=current_user.account_type).first()
        if can_change_status or can_override_lock:
            complain.locker = None
            complain.save(update_fields=["locker"])
            return HttpResponseRedirect('/project/new-complain/?unlock=unlock')


def logout_view(request):
    print 'majbah'  # force logout other user , Not needed for now
    # user = User.objects.get(username='mirza.zaman')
    # [s.delete() for s in Session.objects.all() if s.get_decoded().get('_auth_user_id') == 'mirza.zaman']
    for s in Session.objects.all():
        data = s.get_decoded()
        t = complain.locker
        print t
        if data.get('_auth_user_id', None) == 'complain.locker':
            s.delete()
            logout(request)
    return HttpResponseRedirect('/usermodule/login/')


@login_required
def filter_complain_list(request):
    problem_type = request.GET.get('problem_type', 'custom')
    branch = request.GET.get('branch', 'custom')
    status = request.GET.get('status', 'custom')

    start_time = request.GET.get('start', 'custom')
    end_time = request.GET.get('end', 'custom')

    where_clause = ''

    date_part = " and t.received_time > '" + str(start_time) + "' and t.received_time < '" + str(end_time) + "'"
    if status != 'custom':
        status_clause = " t.execution_status = '" + str(problem_type) + "'"
    else:
        status_clause = " (t.execution_status = 'Read' OR t.execution_status = 'New')"

    if problem_type != 'custom':
        where_clause += " and service_type = '" + str(problem_type) + "'"
    if branch != 'custom':
        where_clause += ""

    filter_query = "WITH t AS(SELECT (SELECT branch_id FROM project_data_branch WHERE id = (SELECT branch_id FROM usermodule_usermoduleprofile WHERE user_id = au.id)) AS brc, pdc.*, (select branch_id from usermodule_usermoduleprofile where user_id = pdc.pin_id) as branch FROM project_data_complain pdc left join auth_user au ON au.id = pdc.pin_id) SELECT Concat(t.brc, Lpad(t.id :: text, 5, '0')) AS ticket_id, To_char(t.received_time, 'Dy dd Mon YYYY HH24:MI') AS received_time, t.account_no, t.service_type, t.execution_status, t.transaction_id, To_char(t.transaction_date_time, 'Dy dd Mon YYYY HH24:MI') AS transaction_date_time, t.id FROM t WHERE " + status_clause + " " + date_part + " " + where_clause + " ORDER BY t.received_time DESC"

    complains = json.dumps(__db_fetch_values(filter_query), default=date_handler)

    return HttpResponse(complains)


@login_required
def complain_filter_list(request):
    problem_type = request.GET.get('problem_type', 'custom')
    branch = request.GET.get('branch', 'custom')
    status = request.GET.get('status', 'custom')
    print status
    start_time = request.GET.get('start', 'custom')
    end_time = request.GET.get('end', 'custom')
    # end_time= end_time + " 23:59:59"
    # print end_time
    # q_objects = Q(transaction_date_time__range=(start_time, end_time)) # Create an empty Q object to start with
    q_objects = Q(received_time__range=(start_time, end_time))  # Create an empty Q object to start with

    source = request.GET.get('order', 'asc')
    ordering = 'pk' if source == 'asc' else '-pk'
    if problem_type != 'custom':
        q_objects &= Q(service_type=problem_type)  #
    if branch != 'custom':
        q_objects &= Q(pin__usermoduleprofile__branch__pk=branch)  #
    if status != 'custom':
        if status == "Pending":
            q_objects &= Q(execution_status='New') | Q(execution_status='Read')  #
        else:
            q_objects &= Q(execution_status=status)  #

    complain_list = Complain.objects.filter(q_objects).order_by(ordering)
    # if problem_type != 'custom' and branch != 'custom' and status != 'custom':
    #     complain_list = Complain.objects.filter(transaction_date_time__range=(start_time, end_time), service_type = problem_type, execution_status = status, pin__usermoduleprofile__branch__pk = branch).order_by(ordering)
    # elif problem_type != 'custom' and branch != 'custom':
    #     complain_list = Complain.objects.filter(transaction_date_time__range=(start_time, end_time), service_type = problem_type, pin__usermoduleprofile__branch__pk = branch).order_by(ordering)
    # elif problem_type != 'custom' and status != 'custom':
    #     complain_list = Complain.objects.filter(transaction_date_time__range=(start_time, end_time), service_type = problem_type, execution_status = status).order_by(ordering)
    # elif branch != 'custom' and status != 'custom':
    #     complain_list = Complain.objects.filter(transaction_date_time__range=(start_time, end_time), pin__usermoduleprofile__branch__pk = branch, execution_status = status).order_by(ordering)
    # else:        
    #     complain_list = Complain.objects.all().order_by(ordering)
    # print '==========================='
    # print 'branch',branch
    # print 'status',status  
    # print 'query',complain_list.query  

    response_data = []
    # complain_list = Complain.objects.filter(service_type = problem_type, execution_status = status, pin__usermoduleprofile__branch__pk = branch).order_by("-pk")
    # print complain_list
    for complain in complain_list:
        data = dict()
        if complain.pin.usermoduleprofile.branch is not None:
            data["serial"] = complain.pin.usermoduleprofile.branch.branch_id + ('%05d' % complain.id)
        else:
            data["serial"] = '%05d' % complain.id

        # data["date"] = complain.transaction_date_time.strftime("%A %d %B %Y")
        # data["time"] = complain.transaction_date_time.strftime("%H : %M")
        # print '&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&'
        # print complain.received_time

        data["date"] = localize_datetime(
            complain.received_time)  # .strftime("%a %d %b %Y %H:%M %X") #timezone.localtime(complain.received_time) #complain.received_time.replace(tzinfo='Asia/Dhaka').strftime("%a %d %b %Y %H:%M %X")
        data["time"] = complain.received_time.strftime("%H : %M")
        # print data["time"] + "    " + data["date"]
        data["account_no"] = complain.account_no
        data["service_type"] = complain.service_type
        if complain.service_type == "Transaction Confirmation":
            data["transaction_id"] = complain.transaction_id
            data["tdate"] = complain.transaction_date_time.strftime("%a %d %b %Y %H:%M")
        else:
            data["transaction_id"] = ""
            data["tdate"] = ""
        data["status"] = complain.execution_status
        data["view"] = complain.id

        response_data.append(data)
    # print response_data
    return HttpResponse(json.dumps(response_data), content_type="application/json")


def add_complain(request):
    context = RequestContext(request)
    edit_check = False
    complain_form = ComplainForm(data=request.POST or None, edit_check=edit_check)
    if request.method == 'POST':
        if complain_form.is_valid():
            cmp_obj = complain_form.save(commit=False)
            cmp_obj.pin = request.user
            cmp_obj.save()
            return HttpResponseRedirect('/project/new-complain/')
        else:
            print complain_form.errors
    return render_to_response(
        'project_data/add_complain.html',
        {'complain_form': complain_form},
        context)

import  pandas
@csrf_exempt
def add_complain_mobile(request):
    '''
    JSON field=> model field
    AccountNumber => account_no
    ServiceType => service_type 
    CustomerName => customer_name
    AccountBalance => balance
    IdCardType => id_type
    IdCardNumber => id_no
    TransactionId => transaction_id
    Date => transaction_date_time
    Amount => transaction_amount
    Remarks => remarks_of_csa_customer
    remarks_of_bkash_cs
    execution_status
    not_execute_reason
    '''
    if request.method == 'POST':
        data = request.POST.get("data", "xxx")
        json_obj = json.loads(data)
        print(json_obj)
        user = User.objects.get(username=json_obj['pin'])
        user_profile = UserModuleProfile.objects.get(user_id=user.id)
        branch = Branch.objects.get(pk=user_profile.branch_id)
        if not user.is_active or branch.status == 'inactive':
            error_mes = {}
            error_mes['code'] = 403
            error_mes['message'] = 'Your User account is disabled.'
            return HttpResponse(json.dumps(error_mes), status=403)
        # valid = wallet_check(request, json_obj['account_number'])
        valid = True
        if valid:
            complain_obj = Complain()
            complain_obj.service_type = json_obj['service_type']
            serv_type =  json_obj['service_type']
            if not len(serv_type):
                return HttpResponse(status=201)
            if "mac_address" in json_obj:
                complain_obj.mac_address = json_obj['mac_address']
            if "csa_ticket_open_time" in json_obj:
                complain_obj.csa_ticket_open_time = json_obj['csa_ticket_open_time']
            if "csa_ticket_close_time" in json_obj:
                complain_obj.csa_ticket_close_time = json_obj['csa_ticket_close_time']
            if serv_type == 'New Registration' or serv_type == 'Information Update':
                if "parent_id" in json_obj:
                    complain_obj.parent_id = json_obj['parent_id']
                    query = "select id from project_data_complain where id = "+str(json_obj['parent_id'])+" or parent_id = "+str(json_obj['parent_id'])+" order by id desc limit 1"
                    df = pandas.DataFrame()
                    df = pandas.read_sql(query,connection)
                    # if this data frame is empty then there is a problem
                    id = df.id.tolist()[0]
                    obj = Complain.objects.get(pk=id)
                    if "account_number" in json_obj:
                        complain_obj.account_no = json_obj['account_number']
                    else:
                        complain_obj.account_no = obj.account_no
                    if "account_name" in json_obj:
                        complain_obj.customer_name = json_obj['account_name']
                    else:
                        complain_obj.customer_name = obj.customer_name

                    if "nid_number" in json_obj:
                        complain_obj.id_no = json_obj['nid_number']
                    else:
                        complain_obj.id_no = obj.id_no

                    if "barcode_number" in json_obj:
                        complain_obj.barcode_number = json_obj['barcode_number']
                    else:
                        complain_obj.barcode_number = obj.barcode_number

                    if "remarks" in json_obj:
                        complain_obj.remarks = json_obj['remarks']
                    else:
                        complain_obj.remarks = obj.remarks


                    if "nid_front" in request.FILES:
                        myfile = request.FILES['nid_front']
                        url = "static/media/uploaded_files/"
                        userName = json_obj['pin']  # "Jubair"
                        fs = FileSystemStorage(location=url)
                        # myfile.name = str(str(datetime.now()).replace(' ', '_')) + "_" + str(userName) + "_" + str(myfile.name)
                        myfile.name = complain_obj.account_no+'(1).jpg'
                        filename = fs.save(myfile.name, myfile)
                        full_file_path1 = "/static/media/uploaded_files/" + myfile.name
                        complain_obj.nid_front = full_file_path1
                    else:
                        complain_obj.nid_front = obj.nid_front

                    if "nid_back" in request.FILES:
                        myfile = request.FILES['nid_back']
                        url = "static/media/uploaded_files/"
                        userName = json_obj['pin']  # "Jubair"
                        fs = FileSystemStorage(location=url)
                        # myfile.name = str(str(datetime.now()).replace(' ', '_')) + "_" + str(userName) + "_" + str(myfile.name)
                        myfile.name = complain_obj.account_no + '(2).jpg'
                        filename = fs.save(myfile.name, myfile)
                        full_file_path2 = "/static/media/uploaded_files/" + myfile.name
                        complain_obj.nid_back = full_file_path2
                    else:
                        complain_obj.nid_back = obj.nid_back
                    if "dob" in json_obj:
                        complain_obj.date_of_birth = json_obj['dob']
                    else:
                        complain_obj.date_of_birth = obj.date_of_birth

                    if "pin" in json_obj:
                        complain_obj.pin = User.objects.filter(username=json_obj['pin']).first()
                    else:
                        complain_obj.pin = obj.pin
                    if "account_balance" in json_obj:
                        complain_obj.account_balance = json_obj['account_balance']
                    else:
                        complain_obj.account_balance = obj.account_balance

                    complain_obj.id_type = 'NID'
                    if obj.execution_status == 'Correction Needed':
                        complain_obj.execution_status = 'Corrected'
                    else:
                        complain_obj.execution_status = 'New'
                    complain_obj.status = 'Open'


                    obj.status = 'Closed'
                    obj.save(update_fields=["status"])
                    if "transaction_type" in json_obj:
                        complain_obj.transaction_type = json_obj['transaction_type']
                    if "transaction_amount" in json_obj:
                        complain_obj.transaction_amount = json_obj['transaction_amount']

                    if "kyc_front" in request.FILES:
                        complain_obj.step = 2                        
                        myfile = request.FILES['kyc_front']
                        url = "static/media/uploaded_files/"
                        userName = json_obj['pin']
                        fs = FileSystemStorage(location=url)
                        # myfile.name = str(str(datetime.now()).replace(' ', '_')) + "_" + str(userName) + "_" + str(myfile.name)
                        myfile.name = complain_obj.account_no + '(3).jpg'
                        filename = fs.save(myfile.name, myfile)
                        full_file_path3 = "/static/media/uploaded_files/" + myfile.name
                        complain_obj.kyc_front = full_file_path3
                    else: complain_obj.step = obj.step

                    if "kyc_back" in request.FILES:
                        myfile = request.FILES['kyc_back']
                        url = "static/media/uploaded_files/"
                        userName = json_obj['pin']
                        fs = FileSystemStorage(location=url)
                        # myfile.name = str(str(datetime.now()).replace(' ', '_')) + "_" + str(userName) + "_" + str(myfile.name)
                        myfile.name = complain_obj.account_no + '(4).jpg'
                        filename = fs.save(myfile.name, myfile)
                        full_file_path4 = "/static/media/uploaded_files/" + myfile.name
                        complain_obj.kyc_back = full_file_path4
                    if "nid_copy" in request.FILES:
                        myfile = request.FILES['nid_copy']
                        url = "static/media/uploaded_files/"
                        userName = json_obj['pin']
                        fs = FileSystemStorage(location=url)
                        # myfile.name = str(str(datetime.now()).replace(' ', '_')) + "_" + str(userName) + "_" + str(myfile.name)
                        myfile.name = complain_obj.account_no + '(5).jpg'
                        filename = fs.save(myfile.name, myfile)
                        full_file_path5 = "/static/media/uploaded_files/" + myfile.name
                        complain_obj.nid_copy = full_file_path5

                else:
                    complain_obj.account_no = json_obj['account_number']
                    complain_obj.customer_name = json_obj['account_name']
                    if "barcode_number" in json_obj:
                        complain_obj.barcode_number = json_obj['barcode_number']
                    if "remarks" in json_obj:
                        complain_obj.remarks = json_obj['remarks']
                    if "account_balance" in json_obj:
                        complain_obj.account_balance = json_obj['account_balance']
                    if "reason" in json_obj:
                        complain_obj.reason = json_obj['reason']
                    if "transaction_type" in json_obj:
                        complain_obj.transaction_type = json_obj['transaction_type']
                    if "transaction_amount" in json_obj:
                        complain_obj.transaction_amount = json_obj['transaction_amount']
                    complain_obj.id_no = json_obj['nid_number']
                    complain_obj.date_of_birth = json_obj['dob']
                    complain_obj.pin = User.objects.filter(username=json_obj['pin']).first()
                    myfile = request.FILES['nid_front']
                    url = "static/media/uploaded_files/"
                    userName = json_obj['pin']  # "Jubair"
                    fs = FileSystemStorage(location=url)
                    # myfile.name = str(str(datetime.now()).replace(' ', '_')) + "_" + str(userName) + "_" + str(myfile.name)
                    myfile.name = complain_obj.account_no + '(1).jpg'
                    filename = fs.save(myfile.name, myfile)
                    full_file_path1 = "/static/media/uploaded_files/" + myfile.name
                    complain_obj.nid_front = full_file_path1

                    myfile = request.FILES['nid_back']
                    url = "static/media/uploaded_files/"
                    userName = json_obj['pin']  # "Jubair"
                    fs = FileSystemStorage(location=url)
                    # myfile.name = str(str(datetime.now()).replace(' ', '_')) + "_" + str(userName) + "_" + str(myfile.name)
                    myfile.name = complain_obj.account_no + '(2).jpg'
                    filename = fs.save(myfile.name, myfile)
                    full_file_path2 = "/static/media/uploaded_files/" + myfile.name
                    complain_obj.nid_back = full_file_path2

                    complain_obj.step = 1
                    complain_obj.id_type = 'NID'
                    complain_obj.execution_status = 'New'
                    complain_obj.status = 'Open'
                complain_obj.save()

            elif serv_type == 'Transaction Confirmation':
                complain_obj.step = 1
                complain_obj.account_no = json_obj['account_number']
                complain_obj.customer_name = json_obj['account_name']
                complain_obj.account_balance = json_obj['account_balance']
                complain_obj.transaction_date_time = json_obj['transaction_date']
                complain_obj.transaction_amount = json_obj['transaction_amount']
                complain_obj.id_no = json_obj['nid_number']
                complain_obj.transaction_type = json_obj['transaction_type']
                if "transaction_id" in json_obj:
                    complain_obj.transaction_id = json_obj['transaction_id']
                if "remarks" in json_obj:
                    complain_obj.remarks_of_csa_customer = json_obj['remarks']
                complain_obj.pin = User.objects.filter(username=json_obj['pin']).first()
                if "parent_id" in json_obj:
                    complain_obj.parent_id = json_obj['parent_id']
                    query = "select id from project_data_complain where id = " + str(json_obj['parent_id']) + " or parent_id = " + str(json_obj['parent_id']) + " order by id desc limit 1"
                    df = pandas.DataFrame()
                    df = pandas.read_sql(query, connection)
                    # if this data frame is empty then there is a problem
                    id = df.id.tolist()[0]
                    obj = Complain.objects.get(pk=id)
                    if obj.execution_status == 'Correction Needed':
                        complain_obj.execution_status = 'Corrected'
                    obj.status = 'Closed'
                    if "nid_front" in request.FILES:
                        myfile = request.FILES['nid_front']
                        url = "static/media/uploaded_files/"
                        userName = json_obj['pin']  # "Jubair"
                        fs = FileSystemStorage(location=url)
                        # myfile.name = str(str(datetime.now()).replace(' ', '_')) + "_" + str(userName) + "_" + str(myfile.name)
                        myfile.name = complain_obj.account_no + '(1).jpg'
                        filename = fs.save(myfile.name, myfile)
                        full_file_path1 = "/static/media/uploaded_files/" + myfile.name
                        complain_obj.nid_front = full_file_path1
                    else:
                        complain_obj.nid_front = obj.nid_front

                    if "nid_back" in request.FILES:
                        myfile = request.FILES['nid_back']
                        url = "static/media/uploaded_files/"
                        userName = json_obj['pin']  # "Jubair"
                        fs = FileSystemStorage(location=url)
                        # myfile.name = str(str(datetime.now()).replace(' ', '_')) + "_" + str(userName) + "_" + str(myfile.name)
                        myfile.name = complain_obj.account_no + '(2).jpg'
                        filename = fs.save(myfile.name, myfile)
                        full_file_path2 = "/static/media/uploaded_files/" + myfile.name
                        complain_obj.nid_back = full_file_path2
                    else:
                        complain_obj.nid_back = obj.nid_back
                    obj.save(update_fields=["status"])
                else:
                    if "nid_front" in request.FILES:
                        myfile = request.FILES['nid_front']
                        url = "static/media/uploaded_files/"
                        userName = json_obj['pin']  # "Jubair"
                        fs = FileSystemStorage(location=url)
                        # myfile.name = str(str(datetime.now()).replace(' ', '_')) + "_" + str(userName) + "_" + str(myfile.name)
                        myfile.name = complain_obj.account_no + '(1).jpg'
                        filename = fs.save(myfile.name, myfile)
                        full_file_path1 = "/static/media/uploaded_files/" + myfile.name
                        complain_obj.nid_front = full_file_path1

                    if "nid_back" in request.FILES:
                        myfile = request.FILES['nid_back']
                        url = "static/media/uploaded_files/"
                        userName = json_obj['pin']  # "Jubair"
                        fs = FileSystemStorage(location=url)
                        # myfile.name = str(str(datetime.now()).replace(' ', '_')) + "_" + str(userName) + "_" + str(myfile.name)
                        myfile.name = complain_obj.account_no + '(2).jpg'
                        filename = fs.save(myfile.name, myfile)
                        full_file_path2 = "/static/media/uploaded_files/" + myfile.name
                        complain_obj.nid_back = full_file_path2
                    complain_obj.execution_status = 'New'
                complain_obj.status = 'Open'
                complain_obj.save()


            elif serv_type == 'Pin Reset' or serv_type == 'Bar' or serv_type=='Unbar':
                complain_obj.step = 1
                complain_obj.account_no = json_obj['account_number']
                complain_obj.customer_name = json_obj['account_name']
                if "reason" in json_obj:
                    complain_obj.reason = json_obj['reason']
                if "transaction_type" in json_obj:
                    complain_obj.transaction_type = json_obj['transaction_type']
                if "transaction_amount" in json_obj:
                    complain_obj.transaction_amount = json_obj['transaction_amount']
                if "account_balance" in json_obj:
                    complain_obj.account_balance = json_obj['account_balance']
                if "nid_number" in json_obj:
                    complain_obj.id_no = json_obj['nid_number']

                if "remarks" in json_obj:
                    complain_obj.remarks_of_csa_customer = json_obj['remarks']
                complain_obj.pin = User.objects.filter(username=json_obj['pin']).first()

                if "parent_id" in json_obj:

                    complain_obj.parent_id = json_obj['parent_id']
                    query = "select id from project_data_complain where id = " + str(json_obj['parent_id']) + " or parent_id = " + str(json_obj['parent_id']) + " order by id desc limit 1"
                    df = pandas.DataFrame()
                    df = pandas.read_sql(query, connection)
                    # if this data frame is empty then there is a problem
                    id = df.id.tolist()[0]
                    obj = Complain.objects.get(pk=id)
                    if obj.execution_status == 'Correction Needed':
                        complain_obj.execution_status = 'Corrected'
                    obj.status = 'Closed'
                    if "nid_front" in request.FILES:
                        myfile = request.FILES['nid_front']
                        url = "static/media/uploaded_files/"
                        userName = json_obj['pin']  # "Jubair"
                        fs = FileSystemStorage(location=url)
                        # myfile.name = str(str(datetime.now()).replace(' ', '_')) + "_" + str(userName) + "_" + str(myfile.name)
                        myfile.name = complain_obj.account_no + '(1).jpg'
                        filename = fs.save(myfile.name, myfile)
                        full_file_path1 = "/static/media/uploaded_files/" + myfile.name
                        complain_obj.nid_front = full_file_path1
                    else:
                        complain_obj.nid_front = obj.nid_front

                    if "nid_back" in request.FILES:
                        myfile = request.FILES['nid_back']
                        url = "static/media/uploaded_files/"
                        userName = json_obj['pin']  # "Jubair"
                        fs = FileSystemStorage(location=url)
                        # myfile.name = str(str(datetime.now()).replace(' ', '_')) + "_" + str(userName) + "_" + str(myfile.name)
                        myfile.name = complain_obj.account_no + '(2).jpg'
                        filename = fs.save(myfile.name, myfile)
                        full_file_path2 = "/static/media/uploaded_files/" + myfile.name
                        complain_obj.nid_back = full_file_path2
                    else:
                        complain_obj.nid_back = obj.nid_back
                    obj.save(update_fields=["status"])
                else:
                    if "nid_front" in request.FILES:
                        myfile = request.FILES['nid_front']
                        url = "static/media/uploaded_files/"
                        userName = json_obj['pin']  # "Jubair"
                        fs = FileSystemStorage(location=url)
                        # myfile.name = str(str(datetime.now()).replace(' ', '_')) + "_" + str(userName) + "_" + str(myfile.name)
                        myfile.name = complain_obj.account_no + '(1).jpg'
                        filename = fs.save(myfile.name, myfile)
                        full_file_path1 = "/static/media/uploaded_files/" + myfile.name
                        complain_obj.nid_front = full_file_path1

                    if "nid_back" in request.FILES:
                        myfile = request.FILES['nid_back']
                        url = "static/media/uploaded_files/"
                        userName = json_obj['pin']  # "Jubair"
                        fs = FileSystemStorage(location=url)
                        # myfile.name = str(str(datetime.now()).replace(' ', '_')) + "_" + str(userName) + "_" + str(myfile.name)
                        myfile.name = complain_obj.account_no + '(2).jpg'
                        filename = fs.save(myfile.name, myfile)
                        full_file_path2 = "/static/media/uploaded_files/" + myfile.name
                        complain_obj.nid_back = full_file_path2

                    complain_obj.execution_status = 'New'
                complain_obj.status = 'Open'
                complain_obj.save()

            return HttpResponse(complain_obj.id)
        else:
            return HttpResponse(status=201)
    else:
        return HttpResponse(status=201)



def full_view_complain(request,complain_id):
    context = RequestContext(request)
    complain = Complain.objects.get(pk=complain_id)
    # get comment text from comment_id in complain object
    # q = "select comment_text from comments where id = " + str(complain.comment_id)
    # df = pandas.DataFrame()
    # df = pandas.read_sql(q, connection)
    # complain.comment_id = df.comment_text.tolist()[0]
    parent_id = complain.parent_id
    current_user = UserModuleProfile.objects.filter(user=request.user).first()
    parent = Complain()
    reply_by = ""
    if parent_id:
        parent = Complain.objects.filter(~Q(pk=complain_id) & Q(status='Closed') & (Q(pk=parent_id) | Q(parent_id=parent_id)) & Q(reply_by__isnull=False)).order_by(
            'ticket_id')
        reply_by = User.objects.filter(pk__in=parent.values_list('reply_by', flat=True)).values('id', 'username')

        for i in range(0, len(parent)):
            for j in range(0, len(reply_by)):
                print(reply_by[j]['id'])
                if parent[i].reply_by == reply_by[j]['id']:
                    parent[i].reply_by = reply_by[j]['username']
    return render_to_response('project_data/full_view_complain.html',
        {'id': complain_id, 'parent': parent, 'reply_by': reply_by,'complain_mgt':'complain_mgt','all_complain':'all_complain',
         'complain': complain},
        context)

@login_required
def edit_complain(request, complain_id):
    context = RequestContext(request)
    edit_check = True
    show_status_dropdown = False
    complain = Complain.objects.get(pk=complain_id)
    reply_from = ""
    if complain.execution_status in [ 'Escalate','Forward']:
        reply_from = User.objects.get(pk=complain.reply_by)
    # get comment text from comment_id in complain object
    # if complain.comment_text is not None:
        # q = "select comment_text from comments where id = " + str(complain.comment_id)
        # df = pandas.DataFrame()
        # df = pandas.read_sql(q, connection)
        # complain.comment_text = comment_text
    current_user = UserModuleProfile.objects.filter(user=request.user).first()
    is_bkash_exec = False
    can_change_status = False
    can_override_lock = False

    user_id = request.user.id
    query_role = "select role_id from usermodule_userrolemap where user_id = (select id from usermodule_usermoduleprofile where user_id = "+str(user_id)+")"
    df = pandas.DataFrame()
    df = pandas.read_sql(query_role,connection)
    if not df.empty:
        role_id = df.role_id.tolist()[0]
    else: role_id = 0
    if complain.execution_status in ['Solved','Closed','Correction Needed'] or (role_id == 3 and complain.execution_status=='Escalate') or (role_id == 4 and complain.execution_status=='Forward'):
        return error_page(request,"Page Not Found")
    # + timedelta(minutes=5)
    t = datetime.now()
    if complain.lock_date_time is None:
        complain.lock_date_time = t
    # complain.locker = request.user
    parent_id = complain.parent_id
    complain.save()
    parent = Complain()
    reply_by = ""
    if parent_id:
        parent = Complain.objects.get(pk=parent_id)
        parent = Complain.objects.filter(Q(pk=parent_id) | Q(parent_id=parent_id) & Q(reply_by__isnull=False)).order_by('ticket_id')
        reply_by = User.objects.filter(pk__in=parent.values_list('reply_by', flat=True)).values('id','username')

        for i in range(0,len(parent)):
            for j in range(0,len(reply_by)):
                if parent[i].reply_by == reply_by[j]['id']:
                    parent[i].reply_by = reply_by[j]['username']
            if parent[i].comment_text is None:
                parent[i].comment_text = ""
            # else:
                # q = "select comment_text from comments where id ="+str(parent[i].comment_id)
                # df = pandas.DataFrame()
                # df = pandas.read_sql(q,connection)
                # parent[i].comment_text = comment_text
                # print(parent[i].comment_id)
    query = "select EXTRACT(epoch from given_sla_time)::int*1000 given_sla_time from project_data_complain where  id="+str(complain_id)
    df = pandas.DataFrame()
    df = pandas.read_sql(query,connection)
    given_sla_time = df.given_sla_time.tolist()[0]
    print(given_sla_time)
    # query=" SELECT lock_date_time FROM public.project_data_complain where locker_id = '144' ";


    #  b = Complain.lock_date_time(complain_id=complain_id)
    #  b=Complain.objects.filter(id='complain_id')
    b = Complain.objects.filter(pk=complain_id).first()
    lock_time = b.lock_date_time

    # print lock_time

    # z=datetime.now()
    # fixed_lock_time=z-lock_time

    # print fixed_lock_time
    # print t
    if datetime.now() > lock_time:
        print 'Ok Acid'
        complain.locker == None
        complain.save(update_fields=["locker"])
    if current_user:
        can_change_status = TaskRolePermissionMap.objects.filter(name__name='Change Complain Status',
                                                                 role=current_user.account_type).first()
        can_override_lock = TaskRolePermissionMap.objects.filter(name__name='Override Complain Lock',
                                                                 role=current_user.account_type).first()

        # if can_override_lock:
        #     show_status_dropdown = True
        # if not request user's role has permission to override lock then proceed
        if can_change_status:
            is_bkash_exec = True
            show_status_dropdown = True
            if complain.locker == None:
                # check if locker is null, if null then set locker
                complain.locker = request.user
                complain.save(update_fields=["locker"])
            elif complain.locker == request.user:
                # if locker is not null then if request user is locker user then proceed
                pass
            else:
                # you are here, so complain is locked but current user is not the locker

                # if you are lock over ride type user then you should be able to see
                # the details but cannot change while locked
                #
                if can_override_lock:
                    show_status_dropdown = False
                else:
                    # user is neither locker nor lock override type role's user so redirect to complain page,
                    # with message that complain is locked by username
                    return HttpResponseRedirect('/project/new-complain/?complain_id='+str(complain.id)+'&locker=' + complain.locker.username)
    # complain_form = ComplainForm(data=request.POST or None, instance=complain, edit_check=edit_check,
    #                              show_status_dropdown=show_status_dropdown,
    #                              initial={'execution_status': complain.execution_status})
    if request.method == 'POST':
        complain = Complain.objects.get(pk=complain_id)
        status = request.POST.get('status')
        complain.execution_status = status
        if complain.execution_status == 'Closed':
            complain.status = 'Closed'
        elif complain.execution_status in ['Correction Needed','Escalate','Forward']:
            complain.status = 'Open'
        elif complain.execution_status == 'Solved':
            if complain.step == 1 and complain.service_type in ['New Registration', 'Information Update']:
                complain.status = 'Open'
            else:
                complain.status = 'Closed'


        if status == 'Solved' or status == 'Closed' or status == 'Correction Needed':
            comment = request.POST.getlist('comment')
            # print(comment)
            other_comment  = request.POST.get('other_comment','')
            res = ""
            for i in range(0,len(comment)):
                query = "select comment_text from comments where id = "+str(comment[i])
                df = pandas.read_sql(query,connection)
                res = res + df.comment_text.tolist()[0] + ', '
            res = res[0:-2]
            complain.comment_text  = res
            complain.other_comment = other_comment
        elif status == 'Escalate' or status == 'Forward':
            escalate = request.POST.get('escalate')
            note = request.POST.get('note', '')
            complain.escalate_to = escalate
            complain.note = note

        complain.reply_by = request.user.id
        complain.locker = None
        # + timedelta(minutes=5)
        complain.ticket_close_time = datetime.now()
        qry = "select to_char((getworkingtime(received_time,'"+str(complain.ticket_close_time)+"') || ' minute' ) :: interval, 'HH24:MI:SS') sla from project_data_complain where id="+str(complain_id)
        df = pandas.DataFrame()
        df = pandas.read_sql(qry,connection)
        complain.sla = df.sla.tolist()[0]
        if complain.execution_status in ['Solved', 'Closed', 'Correction Needed']:
            send_push_notification(complain.mac_address,complain.service_type,complain_id,complain.execution_status,complain.comment_text,complain.other_comment,complain.customer_name)


        complain.save(update_fields=['locker','execution_status','status','comment_text','other_comment','escalate_to','note','reply_by','ticket_close_time','sla'])

        # dont know what this does
        '''if is_bkash_exec:
            cmp_stat = ComplainStatusLog(complain=complain, bkash_agent=request.user,status=complain.execution_status)
            cmp_stat.save()'''

        return HttpResponseRedirect('/project/new-complain/?status=success')




        # if complain_form.is_valid():
        #     cmp_obj = complain_form.save(commit=False)
        #     if can_change_status or can_override_lock:
        #         cmp_obj.locker = None
        #     if cmp_obj.execution_status == 'Executed':
        #         cmp_obj.not_execute_reason = None
        #     elif cmp_obj.execution_status == 'Escalated':
        #         cmp_obj.not_execute_reason = None
        #     cmp_obj.save()
        #     if is_bkash_exec:
        #         cmp_stat = ComplainStatusLog(complain=complain, bkash_agent=request.user,
        #                                      status=complain.execution_status)
        #         cmp_stat.save()
        #     return HttpResponseRedirect('/project/new-complain/?status=success')
        # else:
        #     print complain_form.errors

    if current_user:
        is_previously_set = complain.execution_status in ['Forward', 'Escalate', 'Correction Needed','Solved','Closed']
        if not is_previously_set:
            complain.execution_status = 'Open'
            # complain.save()
            complain.save(update_fields=["execution_status"])

            # dont know what this does
            '''cmp_stat = ComplainStatusLog(complain=complain, bkash_agent=request.user, status='Read')
            cmp_stat.save()'''

    return render_to_response(
        'project_data/edit_complain.html',
        { 'id': complain_id,'parent':parent,'reply_by':reply_by,'role_id':role_id,'reply_from':reply_from,
         'complain': complain, 'show_status_dropdown': show_status_dropdown,'given_sla_time':given_sla_time},
        context)


@csrf_exempt
def user_login(request):
    '''
    receives pin and password and returns 200 if valid
	'''
    json_string = request.body
    data = json.loads(json_string)
    print("USER LOGIN")
    print(data)
    print("***************")
    error_mes = {}
    if data:
        m_username = data['pin']
        m_password = data['password']
        user = authenticate(username=m_username, password=m_password)
        if user:
            mobile_response = {}
            user = User.objects.get(username=m_username)
            user_profile = UserModuleProfile.objects.get(user_id=user.id)
            branch = Branch.objects.get(pk=user_profile.branch_id)
            if not user.is_active or branch.status == 'inactive':
                error_mes['code'] = 403
                error_mes['message'] = 'Your User account is disabled.'
                return HttpResponse(json.dumps(error_mes), status=403)
            mobile_response['username'] = m_username
            mobile_response['name'] = user.first_name
            mobile_response['password'] = m_password
            mobile_response['branch'] = branch.name
            update_token(data)
            return HttpResponse(json.dumps(mobile_response), content_type="application/json")
        else:
            # raise Http404("No such user exists with that pin and password combination")
            error_mes['code'] = 404
            error_mes['message'] = 'No such user exists with that pin and password combination'
            return HttpResponse(json.dumps(error_mes), status=404)
    else:
        error_mes['code'] = 401
        error_mes['message'] = 'Invalid Login'
        return HttpResponse(json.dumps(error_mes),status=401)


@login_required
def branch_list(request):
    context = RequestContext(request)
    branches = Branch.objects.all().order_by("pk")
    return render_to_response(
        'project_data/branch_list.html',
        {'branches': branches, 'branch_mgt': 'branch_mgt', 'branch_list': 'branch_list'},
        context)


@login_required
def add_branch(request):
    context = RequestContext(request)
    branch_form = BranchForm(data=request.POST or None)
    if request.method == 'POST':
        if branch_form.is_valid():
            branch_form.save()
            return HttpResponseRedirect('/project/branch-list/')
        else:
            print branch_form.errors
    return render_to_response(
        'project_data/add_branch.html',
        {'branch_form': branch_form, 'branch_mgt': 'branch_mgt', 'add_branch': 'add_branch'},
        context)


@login_required
@user_passes_test(admin_check, login_url='/usermodule/')
def edit_branch(request, branch_id):
    context = RequestContext(request)
    edited = False
    branch = Branch.objects.filter(pk=branch_id).first()
    if request.method == 'POST':
        branch_form = BranchForm(data=request.POST, instance=branch)
        if branch_form.is_valid():
            branch_form.save()
            edited = True
            return HttpResponseRedirect('/project/branch-list/')
        else:
            print branch_form.errors
    else:
        branch_form = BranchForm(instance=branch)
    return render_to_response(
        'project_data/edit_branch.html',
        {'id': branch_id, 'branch_form': branch_form,
         'edited': edited, 'branch_mgt': 'branch_mgt'},
        context)


@login_required
@user_passes_test(admin_check, login_url='/usermodule/')
def delete_branch(request, branch_id):
    context = RequestContext(request)
    branch = Branch.objects.get(pk=branch_id)
    branch.delete()
    return HttpResponseRedirect('/project/branch-list/')

@csrf_exempt
def check_for_delete(request):
    id = request.POST.get('id')
    # Dependency Check
    # First if it exists in usermodule_usermoduleprofile
    query_up = "select username from auth_user where id = any(select user_id from usermodule_usermoduleprofile where branch_id =" + str(id)+")"
    df_up = pandas.DataFrame()
    df_up = pandas.read_sql(query_up, connection)

    # if it exists in project_data_complain
    query_com = "select id from project_data_complain where pin_id = any(select user_id from usermodule_usermoduleprofile where branch_id = "+str(id)+")"
    df_com = pandas.DataFrame()
    df_com = pandas.read_sql(query_com, connection)

    extra_info= ""
    if df_up.empty and df_com.empty:
        dependency = 0
    elif not df_up.empty:
        extra_info = json.dumps(df_up.username.tolist())
        dependency = 1
    elif not df_com.empty:
        dependency = 2
    else:
        dependency = 3
    return HttpResponse(json.dumps({'dependency':dependency,'extra_info':extra_info}))


@csrf_exempt
def mobile_branch_verify(request):
    '''
    JSON field => model field
    address => address
    branch => name 
    code => branch_id
    '''
    if request.method == 'POST':
        data = request.POST.get("data", "xxx")
        json_obj = json.loads(data)
        # print ('json_obj',json_obj)
        branch = Branch.objects.filter(branch_id=json_obj['code'], status='active').first()
        # branch = Branch.objects.filter(name__icontains = json_obj['branch'], branch_id = json_obj['code'],status = 'active').first()
        if branch:
            return HttpResponse(status=200)
    return HttpResponse(content="Information not valid, please provide valid information", status=403)


@csrf_exempt
def mobile_registration(request):
    '''
	JSON field => model field
	pin => username
	name => first_name 
	password => password
	mobile => contact
	securityCode => security_code
    '''
    if request.method == 'POST':
        data = request.POST.get("data", "xxx")
        json_obj = json.loads(data)
        dj_user = User.objects.filter(username=json_obj['pin'], first_name=json_obj['name']).first()
        usermodule_user = UserModuleProfile.objects.filter(contact=json_obj['mobile']).first()
        if dj_user and usermodule_user:
            user_security_code = UserSecurityCode.objects.filter(user=dj_user).order_by('-generation_time').first()
            is_code_valid = False
            response_code = ''
            if user_security_code:
                # print "system time:", timezone.now()
                # print "db time:", user_security_code.generation_time
                # print "time_diff", time_diff.seconds
                time_diff = timezone.now() - user_security_code.generation_time
                validity_period = 5 * 60
                is_code_valid = time_diff.seconds <= validity_period

            if is_code_valid:
                response_code = user_security_code.code
            else:
                response_code = '{0:05}'.format(random.randint(1, 100000))
                new_user_security_code = UserSecurityCode(user=dj_user, code=response_code)
                new_user_security_code.save()
            return HttpResponse(response_code)
        else:
            return HttpResponse(content="Information not valid, please provide valid information", status=403)
        # dj_user.username = json_obj['pin']
        # dj_user.first_name = json_obj['name']
        # dj_user.password = make_password(json_obj['password'])
        # user_obj = dj_user.save()

        # usermodule_user = UserModuleProfile()
        # usermodule_user.contact = json_obj['mobile']
        # usermodule_user.security_code = json_obj['securityCode']

        # # usermodule required defaults
        # expiry_months_delta = 12
        # next_expiry_date = (datetime.today() + timedelta(expiry_months_delta*365/12))
        # usermodule_user.expired = next_expiry_date
        # usermodule_user.user = user_obj
        # usermodule_user.admin = False
        # usermodule_user.organisation_name = Organizations.objects.filter(pk=BRAC_ORD_ID).first()

        return HttpResponse("All Good")
    else:
        return HttpResponse(status=201)


@csrf_exempt
def mobile_user_activate(request):
    '''
	JSON field => model field
	pin => username
	name => first_name 
	__ => email
	password => password
	mobile => contact
	securityCode => security_code
    '''
    if request.method == 'POST':
        data = request.POST.get("data", "xxx")
        json_obj = json.loads(data)
        dj_user = User.objects.filter(username=json_obj['pin'], first_name=json_obj['name']).first()
        usermodule_user = UserModuleProfile.objects.filter(contact=json_obj['mobile']).first()
        user_security_code = UserSecurityCode.objects.filter(user=dj_user, code=json_obj['securityCode']).order_by(
            '-generation_time').first()
        is_code_valid = False
        if user_security_code:
            # validity_period = minutes * 60 seconds
            validity_period = 5 * 60
            time_diff = timezone.now() - user_security_code.generation_time
            is_code_valid = time_diff.seconds <= validity_period
            # print "system time:", timezone.now()
            # print "db time:", user_security_code.generation_time
            # print "time_diff", time_diff.seconds
        if dj_user and usermodule_user and is_code_valid:
            dj_user.password = make_password(json_obj['password'])
            dj_user.is_active = True
            dj_user.save()
            return HttpResponse("User Validated")
    return HttpResponse(content="Invalid Credentials", status=403)


@login_required
def report_accounts(request):
    from_date = '1971-03-26'
    to_date = '2999-03-26'
    q_objects_first_query = Q(execution_status='Executed') | Q(execution_status='Not Executed')
    q_objects_second_query = Q(status='Executed') | Q(status='Not Executed')
    if request.method == 'POST':
        from_date = request.POST.get('start', from_date)
        to_date = request.POST.get('end', to_date)
        service_type = request.POST.get('service_type', 'custom')
        account_no = request.POST.get('account_no', 'custom')
        brac_csa_agent_id = request.POST.get('brac_csa_agent_id', 'custom')
        bkash_exec_agent_id = request.POST.get('bkash_exec_agent_id', 'custom')
        # print from_date,to_date,service_type,account_no,brac_csa_agent_id,bkash_exec_agent_id
        if service_type != 'custom':
            q_objects_first_query &= Q(service_type=service_type)
        if account_no:
            q_objects_first_query &= Q(account_no=account_no)
        if brac_csa_agent_id != 'custom':
            q_objects_first_query &= Q(pin__id=brac_csa_agent_id)
        if bkash_exec_agent_id != 'custom':
            q_objects_second_query &= Q(bkash_agent__id=bkash_exec_agent_id)

    # print "here"
    q_objects_first_query &= Q(received_time__range=(from_date, to_date))  # Create an empty Q object to start with
    q_objects_second_query &= Q(change_time__range=(from_date, to_date))
    context = RequestContext(request)
    # complains = Complain.objects.filter(Q(execution_status='Executed') | Q(execution_status='Not Executed')).order_by("pk")
    complains = Complain.objects.filter(q_objects_first_query).order_by("pk")
    complain_list = []

    for complain in complains:
        # cmp_stat = ComplainStatusLog.objects.filter(Q(complain = complain) & Q(status='Executed') | Q(status='Not Executed')).order_by("-pk") # wrong query
        cmp_stat = ComplainStatusLog.objects.filter(Q(complain=complain) & q_objects_second_query).order_by(
            "-pk").first()

        if cmp_stat:
            ret_obj = {}
            ret_obj['id'] = str(complain.id)
            ret_obj['account_no'] = complain.account_no
            ret_obj['service_type'] = complain.service_type
            ret_obj['execution_status'] = complain.execution_status
            ret_obj['pin'] = complain.pin.username
            ret_obj['agent'] = cmp_stat.bkash_agent.username
            # ret_obj['transaction_date_time'] = formats.date_format(complain.transaction_date_time, "D d M Y H:i")
            ret_obj['received_time'] = formats.date_format(complain.received_time, "m/d/Y h:i:s")
            ret_obj['replied_time'] = formats.date_format(cmp_stat.change_time, "m/d/Y h:i:s")
            ret_obj['received_time_export'] = complain.received_time
            ret_obj['replied_time_export'] = cmp_stat.change_time
            seconds = (cmp_stat.change_time - complain.received_time).total_seconds()
            h = int(seconds // 3600)
            mn = int((seconds % 3600) // 60)
            sec = int((seconds % 3600) % 60)
            ret_obj['handling_time'] = "%d:%d:%d" % (
                h, mn, sec)  # str((cmp_stat.change_time - complain.received_time).total_seconds() // 3600)
            ret_obj['handling_time_export'] = seconds
            ret_obj['remarks_of_csa_customer'] = complain.remarks_of_csa_customer
            ret_obj['remarks_of_bkash_cs'] = complain.not_execute_reason
            complain_list.append(ret_obj)

    return_type = request.POST.get('export', 'nothing')
    if request.method == 'POST' and return_type == 'export':
        return export_report_accounts(complain_list)
    elif request.method == 'POST':
        return HttpResponse(json.dumps(complain_list, default=datetime_handler), content_type="application/json")

    # account no list
    accounts = Complain.objects.values('account_no').distinct()
    # csa users for filtering list
    csa_perm_map = TaskRolePermissionMap.objects.filter(name__name='Can Send Complain From App').first()
    brac_csa_users = UserModuleProfile.objects.filter(account_type=csa_perm_map.role).order_by('user__username')
    # bkash exec for filtering list
    bkash_exec_perm_map = TaskRolePermissionMap.objects.filter(name__name='Change Complain Status').first()
    bkash_exec_users = UserModuleProfile.objects.filter(account_type=bkash_exec_perm_map.role).order_by(
        'user__username')

    return render_to_response(
        'project_data/report_accounts.html',
        {'reports': 'reports', 'account': 'account', 'complains': complain_list, 'accounts': accounts,
         'brac_csa_users': brac_csa_users, 'bkash_exec_users': bkash_exec_users
         },
        context)


@login_required
def report_services(request):
    context = RequestContext(request)
    cursor = connection.cursor()

    from_date = "'1971-03-26'"
    to_date = "'2999-03-26'"
    if request.method == 'POST':
        from_date = "'" + request.POST.get('start', from_date) + " 00:00:00'"
        to_date = "'" + request.POST.get('end', to_date) + " 23:59:59'"
        print type(from_date)
    options_query = '''select service_type,request_offered,(executed+not_executed) request_replied, executed,not_executed, (request_offered - (executed+not_executed)) request_rectified,max_handled_time, avg_handled_time, min_handled_time from (
select service_type,get_request_count(service_type,''' + from_date + ''' , ''' + to_date + ''') as request_offered,
sum(executed_count) executed,sum(not_executed_count) not_executed,avg(solvetime) avg_handled_time,max(solvetime) max_handled_time,min(solvetime) min_handled_time from (
select *,getworkingtime(transaction_date_time ,resolvetime) solvetime from (
select id,service_type,execution_status,executed_count,not_executed_count,transaction_date_time,max(change_time) resolvetime from (
select pdc.id,pdc.service_type,pdc.execution_status ,pdc.received_time transaction_date_time,pdcs.change_time,(CASE WHEN pdc.execution_status='Executed' THEN 1  ELSE 0  END) AS executed_count,
(CASE WHEN pdc.execution_status='Not Executed' THEN 1 ELSE 0  END) AS not_executed_count
from project_data_complain pdc inner join project_data_complainstatuslog pdcs on pdc.id = pdcs.complain_id
where (pdc.execution_status = 'Executed' or pdc.execution_status = 'Not Executed') AND pdc.received_time between ''' + from_date + ''' AND ''' + to_date + ''') t
group by id,service_type,execution_status,executed_count,not_executed_count,transaction_date_time) resolve) complain_summary
group by service_type) inception
'''
    print options_query
    cursor.execute(options_query)
    data_list1 = dictfetchall(cursor)
    for data in data_list1:
        data['min_handled_time_export'] = data['min_handled_time']
        data['max_handled_time_export'] = data['max_handled_time']
        data['avg_handled_time_export'] = data['avg_handled_time']
        data['min_handled_time'] = seconds_to_formatted_time(int(data['min_handled_time']))
        data['max_handled_time'] = seconds_to_formatted_time(int(data['max_handled_time']))
        data['avg_handled_time'] = seconds_to_formatted_time(int(data['avg_handled_time']))

    return_type = request.POST.get('export', 'nothing')
    if request.method == 'POST' and return_type == 'export':
        return export_report_services(data_list1)
    elif request.method == 'POST':
        return HttpResponse(json.dumps(data_list1), content_type="application/json")
    # print days, hours, minutes, seconds
    return render_to_response(
        'project_data/report_services.html',
        {'reports': 'reports', 'service': 'service',
         'page_header': 'Service Report',
         'data_list1': data_list1},
        context)


def dashboard(request):

    now = datetime.now()
    now_minus_15 = now - timedelta(minutes=15)

    now_minus_7_days= now - timedelta(days=7)

    print now_minus_7_days


    from_date = str(now)
    to_date = str(now_minus_15)
    week_to_date=str(now_minus_7_days)

    context = RequestContext(request)
    cursor = connection.cursor()

    # service percentage
    servicequery = "with total_cnt as( select case when count(*) = 0 then 1 else count(*) end total from project_data_complain where received_time::date >= (current_date-interval '6 days')), t as ( select count(*) cnt from project_data_complain where received_time::date >= (current_date-interval '6 days') and execution_status = any('{Solved,Closed,Correction Needed}') and ticket_close_time is not null and extract(epoch from ticket_close_time-lock_date_time)::int between 0 and  extract(epoch from given_sla_time)::int )select round(cnt*100/total::float)::int service from t ,total_cnt"
    cursor.execute(servicequery)
    data_service = dictfetchall(cursor)

    # executed count
    table_query2 = "select COUNT(*) as requests  from project_data_complain where received_time >=(CURRENT_DATE - INTERVAL '6 day') and execution_status=any('{Solved}')  "
    cursor.execute(table_query2)
    data_list_tab1 = dictfetchall(cursor)

    # not executed count
    table_query3 = "select COUNT(*) as requests  from project_data_complain where received_time >=(CURRENT_DATE - INTERVAL '6 day') and execution_status=any('{Closed}')  "
    cursor.execute(table_query3)
    data_list_tab2 = dictfetchall(cursor)

    # Total Pending
    table_query4 = "select COUNT(*) as requests  from project_data_complain where received_time::date >=(CURRENT_DATE - INTERVAL '6 day') and execution_status= any('{New,Open,Corrected}') "
    cursor.execute(table_query4)
    data_list_tab3 = dictfetchall(cursor)


    # replied,offered, awt ,aht
    query2 = "WITH main_table AS( SELECT id, lock_date_time, ticket_close_time, csa_ticket_open_time, csa_ticket_close_time, reply_by, execution_status,sla FROM project_data_complain WHERE received_time::date >= (CURRENT_DATE-interval '6 days')),req_off AS ( SELECT count(*) ro FROM main_table), req_rep AS ( SELECT count(*) rr FROM main_table WHERE reply_by IS NOT NULL ), solved_tic AS ( SELECT CASE WHEN count(*) = 0 THEN 1 ELSE count(*) END total_solved FROM main_table WHERE execution_status = ANY('{Solved,Closed,Correction Needed}') ), aht_calc AS ( SELECT COALESCE(to_char(((sum(extract(epoch FROM sla::interval)::int)/total_solved) || ' second')::interval, 'HH24:MI:SS'),'00:00:00') aht FROM main_table, solved_tic GROUP BY total_solved ), awt_calc AS ( SELECT COALESCE(to_char(((sum(extract(epoch FROM sla::interval+(csa_ticket_close_time-csa_ticket_open_time))):: int/total_solved) || ' second')::interval, 'HH24:MI:SS'),'00:00:00') awt FROM main_table, solved_tic GROUP BY total_solved ) SELECT * FROM req_off, req_rep, aht_calc, awt_calc"
    cursor.execute(query2)
    data_list1 = dictfetchall(cursor)

    # request frequency line chart count
    query = ''' select (received_time::date) as name , count(received_time::date)  as value from project_data_complain WHERE received_time >=(CURRENT_DATE - INTERVAL '6 day') GROUP BY received_time::date order by received_time::date '''
    jsonForChart = generateChartData('name', 'value', query)

    # service distribution pie chart count
    query = "with t as( select count(*)::float total from project_data_complain where received_time::date >= (current_date-interval '6 days')), t1 as (select service_type,count(*) cnt,round(count(*)*100/total)::int percentage from project_data_complain,t where received_time::date >= (current_date-interval '6 days') group by service_type,total), tt as ( select 'New Registration' as service_type union all select 'Information Update' as service_type union all select 'Transaction Confirmation' as service_type union all select 'Pin Reset' as service_type union all select 'Bar' as service_type union all select 'Unbar' as service_type ) select tt.service_type,coalesce(cnt,0) cnt,coalesce(percentage,0) percentage from tt left join t1 on tt.service_type = t1.service_type order by service_type"
    df = pandas.DataFrame()
    df = pandas.read_sql(query,connection)
    service_type = df.service_type.tolist()
    count = df.cnt.tolist()
    percentage = df.percentage.tolist()
    service_distribution = {}
    service_distribution['service_type'] = service_type
    service_distribution['count'] = count
    service_distribution['percentage'] = percentage

    return render_to_response('project_data/dashboard.html',
        {'page_header': 'Service Report',
         'dashboard': 'dashboard',
         'data_list1': data_list1,
         'data_list_tab1': data_list_tab1,
         'data_list_tab2': data_list_tab2,
         'data_list_tab3': data_list_tab3,
         'data_service'  : data_service,
        'service_distribution': json.dumps(service_distribution),
         'jsonForChart': jsonForChart},context)


def dashboard_monthly(request):
    now = datetime.now()
    now_minus_15 = now - timedelta(minutes=15)
    now_minus_30_days = now - timedelta(days=30)



    from_date = str(now)
    to_date = str(now_minus_15)
    month_to_date=str(now_minus_30_days)
    print from_date
    print to_date

    context = RequestContext(request)
    cursor = connection.cursor()

    # service percentage
    servicequery = "with total_cnt as( select case when count(*) = 0 then 1 else count(*) end total from project_data_complain where received_time between date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 21 || ' days')::interval)::date and date_trunc('day',current_date+(EXTRACT(DOW FROM CURRENT_DATE)::int || ' days')::interval)::date ), t as ( select count(*) cnt from project_data_complain where received_time between date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 21 || ' days')::interval)::date and date_trunc('day',current_date+(EXTRACT(DOW FROM CURRENT_DATE)::int || ' days')::interval)::date  and execution_status = any('{Solved,Closed,Correction Needed}') and ticket_close_time is not null and extract(epoch from ticket_close_time-calculated_sla_time)::int >0 and extract(epoch from ticket_close_time-calculated_sla_time)::int <= extract(epoch from given_sla_time)::int )select round(cnt*100/total::float)::int service from t ,total_cnt"
    cursor.execute(servicequery)
    data_service = dictfetchall(cursor)

    now = datetime.now()

    context = RequestContext(request)
    cursor = connection.cursor()

    # executed count
    table_query2 = "select COUNT(*) as requests  from project_data_complain where received_time between date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 21 || ' days')::interval)::date and date_trunc('day',current_date+(EXTRACT(DOW FROM CURRENT_DATE)::int || ' days')::interval)::date  and execution_status=any('{Solved}')"
    cursor.execute(table_query2)
    data_list_tab1 = dictfetchall(cursor)

    # not executed count
    table_query3 = "select COUNT(*) as requests  from project_data_complain where received_time between date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 21 || ' days')::interval)::date and date_trunc('day',current_date+(EXTRACT(DOW FROM CURRENT_DATE)::int || ' days')::interval)::date and execution_status=any('{Closed}')"
    cursor.execute(table_query3)
    data_list_tab2 = dictfetchall(cursor)

    # Total Pending
    table_query4 = "select COUNT(*) as requests  from project_data_complain where received_time between date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 21 || ' days')::interval)::date and date_trunc('day',current_date+(EXTRACT(DOW FROM CURRENT_DATE)::int || ' days')::interval)::date and execution_status=any('{New,Open,Corrected}')"
    cursor.execute(table_query4)
    data_list_tab3 = dictfetchall(cursor)

    # replied,offered, awt ,aht
    query2 = "WITH main_table AS(SELECT id, lock_date_time, ticket_close_time, csa_ticket_open_time, csa_ticket_close_time, reply_by, execution_status,sla FROM project_data_complain WHERE received_time BETWEEN Date_trunc('day', current_date - ( Extract(dow FROM current_date) :: INT + 21 || ' days') :: interval) :: DATE AND Date_trunc('day', current_date + ( Extract(dow FROM current_date) :: INT || ' days' ) :: interval) :: DATE), req_off AS (SELECT Count(*) ro FROM main_table), req_rep AS (SELECT Count(*) rr FROM main_table WHERE reply_by IS NOT NULL), solved_tic AS (SELECT CASE WHEN Count(*) = 0 THEN 1 ELSE Count(*) END total_solved FROM main_table WHERE execution_status = ANY ( '{Solved,Closed,Correction Needed}' )), aht_calc AS (SELECT Coalesce(To_char(( ( SUM(Extract(epoch FROM sla::interval) :: INT) / total_solved ) || ' second' ) :: interval, 'HH24:MI:SS'), '00:00:00' ) aht FROM main_table, solved_tic GROUP BY total_solved), awt_calc AS (SELECT Coalesce(To_char(( ( SUM(Extract(epoch FROM sla::interval + ( csa_ticket_close_time - csa_ticket_open_time ))) :: INT / total_solved ) || ' second' ) :: interval, 'HH24:MI:SS'), '00:00:00' ) awt FROM main_table, solved_tic GROUP BY total_solved) SELECT * FROM req_off, req_rep, aht_calc, awt_calc"
    cursor.execute(query2)
    data_list1 = dictfetchall(cursor)

    # request frequency line chart count
    query = ''' select to_char(date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 21 || ' days')::interval)::date,'dd MON') || '-' || to_char(date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 15 || ' days')::interval)::date,'dd MON') as name, count(*) as value from project_data_complain where received_time between date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 21 || ' days')::interval)::date and date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 15 || ' days')::interval)::date union all select to_char(date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 14 || ' days')::interval)::date,'dd MON') || '-' || to_char(date_trunc('day',current_date- (EXTRACT(DOW FROM CURRENT_DATE)::int + 8 || ' days')::interval)::date,'dd MON') as name, count(*) as value from project_data_complain where received_time between date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 14 || ' days')::interval)::date and date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 8 || ' days')::interval)::date union all select to_char(date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 7 || ' days')::interval)::date,'dd MON') || '-' || to_char(date_trunc('day',current_date- (EXTRACT(DOW FROM CURRENT_DATE)::int + 1 || ' days')::interval)::date,'dd MON') as name, count(*) as value from project_data_complain where received_time between date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 7 || ' days')::interval)::date and date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 1 || ' days')::interval)::date union all select to_char(date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int || ' days')::interval)::date,'dd MON') || '-' || to_char(date_trunc('day',current_date+(EXTRACT(DOW FROM CURRENT_DATE)::int || ' days')::interval)::date,'dd MON') as name, count(*) as value from project_data_complain where received_time between date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int || ' days')::interval)::date and date_trunc('day',current_date+(EXTRACT(DOW FROM CURRENT_DATE)::int || ' days')::interval)::date'''
    jsonForChart = generateChartData('name', 'value', query)

    # service distribution pie chart count
    query = "with t as( select count(*)::float total from project_data_complain where received_time between date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 21 || ' days')::interval)::date and date_trunc('day',current_date+(EXTRACT(DOW FROM CURRENT_DATE)::int || ' days')::interval)::date ), t1 as (select service_type,count(*) cnt,round(count(*)*100/total)::int percentage from project_data_complain,t where received_time between date_trunc('day',current_date-(EXTRACT(DOW FROM CURRENT_DATE)::int + 21 || ' days')::interval)::date and date_trunc('day',current_date+(EXTRACT(DOW FROM CURRENT_DATE)::int || ' days')::interval)::date group by service_type,total), tt as ( select 'New Registration' as service_type union all select 'Information Update' as service_type union all select 'Transaction Confirmation' as service_type union all select 'Pin Reset' as service_type union all select 'Bar' as service_type union all select 'Unbar' as service_type ) select tt.service_type,coalesce(cnt,0) cnt,coalesce(percentage,0) percentage from tt left join t1 on tt.service_type = t1.service_type order by service_type"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    service_type = df.service_type.tolist()
    count = df.cnt.tolist()
    percentage = df.percentage.tolist()
    service_distribution = {}
    service_distribution['service_type'] = service_type
    service_distribution['count'] = count
    service_distribution['percentage'] = percentage


    return render_to_response(
        'project_data/dashboard_month.html',
        {'dashboard': 'dashboard',
         'page_header': 'Service Report',
         'data_list1': data_list1,
         'data_list_tab1': data_list_tab1,
         'data_list_tab2': data_list_tab2,
         'data_list_tab3': data_list_tab3,
         'data_service'  :data_service,
         'service_distribution':json.dumps(service_distribution),
         'jsonForChart': jsonForChart
         },
        context)

def wrap_and_encode(x):
    return encode("'%s'" % x)

def dashboard_yearly(request):
    now = datetime.now()
    now_minus_15 = now - timedelta(minutes=15)

    from_date = str(now)
    to_date = str(now_minus_15)

  
    year_from_date = str(date(date.today().year, 1, 1))
    year_to_date= str(date(date.today().year, 12, 31))

    context = RequestContext(request)
    cursor = connection.cursor()

    # service percentage
    servicequery = "with total_cnt as( select case when count(*) = 0 then 1 else count(*) end total from project_data_complain where received_time >= date_trunc('month', CURRENT_DATE-interval '11 months') ), t as ( select count(*) cnt from project_data_complain where received_time >= date_trunc('month', CURRENT_DATE-interval '11 months')  and execution_status = any('{Solved,Closed,Correction Needed}') and ticket_close_time is not null and extract(epoch from ticket_close_time-calculated_sla_time)::int >0 and extract(epoch from ticket_close_time-calculated_sla_time)::int <= extract(epoch from given_sla_time)::int )select round(cnt*100/total)::int service from t ,total_cnt"
    print servicequery
    cursor.execute(servicequery)
    data_service = dictfetchall(cursor)


    from_date = repr(year_from_date)
    to_date = repr(year_to_date)
    #print type(from_date)
    #print from_date
    #print type(to_date)


    context = RequestContext(request)
    cursor = connection.cursor()

    # executed count
    table_query2 = "select COUNT(*) as requests  from project_data_complain where received_time >= date_trunc('month', CURRENT_DATE-interval '11 months')  and execution_status=any('{Solved}') "
    cursor.execute(table_query2)
    data_list_tab1 = dictfetchall(cursor)

    # not executed count
    table_query3 = "select COUNT(*) as requests  from project_data_complain where received_time >= date_trunc('month', CURRENT_DATE-interval '11 months') and execution_status=any('{Closed}') "
    cursor.execute(table_query3)
    data_list_tab2 = dictfetchall(cursor)

    # Total Pending
    table_query4 = "select COUNT(*) as requests  from project_data_complain where received_time >= date_trunc('month', CURRENT_DATE-interval '11 months') and execution_status=any('{New,Open,Corrected}')  "
    cursor.execute(table_query4)
    data_list_tab3 = dictfetchall(cursor)

    # replied,offered, awt ,aht
    query2 = "WITH main_table AS( SELECT id, lock_date_time, ticket_close_time, csa_ticket_open_time, csa_ticket_close_time, reply_by, execution_status,sla FROM project_data_complain WHERE received_time >= date_trunc('month', CURRENT_DATE-interval '11 months')),req_off AS ( SELECT count(*) ro FROM main_table), req_rep AS ( SELECT count(*) rr FROM main_table WHERE reply_by IS NOT NULL ), solved_tic AS ( SELECT CASE WHEN count(*) = 0 THEN 1 ELSE count(*) END total_solved FROM main_table WHERE execution_status = ANY('{Solved,Closed,Correction Needed}') ), aht_calc AS ( SELECT COALESCE(to_char(((sum(extract(epoch FROM sla::interval)::int)/total_solved) || ' second')::interval, 'HH24:MI:SS'),'00:00:00') aht FROM main_table, solved_tic GROUP BY total_solved ), awt_calc AS ( SELECT COALESCE(to_char(((sum(extract(epoch FROM sla::interval+(csa_ticket_close_time-csa_ticket_open_time))):: int/total_solved) || ' second')::interval, 'HH24:MI:SS'),'00:00:00') awt FROM main_table, solved_tic GROUP BY total_solved ) SELECT * FROM req_off, req_rep, aht_calc, awt_calc "
    cursor.execute(query2)
    data_list1 = dictfetchall(cursor)

    # request frequency line chart count
    query=''' WITH t AS( SELECT To_char(received_time::date, 'Month') || to_char(received_time::date, 'YY') AS NAME, To_char(received_time::date, 'MM') AS mon, to_char(received_time::date, 'YY') as yer, Count(received_time:: date) AS value FROM project_data_complain WHERE received_time >= date_trunc('month', CURRENT_DATE-interval '11 months') GROUP BY mon,yer, NAME) SELECT NAME, value FROM t ORDER BY yer,mon'''
    jsonForChart = generateChartData('name', 'value', query)

    # service distribution pie chart count
    query = "with t as( select count(*)::float total from project_data_complain where received_time >= date_trunc('month', CURRENT_DATE-interval '11 months')), t1 as (select service_type,count(*) cnt,round(count(*)*100/total)::int percentage from project_data_complain,t where received_time >= date_trunc('month', CURRENT_DATE-interval '11 months') group by service_type,total), tt as ( select 'New Registration' as service_type union all select 'Information Update' as service_type union all select 'Transaction Confirmation' as service_type union all select 'Pin Reset' as service_type union all select 'Bar' as service_type union all select 'Unbar' as service_type ) select tt.service_type,coalesce(cnt,0) cnt,coalesce(percentage,0) percentage from tt left join t1 on tt.service_type = t1.service_type order by service_type"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    service_type = df.service_type.tolist()
    count = df.cnt.tolist()
    percentage = df.percentage.tolist()
    service_distribution = {}
    service_distribution['service_type'] = service_type
    service_distribution['count'] = count
    service_distribution['percentage'] = percentage


    return render_to_response(
        'project_data/dashboard_year.html',
        {'dashboard': 'dashboard',
         'page_header': 'Service Report',
         'data_list1': data_list1,
         'data_list_tab1': data_list_tab1,
         'data_list_tab2': data_list_tab2,
         'data_list_tab3': data_list_tab3,
         'data_service' : data_service,
         'service_distribution': json.dumps(service_distribution),
         'jsonForChart': jsonForChart

         },
        context)

@csrf_exempt
def getRangedData(request):
    from_date = request.POST.get('from_date')
    to_date = request.POST.get('to_date')
    # requests frequency
    query = "select (received_time::date) as name , count(received_time::date)  as value from project_data_complain WHERE received_time::date between '"+str(from_date)+"' and '"+str(to_date)+"' GROUP BY received_time::date order by received_time::date"
    jsonForChart = generateChartData('name', 'value', query)
    # Service Distribution
    query = "with t as( select count(*)::float total from project_data_complain where received_time::date between '"+str(from_date)+"' and '"+str(to_date)+"'), t1 as (select service_type,count(*) cnt,round( CAST(count(*) * 100/ total as numeric), 1) percentage from project_data_complain,t where received_time::date between '"+str(from_date)+"' and '"+str(to_date)+"' group by service_type,total), tt as ( select 'New Registration' as service_type union all select 'Information Update' as service_type union all select 'Transaction Confirmation' as service_type union all select 'Pin Reset' as service_type union all select 'Bar' as service_type union all select 'Unbar' as service_type ) select tt.service_type,coalesce(cnt,0) cnt,coalesce(percentage,0) percentage from tt left join t1 on tt.service_type = t1.service_type order by service_type"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    service_type = df.service_type.tolist()
    count = df.cnt.tolist()
    percentage = df.percentage.tolist()
    service_distribution = {}
    service_distribution['service_type'] = service_type
    service_distribution['count'] = count
    service_distribution['percentage'] = percentage

    # service
    query = "with total_cnt as( select case when count(*) = 0 then 1 else count(*) end total from project_data_complain where received_time::date between '"+str(from_date)+"' and '"+str(to_date)+"'), t as ( select count(*) cnt from project_data_complain where received_time::date between '"+str(from_date)+"' and '"+str(to_date)+"' and execution_status = any('{Solved,Closed,Correction Needed}') and ticket_close_time is not null AND Extract(epoch FROM ticket_close_time - lock_date_time)::INT between 0 AND Extract( epoch FROM given_sla_time) :: INT )select round(cnt*100/total::float)::int service from t ,total_cnt"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    service = df.service.tolist()[0] if not df.empty else 0

    # replied,offered, awt ,aht
    query = "WITH main_table AS(SELECT id, lock_date_time, ticket_close_time, csa_ticket_open_time, csa_ticket_close_time, reply_by, execution_status,sla FROM project_data_complain WHERE received_time :: DATE BETWEEN '"+str(from_date)+"' AND '"+str(to_date)+"'), req_off AS (SELECT Count(*) ro FROM main_table), req_rep AS (SELECT Count(*) rr FROM main_table WHERE reply_by IS NOT NULL), solved_tic AS (SELECT CASE WHEN Count(*) = 0 THEN 1 ELSE Count(*) END total_solved FROM main_table WHERE execution_status = ANY ( '{Solved,Closed,Correction Needed}')), aht_calc AS (SELECT Coalesce(To_char(( ( SUM(Extract(epoch from sla::interval) :: INT) / total_solved ) || ' second' ) :: interval, 'HH24:MI:SS'), '00:00:00' ) aht FROM main_table, solved_tic GROUP BY total_solved), awt_calc AS (SELECT Coalesce(To_char(( ( SUM(Extract(epoch FROM sla::interval + ( csa_ticket_close_time - csa_ticket_open_time ))) :: INT / total_solved ) || ' second' ) :: interval, 'HH24:MI:SS'), '00:00:00' ) awt FROM main_table, solved_tic GROUP BY total_solved) SELECT * FROM req_off, req_rep, aht_calc, awt_calc "
    print(query)
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    ro = df.ro.tolist()[0] if not df.empty else 0
    rr = df.rr.tolist()[0] if not df.empty else 0
    awt = df.awt.tolist()[0] if not df.empty else 0
    aht = df.aht.tolist()[0] if not df.empty else 0

    # pending
    query = "select COUNT(*) as pending  from project_data_complain where received_time::date between '"+str(from_date)+"' and '"+str(to_date)+"' and execution_status= any('{New,Open}')"
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    pending = df.pending.tolist()[0] if not df.empty else 0

    #not executed
    query = "select COUNT(*) as not_executed  from project_data_complain where received_time::date between '"+str(from_date)+"' and '"+str(to_date)+"' and execution_status=any('{Closed}')  "
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    not_executed = df.not_executed.tolist()[0] if not df.empty else 0

    # executed
    query = "select COUNT(*) as executed  from project_data_complain where received_time::date between '"+str(from_date)+"' and '"+str(to_date)+"' and execution_status=any('{Solved}')  "
    df = pandas.DataFrame()
    df = pandas.read_sql(query, connection)
    executed = df.executed.tolist()[0] if not df.empty else 0

    data = json.dumps({
        'jsonForChart':jsonForChart,
        'service_distribution':service_distribution,
        'ro':ro,'rr':rr,'awt':awt,'aht':aht,'service':service,'pending':pending,'not_executed':not_executed
        ,'executed':executed
    })

    return  HttpResponse(data)

def generateChartData(name_field, data_field, query):
    # print("Chart Query "+ str(query))
    dataset = __db_fetch_values_dict(query);
    #uniqueList = getUniqueValues(dataset, name_field)

    category_list = getUniqueValues(dataset, name_field)
    seriesData = []
    dict = {}
    dict['data'] = [nameTodata[data_field] for nameTodata in dataset]
    seriesData.append(dict)
    jsonForChart = json.dumps({'cat_list': category_list, 'total': seriesData},default=date_handler)
    # print("JSON CHART "+str(jsonForChart))
    return jsonForChart

    '''
    seriesData = []
    for ul in uniqueList:
        print(ul)
        dict = {}
        dict['name'] = ul;

        dict['data'] = [nameTodata[data_field] for nameTodata in dataset if nameTodata[name_field] == ul]
        seriesData.append(dict)

    jsonForChart = json.dumps({'cat_list': category_list, 'total': seriesData}, default=decimal_default)

    return jsonForChart
 '''

def getUniqueValues(dataset, colname):
    list = [];

    for dis in dataset:
        if dis[colname] in list:
            continue;
        else:
            list.append(dis[colname]);
    return list;

def date_handler(obj):
   return obj.isoformat() if hasattr(obj, 'isoformat') else obj


def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
        ]


def seconds_to_formatted_time(seconds):
    # days, seconds = divmod(seconds, 24*60*60)
    hours, seconds = divmod(seconds, 60 * 60)
    minutes, seconds = divmod(seconds, 60)
    # return str(days) + "days " + str(hours) + "hours " + str(minutes) +"minutes" + str(seconds) + "seconds"
    # return str(days) + "d " + str(hours).zfill(2) + ":" + str(minutes).zfill(2) +":" + str(seconds).zfill(2)
    return str(hours).zfill(2) + ":" + str(minutes).zfill(2) + ":" + str(seconds).zfill(2)


@login_required
def report_agents(request):
    context = RequestContext(request)
    cursor = connection.cursor()
    agent_role = TaskRolePermissionMap.objects.filter(name__name='Change Complain Status').first()
    userlist = UserModuleProfile.objects.filter(account_type=agent_role.role).order_by('user__username')

    start_time = (timezone.now() - timedelta(days=7)).date()
    end_time = (timezone.now() + timedelta(days=1)).date()
    # print start_time
    # print end_time

    from_date = "'1971-03-26'"
    to_date = "'2999-03-26'"
    options_query_extra = ''
    user_filter_query = ''
    data_exp_list = []
    if not request.user.is_superuser:
        logged_user = UserModuleProfile.objects.filter(user=request.user).first()
        current_user_role = UserRoleMap.objects.filter(user=logged_user).values('role_id').first()
        # print "##########################################" + str(current_user_role["role_id"])
        if current_user_role["role_id"] == 3:
            user_filter_query = ' and user_login_summary.user_id=' + str(request.user.id)

    if request.method == 'POST':
        # print "################################" + request.user.user_id
        from_date = "'" + request.POST.get('start', from_date) + "'"
        to_date = "'" + request.POST.get('end', to_date) + "'"
        agent_id = request.POST.get('agent_id', 'custom')

        if agent_id and agent_id != 'custom':
            options_query_extra = 'and complain_status.bkash_agent_id = ' + agent_id


            # print ('from_date',from_date)
    # print ('to_date',to_date)


    options_query = '''select transaction_date_time,username,(executed+not_executed) request_offered,(executed+not_executed) as request_replied,complain_status.avg_handled_time,user_login_summary.total_log_time from (
select bkash_agent_id,date_trunc('day',  transaction_date_time) transaction_date_time,
sum(executed_count) executed,sum(not_executed_count) not_executed,avg(solvetime) avg_handled_time from (
select *,(EXTRACT(EPOCH FROM resolvetime) - EXTRACT(EPOCH FROM transaction_date_time)) solvetime from (
select id,bkash_agent_id,execution_status,executed_count,not_executed_count,transaction_date_time,max(change_time) resolvetime 
from ( select pdc.id,pdcs.bkash_agent_id,pdc.execution_status ,pdc.received_time transaction_date_time,pdcs.change_time,
(CASE WHEN pdc.execution_status='Executed' THEN 1  ELSE 0  END) AS executed_count,
(CASE WHEN pdc.execution_status='Not Executed' THEN 1 ELSE 0  END) AS not_executed_count
from project_data_complain pdc inner join project_data_complainstatuslog pdcs on pdc.id = pdcs.complain_id
where (pdc.execution_status = 'Executed' or pdc.execution_status = 'Not Executed') and (pdcs.status = 'Executed' or pdcs.status = 'Not Executed') AND pdc.received_time between ''' + from_date + ''' AND ''' + to_date + ''') t group by id,bkash_agent_id,execution_status,executed_count,not_executed_count,transaction_date_time
 ) resolve ) complain_summary
group by bkash_agent_id,date_trunc('day',  transaction_date_time)) complain_status,
(select login_summary.*,username from (Select user_id,date_trunc('day',  login_time) login_time, sum(EXTRACT (EPOCH FROM (logout_time::timestamp(0) - login_time::timestamp(0)))) total_log_time from usermodule_useraccesslog
where login_time>=''' + from_date + ''' and logout_time<=''' + to_date + ''' group by user_id,date_trunc('day',  login_time)
)login_summary,auth_user where login_summary.user_id=auth_user.id)user_login_summary
where user_login_summary.user_id=complain_status.bkash_agent_id and user_login_summary.login_time=complain_status.transaction_date_time
''' + options_query_extra + user_filter_query
    # print ('options_query--------------------------------------')
    # print options_query
    cursor.execute(options_query)
    data_list = dictfetchall(cursor)
    for data in data_list:
        # print data
        data_obj = {}
        data_obj['transaction_date_time'] = formats.date_format(data['transaction_date_time'],
                                                                "d/m/Y")  # str(data['transaction_date_time'])
        data_obj['username'] = data['username']
        data_obj['total_log_time'] = seconds_to_formatted_time(int(data['total_log_time']))
        data_obj['avg_handled_time'] = seconds_to_formatted_time(int(data['avg_handled_time']))
        data_obj['request_offered'] = int(data['request_offered'])
        data_obj['request_replied'] = int(data['request_replied'])
        data_exp_list.append(data_obj)

    return_type = request.POST.get('export', 'nothing')
    if request.method == 'POST' and return_type == 'export':
        # print('data export data_list')
        # print data_exp_list
        return export_report_agents(data_exp_list)
    elif request.method == 'POST':
        return HttpResponse(json.dumps(data_exp_list), content_type="application/json")

    return render_to_response(
        'project_data/report_agents.html',
        {'reports': 'reports', 'agent': 'agent', 'userlist': userlist,
         'page_header': 'Agents Report', 'data_list': data_exp_list
         },
        context)


@login_required
def report_agents_performance(request):
    context = RequestContext(request)
    cursor = connection.cursor()
    agent_role = TaskRolePermissionMap.objects.filter(name__name='Change Complain Status').first()
    userlist = UserModuleProfile.objects.filter(account_type=agent_role.role).order_by('user__username')

    start_time = (timezone.now() - timedelta(days=7)).date()
    end_time = (timezone.now() + timedelta(days=1)).date()

    # print start_time
    # print end_time

    from_date = '1971-03-26'
    to_date = '2999-03-26'
    options_query_extra = ''
    user_filter_query = ''
    if not request.user.is_superuser:
        logged_user = UserModuleProfile.objects.filter(user=request.user).first()
        current_user_role = UserRoleMap.objects.filter(user=logged_user).values('role_id').first()
        # print "##########################################" + str(current_user_role["role_id"])
        if current_user_role["role_id"] == 3:
            from_date = start_time
            # print end_time.strftime('%Y-%m-%d')

            # print from_date
            to_date = end_time
            # print to_date
            user_filter_query = ' and cpsummary.bkash_agent_id=' + str(request.user.id)

    if request.method == 'POST':
        # print "################################" + request.user.user_id
        from_date = " " + request.POST.get('start', from_date) + "  00:00:00 "
        # print from_date
        to_date = " " + request.POST.get('end', to_date) + " 23:59:59 "
        # print to_date
        agent_id = request.POST.get('agent_id', 'custom')

        if agent_id and agent_id != 'custom':
            options_query_extra = 'and cpsummary.bkash_agent_id = ' + agent_id

    options_query = "select cpsummary.id,pin, account_no, service_type, received_time,execution_status,remarks_of_bkash_cs,change_time, bkash_agent_id,username from( select cp.*,cplog.change_time, bkash_agent_id from(SELECT id,pin_id pin, account_no, service_type, received_time,execution_status,remarks_of_bkash_cs FROM project_data_complain where (execution_status='Executed' or execution_status='Not Executed' or execution_status='Escalated') and received_time between '" + str(
        from_date) + "' and '" + str(
        to_date) + "') cp, (SELECT complain_id, change_time, bkash_agent_id FROM project_data_complainstatuslog where (status='Executed' or status='Not Executed'))cplog where cp.id=cplog.complain_id) cpsummary,auth_user where auth_user.id=cpsummary.bkash_agent_id " + options_query_extra + user_filter_query

    # print options_query
    cursor.execute(options_query)
    data_list = dictfetchall(cursor)
    data_exp_list = []
    # print data_list
    for data in data_list:
        # data['Ticket_ID']
        data_obj = {}

        c_branch = UserModuleProfile.objects.filter(user=data['pin']).values('branch_id').first()
        # print c_branch
        branch = Branch.objects.filter(pk=c_branch["branch_id"]).values('branch_id').first()
        # print branch

        if branch is not None:
            data_obj['Ticket_ID'] = str(branch["branch_id"]) + ('%05d' % data['id'])
            # data_obj['Ticket_ID'] =  '%05d' % data['id']
        else:
            data_obj["Ticket_ID"] = '%05d' % data['id']

        # current_user_role = UserRoleMap.objects.filter(user=logged_user).values('role_id').first()
        data_obj['Request_Date'] = str(formats.date_format(data['received_time'], "m/d/Y h:i:s"))
        data_obj['Execution_Date'] = str(formats.date_format(data['change_time'], "m/d/Y h:i:s"))
        data_obj['Request_Date_export'] = data['received_time']
        data_obj['Execution_Date_export'] = data['change_time']
        data_obj['account_no'] = str(data['account_no'])
        data_obj['service_type'] = str(data['service_type'])
        data_obj['execution_status'] = str(data['execution_status'])
        data_obj['Executed_by'] = str(data['username'])
        data_obj['remarks_of_bkash_cs'] = str(data['remarks_of_bkash_cs'])

        data_exp_list.append(data_obj)
    # print data_exp_list
    return_type = request.POST.get('export', 'nothing')
    if request.method == 'POST' and return_type == 'export':
        return export_report_agents_performance(data_exp_list)
    elif request.method == 'POST':
        return HttpResponse(json.dumps(data_exp_list, default=datetime_handler), content_type="application/json")

    return render_to_response(
        'project_data/report_agents_performance.html',
        {'reports': 'reports', 'agent_performance': 'agent_performance', 'userlist': userlist,
         'page_header': 'Agents Performance Report', 'data_list': data_exp_list
         },
        context)


@login_required
def report_agents_activity(request):
    # print 'Test Agent Activity'
    context = RequestContext(request)
    cursor = connection.cursor()
    agent_role = TaskRolePermissionMap.objects.filter(name__name='Change Complain Status').first()
    userlist = UserModuleProfile.objects.filter(account_type=agent_role.role).order_by('user__username')

    start_time = (timezone.now() - timedelta(days=7)).date()
    end_time = (timezone.now() + timedelta(days=1)).date()
    # print type(start_time)

    # print start_time
    # print end_time

    from_date = '1971-03-26'
    to_date = '2999-03-26'
    options_query_extra = ''
    # user_filter_query = ''
    if not request.user.is_superuser:
        logged_user = UserModuleProfile.objects.filter(user=request.user).first()
        current_user_role = UserRoleMap.objects.filter(user=logged_user).values('role_id').first()
        # print "##########################################" + str(current_user_role["role_id"])
        if current_user_role["role_id"] == 3:
            from_date = start_time
            # print end_time.strftime('%Y-%m-%d')

            # print from_date
            to_date = end_time
            # print to_date
            user_filter_query = ' and auth_user.id=' + str(request.user.id)
            # options_query_extra = 'and auth_user.id = ' + agent_id

    if request.method == 'POST':
        # print "################################" + request.user.user_id
        from_date = " " + request.POST.get('start', from_date) + "  00:00:00 "
        # print from_date
        to_date = " " + request.POST.get('end', to_date) + " 23:59:59 "
        # print to_date
        agent_id = request.POST.get('agent_id', 'custom')
        # print agent_id

        if agent_id and agent_id != 'custom':
            options_query_extra = 'and auth_user.id = ' + agent_id
            # print options_query_extra

    options_query = "select username,login_time,logout_time,user_ip,user_browser from  public.usermodule_useraccesslog inner join public.auth_user on public.usermodule_useraccesslog.user_id=public.auth_user.id where login_time>='" + str(
        from_date) + "' and logout_time<='" + str(to_date) + "' " + options_query_extra

    # print options_query
    cursor.execute(options_query)
    data_list = dictfetchall(cursor)
    data_exp_list = []
    # print data_list
    for data in data_list:
        # data['Ticket_ID']
        data_obj = {}



        # current_user_role = UserRoleMap.objects.filter(user=logged_user).values('role_id').first()
        data_obj['login_time'] = str(formats.date_format(data['login_time'], "m/d/Y h:i:s"))
        data_obj['logout_time'] = str(formats.date_format(data['logout_time'], "m/d/Y h:i:s"))

        data_obj['user_browser'] = data['user_browser']
        data_obj['user_ip'] = str(data['user_ip'])
        data_obj['username'] = str(data['username'])
        # data_obj['remarks_of_bkash_cs'] = str(data['remarks_of_bkash_cs'])

        data_exp_list.append(data_obj)
    # print data_exp_list
    return_type = request.POST.get('export', 'nothing')
    if request.method == 'POST' and return_type == 'export':
        return export_report_agents_activity(data_exp_list)
    elif request.method == 'POST':
        return HttpResponse(json.dumps(data_exp_list, default=datetime_handler), content_type="application/json")

    return render_to_response(
        'project_data/report_agents_activity.html',
        {'reports': 'reports', 'agents_activity_report': 'agents_activity_report', 'userlist': userlist,
         'page_header': 'Agents Activity Report', 'data_list': data_exp_list
         },
        context)


'''
@login_required
def chart_data_json(request):
    data = {}
    params = request.GET

    days = params.get('days', 0)
    name = params.get('name', '')
    if name == 'avg_by_day':
        data['chart_data'] = ChartData.get_avg_by_day(
            user=request.user, days=int(days))

    return HttpResponse(json.dumps(data), content_type='application/json')

'''


@login_required
def report_customer_service_status(request):
    from_date = '1971-03-26'
    to_date = '2999-03-26'
    q_objects_first_query = Q(execution_status='Executed') | Q(execution_status='Not Executed') | Q(
        execution_status='Escalated')
    if request.method == 'POST':
        # from_date = request.POST.get('start', from_date)
        # to_date = request.POST.get('end', to_date)
        service_type = request.POST.get('service_type', 'custom')
        status = request.POST.get('status', 'custom')
        branch = request.POST.get('branch', 'custom')
        region = request.POST.get('region', 'custom')

        # brac_csa_agent_id = request.POST.get('brac_csa_agent_id', 'custom')
        # bkash_exec_agent_id = request.POST.get('bkash_exec_agent_id', 'custom')
        # print from_date,to_date,service_type,brac_csa_agent_id,bkash_exec_agent_id
        if status != 'custom':
            q_objects_first_query = Q(execution_status=status)
        else:
            q_objects_first_query = Q(execution_status='Executed') | Q(execution_status='Not Executed') | Q(
                execution_status='Escalated')

        if branch != 'custom':
            q_objects_first_query &= Q(pin__usermoduleprofile__branch__pk=branch)  #

        if service_type != 'custom':
            q_objects_first_query &= Q(service_type=service_type)
        if region != 'custom':
            q_objects_first_query &= Q(pin__usermoduleprofile__region__pk=region)
    else:
        q_objects_first_query = Q(execution_status='Executed') | Q(execution_status='Not Executed') | Q(
            execution_status='Escalated')
    branches = Branch.objects.filter(status='active').order_by("name")
    q_objects_first_query &= Q(
        transaction_date_time__range=(from_date, to_date))  # Create an empty Q object to start with
    context = RequestContext(request)
    complains = Complain.objects.filter(q_objects_first_query).order_by("pk")
    complain_list = []
    for complain in complains:
        ret_obj = {}
        ret_obj['token_no'] = str(complain.id)
        ret_obj['branch_name'] = complain.pin.usermoduleprofile.branch.name if (
            hasattr(complain.pin,
                    'usermoduleprofile') and complain.pin.usermoduleprofile.branch is not None)  else 'N/A'
        ret_obj['region_name'] = complain.pin.usermoduleprofile.region.name if (
            hasattr(complain.pin,
                    'usermoduleprofile') and complain.pin.usermoduleprofile.region is not None)  else 'N/A'
        ret_obj['service_type'] = complain.service_type
        ret_obj['execution_status'] = complain.execution_status
        ret_obj['not_execute_reason'] = complain.not_execute_reason
        complain_list.append(ret_obj)

    return_type = request.POST.get('export', 'nothing')
    if request.method == 'POST' and return_type == 'export':
        return export_report_customer_service_status(complain_list)
    elif request.method == 'POST':
        return HttpResponse(json.dumps(complain_list), content_type="application/json")

    # csa users for filtering list
    csa_perm_map = TaskRolePermissionMap.objects.filter(name__name='Can Send Complain From App').first()
    brac_csa_users = UserModuleProfile.objects.filter(account_type=csa_perm_map.role)
    # bkash exec for filtering list
    bkash_exec_perm_map = TaskRolePermissionMap.objects.filter(name__name='Change Complain Status').first()
    bkash_exec_users = UserModuleProfile.objects.filter(account_type=bkash_exec_perm_map.role)
    # regions names
    regions = Region.objects.order_by("name")

    return render_to_response(
        'project_data/report_customer_service_status.html',
        {'reports': 'reports', 'customer_service': 'customer_service', 'complains': complain_list, 'branches': branches,
         'brac_csa_users': brac_csa_users, 'bkash_exec_users': bkash_exec_users,
         'page_header': 'Customer Service Status Report', 'regions': regions,
         },
        context)


@login_required
@user_passes_test(admin_check, login_url='/usermodule/')
def add_role_task_permission(request):
    context = RequestContext(request)
    form = TaskRolePermissionMapForm(data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/project/task-role-permission-list/')
        else:
            print form.errors
    return render_to_response(
        'project_data/add_role_task_permission.html',
        {'form': form, 'task_role_mgt': 'task_role_mgt'},
        context)


@login_required
@user_passes_test(admin_check, login_url='/usermodule/')
def role_task_permission_list(request):
    user = UserModuleProfile.objects.filter(user_id=request.user.id).first()
    admin = user.admin if user else True
    context = RequestContext(request)
    task_roles = TaskRolePermissionMap.objects.all().order_by("pk")
    return render_to_response(
        'project_data/role_task_permission_list.html',
        {'task_roles': task_roles, 'task_role_mgt': 'task_role_mgt', 'admin': 'admin'},
        context)


@login_required
@user_passes_test(admin_check, login_url='/usermodule/')
def edit_role_task_permission(request, tast_role_id):
    context = RequestContext(request)
    edited = False
    task_role = TaskRolePermissionMap.objects.filter(pk=tast_role_id).first()

    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        task_role_form = TaskRolePermissionMapForm(data=request.POST, instance=task_role)

        # If the two forms are valid...
        if task_role_form.is_valid():
            edited_user = task_role_form.save(commit=False);
            edited_user.save()
            edited = True
            return HttpResponseRedirect('/project/task-role-permission-list/')
        else:
            print task_role_form.errors

    # Not a HTTP POST, so we render our form using two ModelForm instances.
    # These forms will be blank, ready for user input.
    else:
        task_role_form = TaskRolePermissionMapForm(instance=task_role)

    return render_to_response(
        'project_data/edit_role_task_permission.html',
        {'id': tast_role_id, 'task_role_form': task_role_form,
         'edited': edited, 'task_role_mgt': 'task_role_mgt'},
        context)


@login_required
@user_passes_test(admin_check, login_url='/usermodule/')
def delete_task_role(request, tast_role_id):
    context = RequestContext(request)
    task_role = TaskRolePermissionMap.objects.get(pk=tast_role_id)
    task_role.delete()
    return HttpResponseRedirect('/project/task-role-permission-list/')


@login_required
@user_passes_test(admin_check, login_url='/usermodule/')
def add_task(request):
    context = RequestContext(request)
    form = TaskForm(data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/project/task-list/')
        else:
            print form.errors
    return render_to_response(
        'project_data/add_task.html',
        {'form': form, 'task_mgt': 'task_mgt'},
        context)


@login_required
@user_passes_test(admin_check, login_url='/usermodule/')
def task_list(request):
    user = UserModuleProfile.objects.filter(user_id=request.user.id).first()
    admin = user.admin if user else True
    context = RequestContext(request)
    tasks = Task.objects.all().order_by("pk")
    return render_to_response(
        'project_data/task_list.html',
        {'tasks': tasks, 'task_mgt': 'task_mgt', 'admin': admin},
        context)


@login_required
@user_passes_test(admin_check, login_url='/usermodule/')
def edit_task(request, task_id):
    context = RequestContext(request)
    edited = False
    task = Task.objects.filter(pk=task_id).first()
    if request.method == 'POST':
        task_form = TaskForm(data=request.POST, instance=task)
        if task_form.is_valid():
            edited_user = task_form.save(commit=False);
            edited_user.save()
            edited = True
            return HttpResponseRedirect('/project/task-list/')
        else:
            print task_form.errors
    else:
        task_form = TaskForm(instance=task)
    return render_to_response(
        'project_data/edit_task.html',
        {'id': task_id, 'task_form': task_form,
         'edited': edited, 'task_mgt': 'task_mgt'},
        context)


@login_required
@user_passes_test(admin_check, login_url='/usermodule/')
def delete_task(request, task_id):
    context = RequestContext(request)
    task_role = Task.objects.get(pk=tast_id)
    task_role.delete()
    return HttpResponseRedirect('/usermodule/roles-list')


@login_required
@user_passes_test(admin_check, login_url='/usermodule/')
def send_global_message(request):
    context = RequestContext(request)
    form = NotificationForm(data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            complain_topic = "/CSA/1"
            notification = form.save(commit=False)
            data_message = {
                "service_type": "",
                "title": "Message for All BRAC CSA",
                "message": notification.message,
                "service_id": ""
            }
            query = "select firebase_token from user_device_map where mac_address !='' and mac_address is not null"
            df = pandas.DataFrame()
            df = pandas.read_sql(query,connection)
            if not df.empty:
                list = df.firebase_token.tolist()
                registration_id = []
                for each in list:
                    registration_id.append(each)
                result = push_service.notify_multiple_devices(registration_ids=registration_id, message_title="",
                                                          message_body="", data_message=data_message)
            # send_push_msg(topic=complain_topic, payload=notification.message)
            notification.sender = request.user
            notification.save()
            return HttpResponseRedirect('/project/global-message-history/')
        else:
            print form.errors
    return render_to_response(
        'project_data/send_global_message.html',
        {'form': form, 'notification_mgt': 'notification_mgt', 'notification_add': 'notification_add'},
        context)


@login_required
# @user_passes_test(admin_check,login_url='/usermodule/')
def global_message_history(request):
    context = RequestContext(request)
    notifications = Notification.objects.all().order_by("pk")
    return render_to_response(
        'project_data/global_message_history.html',
        {'notifications': notifications, 'notification_mgt': 'notification_mgt',
         'notification_list': 'notification_list'},
        context)


def sms_test(request):
    # def sms_test(request, to_number = '', message = 'Hello'):
    url = 'http://mydesk.brac.net/sms/api/push'  # Set destination URL here
    # url = 'http://kobo.mpower-social.com:8008/project/sms-status/' # Set destination URL here
    post_fields = {'t': SMS_API_TOKEN, 'to_number': '01985468227', 'message': 'Hi 33'}

    # request = Request(url, urlencode(post_fields).encode())
    # json = urlopen(request).read().decode()
    # print(json)


    # query_args = { 'q':'query string', 'foo':'bar' }
    # encoded_args = urllib.urlencode(post_fields)
    # # url = 'http://localhost:8080/'
    # print encoded_args
    # json =  urllib2.urlopen(url, encoded_args).read()
    # print json
    import urllib
    import urllib2

    data = urllib.urlencode(post_fields)
    # print data
    req = urllib2.Request(url, data)
    # req.add_header('HTTP_REFERER', 'http://kobo.mpower-social.com:8008/')
    # print req
    response = urllib2.urlopen(req)
    the_page = response.read()
    # print the_page
    return HttpResponse(the_page)


@csrf_exempt
def sms_status(request):
    # for i in request.POST:
    # print i
    # print "key: %s , value: %s" % (i, request.POST[i])
    # print "######################################"
    # print request.META.get('HTTP_REFERER')
    for key, value in request.POST.iteritems():
        # print "####"
        print key
        print value
        # print "####"

    return HttpResponse("200")


def export_report_customer_service_status(data_list1):
    wb = xlwt.Workbook()
    ws = wb.add_sheet('CSS Report')
    report_filename = 'Customer_service_status_report'
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=Customer_service_status_report.xls'
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet(str(report_filename))
    style0 = xlwt.easyxf('font: name Times New Roman, color-index red, bold on',
                         num_format_str='#,##0.00')
    style1 = xlwt.easyxf(num_format_str='D-MMM-YY')
    style2 = xlwt.easyxf('font: name Times New Roman, color-index black, bold on',
                         num_format_str='#,##0.00')
    row = 0
    ws.write((row), 0, "Token No.", style2)
    ws.write((row), 1, "Region", style2)
    ws.write((row), 2, "Branch Name", style2)
    ws.write((row), 3, "Service Type", style2)
    ws.write((row), 4, "Execution Status", style2)
    ws.write((row), 5, "Not Execution Reason", style2)

    row += 1
    for data in data_list1:
        col = 0
        ws.write((row), col, data['token_no'], style2)
        ws.write((row), col + 1, data['region_name'], style2)
        ws.write((row), col + 2, data['branch_name'], style2)
        ws.write((row), col + 3, data['service_type'], style2)
        ws.write((row), col + 4, data['execution_status'], style2)
        ws.write((row), col + 5, data['not_execute_reason'], style2)
        row += 1
    wb.save(response)
    return response


def export_report_accounts(data_list):
    date_format = xlwt.XFStyle()
    date_format.num_format_str = 'mm/dd/yyyy'
    time_format = xlwt.XFStyle()
    time_format.num_format_str = 'h:mm:ss'
    wb = xlwt.Workbook()
    ws = wb.add_sheet('Accounts Report')
    report_filename = 'report_accounts'
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=report_accounts.xls'
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet(str(report_filename))
    style0 = xlwt.easyxf('font: name Times New Roman, color-index red, bold on',
                         num_format_str='#,##0.00')
    style1 = xlwt.easyxf(num_format_str='D-MMM-YY')
    style2 = xlwt.easyxf('font: name Times New Roman, color-index black, bold on',
                         num_format_str='#,##0.00')
    row = 0
    ws.write((row), 0, "Serial", style2)
    ws.write((row), 1, "Account No.", style2)
    ws.write((row), 2, "Service Type", style2)
    ws.write((row), 3, "Execution Status", style2)
    ws.write((row), 4, "BRAC Agent", style2)
    ws.write((row), 5, "bKash Agent", style2)
    # ws.write( (row), 6, "Date",style2)
    ws.write((row), 7, "Request Time", style2)
    ws.write((row), 8, "Replied Time", style2)
    ws.write((row), 9, "Handling Time", style2)
    ws.write((row), 10, "Remarks(BRAC CSA)", style2)
    ws.write((row), 11, "Remarks(bKash Executive)", style2)
    row += 1
    for data in data_list:
        col = 0
        ws.write((row), col, data['id'], style2)
        ws.write((row), col + 1, data['account_no'], style2)
        ws.write((row), col + 2, data['service_type'], style2)
        ws.write((row), col + 3, data['execution_status'], style2)
        ws.write((row), col + 4, data['pin'], style2)
        ws.write((row), col + 5, data['agent'], style2)
        # ws.write( (row), col+6, data['transaction_date_time'],style2)
        ws.write((row), col + 7, data['received_time_export'], date_format)
        ws.write((row), col + 8, data['replied_time_export'], date_format)
        # ws.write((row), col + 9, data['handling_time_export'], time_format)
        # ws.write((row), col + 9, datetime.strptime(data['handling_time'], "%H:%M:%S").time(), time_format)
        ws.write((row), col + 9, data['handling_time'], time_format)
        ws.write((row), col + 10, data['remarks_of_csa_customer'], style2)
        ws.write((row), col + 11, data['remarks_of_bkash_cs'], style2)
        row += 1
    wb.save(response)
    return response


def export_report_services(data_list):
    time_format = xlwt.XFStyle()
    time_format.num_format_str = 'h:mm:ss'
    wb = xlwt.Workbook()
    ws = wb.add_sheet('Services Report')
    report_filename = 'report_services'
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=report_services.xls'
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet(str(report_filename))
    style0 = xlwt.easyxf('font: name Times New Roman, color-index red, bold on',
                         num_format_str='#,##0.00')
    style1 = xlwt.easyxf(num_format_str='D-MMM-YY')
    style2 = xlwt.easyxf('font: name Times New Roman, color-index black, bold on',
                         num_format_str='#,##0.00')
    row = 0
    ws.write((row), 0, "Service Type", style2)
    ws.write((row), 1, "Request Offered", style2)
    ws.write((row), 2, "Request Replied", style2)
    ws.write((row), 3, "Request Executed", style2)
    ws.write((row), 4, "Request Not Executed", style2)
    ws.write((row), 5, "Request Rectified", style2)
    ws.write((row), 6, "AHT(Average Handled Time)", style2)
    ws.write((row), 7, "Longest Wait Time", style2)
    ws.write((row), 8, "Lowest Wait Time", style2)
    row += 1
    for data in data_list:
        col = 0
        ws.write((row), col, data['service_type'], style2)
        ws.write((row), col + 1, data['request_offered'], style2)
        ws.write((row), col + 2, data['request_replied'], style2)
        ws.write((row), col + 3, data['executed'], style2)
        ws.write((row), col + 4, data['not_executed'], style2)
        ws.write((row), col + 5, data['request_rectified'], style2)
        ws.write((row), col + 6, data['avg_handled_time_export'], time_format)
        ws.write((row), col + 7, data['max_handled_time_export'], time_format)
        ws.write((row), col + 8, data['min_handled_time_export'], time_format)
        row += 1
    wb.save(response)
    return response


def export_report_agents(data_list):
    time_format = xlwt.XFStyle()
    time_format.num_format_str = 'HH:MM:SS'
    wb = xlwt.Workbook()
    ws = wb.add_sheet('Agent Report')
    report_filename = 'report_agents'
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=report_agents.xls'
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet(str(report_filename))
    style0 = xlwt.easyxf('font: name Times New Roman, color-index red, bold on',
                         num_format_str='#,##0.00')
    style1 = xlwt.easyxf(num_format_str='D-MMM-YY')
    style2 = xlwt.easyxf('font: name Times New Roman, color-index black, bold on',
                         num_format_str='#,##0.00')
    row = 0
    ws.write((row), 0, "Date", style2)
    ws.write((row), 1, "bKash Agent Name(Emp)", style2)
    ws.write((row), 2, "Total Login Time", style2)
    ws.write((row), 3, "Average Handled Time", style2)
    ws.write((row), 4, "Request Offered", style2)
    ws.write((row), 5, "Request Replied", style2)
    row += 1
    for data in data_list:
        col = 0
        ws.write((row), col, data['transaction_date_time'], style2)
        ws.write((row), col + 1, data['username'], style2)
        ws.write((row), col + 2, data['total_log_time'], time_format)
        ws.write((row), col + 3, data['avg_handled_time'], time_format)
        ws.write((row), col + 4, data['request_offered'], style2)
        ws.write((row), col + 5, data['request_replied'], style2)
        row += 1
    wb.save(response)
    return response


def export_report_agents_performance(data_list):
    date_format = xlwt.XFStyle()
    date_format.num_format_str = 'dd/mm/yyyy'
    wb = xlwt.Workbook()
    ws = wb.add_sheet('Agent Report performance')
    report_filename = 'report_agents_performance'
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=report_agents_performance.xls'
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet(str(report_filename))
    style0 = xlwt.easyxf('font: name Times New Roman, color-index red, bold on',
                         num_format_str='#,##0.00')
    style1 = xlwt.easyxf(num_format_str='D-MMM-YY')
    style2 = xlwt.easyxf('font: name Times New Roman, color-index black, bold on',
                         num_format_str='#,##0.00')
    row = 0
    ws.write((row), 0, "Ticket ID", style2)
    ws.write((row), 1, "Request Date & Time", style2)
    ws.write((row), 2, "Execution Date & Time", style2)
    ws.write((row), 3, "Account No.", style2)
    ws.write((row), 4, "Service Type", style2)
    ws.write((row), 5, "Execution Status(Executed/not Executed)", style2)
    ws.write((row), 6, "Executed By", style2)
    ws.write((row), 7, "Remarks of bKash CS Agent", style2)
    row += 1
    for data in data_list:
        col = 0
        ws.write((row), col, data['Ticket_ID'], style2)
        ws.write((row), col + 1, data['Request_Date_export'], date_format)
        ws.write((row), col + 2, data['Execution_Date_export'], date_format)
        ws.write((row), col + 3, data['account_no'], style2)
        ws.write((row), col + 4, data['service_type'], style2)
        ws.write((row), col + 5, data['execution_status'], style2)
        ws.write((row), col + 6, data['Executed_by'], style2)
        ws.write((row), col + 7, data['remarks_of_bkash_cs'], style2)
        row += 1
    wb.save(response)
    return response


def export_report_agents_activity(data_list):
    date_format = xlwt.XFStyle()
    date_format.num_format_str = 'dd/mm/yyyy'
    wb = xlwt.Workbook()
    ws = wb.add_sheet('Agent Report Activity')
    report_filename = 'report_agents_activity'
    response = HttpResponse(content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=report_agents_activity.xls'
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet(str(report_filename))
    style0 = xlwt.easyxf('font: name Times New Roman, color-index red, bold on',
                         num_format_str='#,##0.00')
    style1 = xlwt.easyxf(num_format_str='D-MMM-YY')
    style2 = xlwt.easyxf('font: name Times New Roman, color-index black, bold on',
                         num_format_str='#,##0.00')
    row = 0
    ws.write((row), 0, "Agent Name", style2)
    ws.write((row), 1, "Login Date & Time", style2)
    ws.write((row), 2, "Logout Date & Time", style2)
    ws.write((row), 3, "User IP Address", style2)
    ws.write((row), 4, "Browser", style2)

    row += 1
    for data in data_list:
        col = 0
        ws.write((row), col, data['username'], style2)
        ws.write((row), col + 1, data['login_time'], date_format)
        ws.write((row), col + 2, data['logout_time'], date_format)
        ws.write((row), col + 3, data['user_ip'], style2)
        ws.write((row), col + 4, data['user_browser'], style2)

        row += 1
    wb.save(response)
    return response


# def wallet_check(request):
def wallet_check(request, wallet_no):
    url = 'http://wallet.brac.net/api/checkwallet/check'  # Set destination URL here
    # {" WalletNo":"01816439950"," SecurityKey":"F6D3FD86-D1C5-4266-B0FA-671F3FC3D2C2"}    
    # post_fields = {'t': 'ab0bba166bc4f788db35d16563a8e15db103aa41', 'to_number':'01985468227', 'message':'Hi 33'}
    # post_fields = {'WalletNo': '01816439950', 'SecurityKey':WALLET_API_SECURITY_KEY}
    post_fields = {'WalletNo': wallet_no, 'SecurityKey': WALLET_API_SECURITY_KEY}
    # request = Request(url, urlencode(post_fields).encode())
    # json = urlopen(request).read().decode()
    # print(json)


    # query_args = { 'q':'query string', 'foo':'bar' }
    # encoded_args = urllib.urlencode(post_fields)
    # # url = 'http://localhost:8080/'
    # print encoded_args
    # json =  urllib2.urlopen(url, encoded_args).read()
    # print json
    import urllib
    import urllib2

    data = urllib.urlencode(post_fields)
    # print data
    req = urllib2.Request(url, data)
    # req.add_header('HTTP_REFERER', 'http://kobo.mpower-social.com:8008/')
    # print req
    response = urllib2.urlopen(req)
    the_page = response.read()
    # print "tt",type(the_page)
    if the_page == 'true':
        return True
    elif the_page == 'false':
        return False
    else:
        return False
    return HttpResponse(the_page)


@csrf_exempt
def mobile_change_password(request):
    '''
    JSON field=> model field
    pin => pin
    old_password => old_password
    new_password => new_password
    '''
    if request.method == 'POST':
        data = request.POST.get("data", "xxx")
        json_obj = json.loads(data)
        pin = json_obj['pin']
        old_password = json_obj['old_password']
        new_password = json_obj['new_password']
        current_user = authenticate(username=pin, password=old_password)
        if current_user:
            current_user.password = make_password(new_password)
            current_user.save()
            return HttpResponse(content="Password Changed Successfully", status=200)
        else:
            return HttpResponse(content="No such user exists with that pin and password combination", status=201)
    else:
        return HttpResponse(content="Invalid Request", status=201)


@csrf_exempt
def mobile_reset_token(request):
    '''
    JSON field=> model field
    pin => pin
    '''
    if request.method == 'POST':
        data = request.POST.get("data", "xxx")
        json_obj = json.loads(data)
        pin = json_obj['pin']
        dj_user = User.objects.filter(username=pin).first()
        if dj_user:
            user_security_code = UserSecurityCode.objects.filter(user=dj_user).order_by('-generation_time').first()
            is_code_valid = False
            response_code = ''

            if user_security_code:
                time_diff = timezone.now() - user_security_code.generation_time
                validity_period = 5 * 60
                is_code_valid = time_diff.seconds <= validity_period

            if is_code_valid:
                response_code = user_security_code.code
            else:
                response_code = '{0:05}'.format(random.randint(1, 100000))
                new_user_security_code = UserSecurityCode(user=dj_user, code=response_code)
                new_user_security_code.save()

            usermodule_user = UserModuleProfile.objects.filter(user=dj_user).first()
            if usermodule_user:
                try:
                    url = 'http://mydesk.brac.net/sms/api/push'  # Set destination URL here
                    post_fields = {'t': SMS_API_TOKEN, 'to_number': usermodule_user.contact, 'message': response_code}

                    encoded_args = urllib.urlencode(post_fields)
                    post_response = urllib2.urlopen(url, encoded_args).read()
                except Exception, e:

                    return HttpResponse(status=203)
            return HttpResponse("Please check your mobile for security code.")
    return HttpResponse(status=201)


@csrf_exempt
def mobile_reset_password(request):
    '''
    JSON field=> model field
    pin => pin
    securityCode => securityCode
    password => password
    '''
    if request.method == 'POST':
        data = request.POST.get("data", "xxx")
        json_obj = json.loads(data)
        dj_user = User.objects.filter(username=json_obj['pin']).first()
        usermodule_user = UserModuleProfile.objects.filter(user=dj_user).first()
        user_security_code = UserSecurityCode.objects.filter(user=dj_user, code=json_obj['securityCode']).order_by(
            '-generation_time').first()
        is_code_valid = False
        if user_security_code:
            # validity_period = minutes * 60 seconds
            validity_period = 5 * 60
            time_diff = timezone.now() - user_security_code.generation_time
            is_code_valid = time_diff.seconds <= validity_period

        if dj_user and usermodule_user and is_code_valid:
            dj_user.password = make_password(json_obj['password'])
            dj_user.save()
            return HttpResponse("Password successfully changed.")
    return HttpResponse(content="Invalid Credentials", status=403)


def localize_datetime(dtime):
    # print ('get_current_timezone()::::::',get_current_timezone())
    tz_aware = make_aware(dtime, get_current_timezone())  # .astimezone(get_current_timezone()) #get_current_timezone()
    return datetime.strftime(tz_aware, '%a %d %b %Y %H:%M')  # %Y-%m-%d %H:%M:%S


def __db_fetch_values_dict(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = dictfetchall(cursor)
    cursor.close()
    return fetchVal


def __db_fetch_values(query):
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = cursor.fetchall()
    cursor.close()
    return fetchVal


def dictfetchall(cursor):
    desc = cursor.description
    return [
        OrderedDict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()]


def date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj


def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError


def getLastId(request):
    query = "SELECT COALESCE(max(id),0) FROM public.project_data_complain"
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = cursor.fetchone()
    return HttpResponse(fetchVal[0])


def getLastIdInner():
    query = "SELECT COALESCE(max(id),0) FROM public.project_data_complain"
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = cursor.fetchone()
    return fetchVal[0]

@login_required
def getAgents(request):
    role_id = request.POST.get('role_id')
    query = "select user_id,(select username from auth_user where id = (select user_id from usermodule_usermoduleprofile where id = t.user_id)) from usermodule_userrolemap t where role_id ="+str(role_id)
    data = json.dumps(__db_fetch_values_dict(query))
    return HttpResponse(data)

# web service
@csrf_exempt
def getRequestedList(request,username):
    query = "WITH t AS( SELECT * FROM project_data_complain WHERE ( status ='Open' AND execution_status NOT IN ('Escalate', 'Forward')) and pin_id = (select id from auth_user where username = '"+str(username)+"')) SELECT CASE WHEN parent_id IS NOT NULL THEN parent_id ELSE t.id END service_id, account_no account_number, customer_name account_name, service_type, case when execution_status IN ('New', 'Open', 'Corrected') then 'Submitted' else execution_status end as ticket_status,status,( SELECT username FROM auth_user WHERE id = pin_id limit 1) pin, date_of_birth::date dob, nid_front, nid_back, nid_copy, kyc_front, kyc_back, account_balance, transaction_type, transaction_amount, id_no nid_number,to_char(transaction_date_time,'YYYY-MM-DD')  transaction_date, transaction_amount, transaction_id,remarks_of_csa_customer remarks,step,to_char(received_time, 'YYYY-MM-DD HH24:MI:SS') received_time,comment_text || '\n' || other_comment as comments,reason FROM t"
    data = json.dumps(__db_fetch_values_dict(query), default=decimal_date_default)
    return HttpResponse(data)

@csrf_exempt
def getResolvedList(request,username):
    query = "select id service_id,account_no account_number,customer_name account_name,service_type,execution_status ticket_status,status,to_char(received_time, 'YYYY-MM-DD HH24:MI:SS') received_time,comment_text || '\n' || other_comment as comments from project_data_complain where status ='Closed' and pin_id = (select id from auth_user where username = '"+str(username)+"')"
    data = json.dumps(__db_fetch_values_dict(query), default=datetime_handler)
    return HttpResponse(data)

def getComments(request):
    execution_status = request.POST.get('dist')
    service_type = request.POST.get('service_type')
    query = "select id as value,comment_text as label from comments where service_type = '"+str(service_type)+"' and execution_status = '"+str(execution_status)+"'"
    data = json.dumps(__db_fetch_values_dict(query))
    return HttpResponse(data)
