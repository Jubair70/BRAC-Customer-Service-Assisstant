import json
from datetime import date, timedelta, datetime
import random

from django.shortcuts import render,render_to_response, get_object_or_404
from django.http import (HttpResponseRedirect, HttpResponse,Http404)

from django.template import RequestContext,loader
from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth import authenticate
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
from django.db.models import Count,Q
from project_data.models import Complain, ComplainStatusLog, Branch, Notification, Region
from project_data.forms import ComplainForm, BranchForm, NotificationForm

from usermodule.models import UserModuleProfile, Organizations, UserSecurityCode, Task, TaskRolePermissionMap, UserRoleMap
from usermodule.forms import TaskForm, TaskRolePermissionMapForm
from usermodule.helpers import BKASH_EXEC_ROLE_ID
from usermodule.views import admin_check


from project_data.helpers import send_push_msg
from microfinance.settings import WALLET_API_SECURITY_KEY, SMS_API_TOKEN, TIME_ZONE, USE_TZ
import xlwt

# from urllib.parse import urlencode
# from urllib.request import Request, urlopen
import urllib
import urllib2
# Create your views here.
def index(request):
    send_push_msg(topic = '/CSA/1/22222',payload = "Test Payload")
    return HttpResponse("asdasdsad")

@login_required
def new_complain(request):
    context = RequestContext(request)
    start_time =  (timezone.now() - timedelta(days=7)).date()
    end_time =  (timezone.now() + timedelta(days=1)).date()
    # complains = Complain.objects.filter(Q(execution_status='Read') | Q(execution_status='New') ).order_by("pk")
    # print start_time
    # print end_time
    #q_objects = Q(received_time__range=(start_time, end_time)) # Create an empty Q object to start with
    #complains = Complain.objects.filter(Q(transaction_date_time__range=(start_time, end_time) ) & ( Q(execution_status='Read') | Q(execution_status='New')) ).order_by("pk")
    complains = Complain.objects.filter(Q(received_time__range=(start_time, end_time) ) & ( Q(execution_status='Read') | Q (execution_status='New')) ).order_by("received_time")
    print "##########problem is here"
    print complains
    success = request.GET.get("status", False)
    locker = request.GET.get("locker", False)
    unlock = request.GET.get("unlock", False)
    branches = Branch.objects.filter(status = 'active') #.order_by("pk")
    return render_to_response(
            'project_data/complain_list.html',
            {'complains':complains,'complain_mgt':'complain_mgt',
             'new_complain':'new_complain', 'branches':branches,
             'page_header':'New Requests','success': success,
             'locker':locker,'unlock':unlock
             },
            context)


@login_required
def all_complain(request):
    context = RequestContext(request)
    start_time =  (timezone.now() - timedelta(days=7)).date()
    end_time =  (timezone.now() + timedelta(days=1)).date()

    #complains = Complain.objects.filter().order_by("-pk")
    complains = Complain.objects.filter(Q(received_time__range=(start_time, end_time))).order_by("received_time")
    branches = Branch.objects.filter(status = 'active').order_by("pk")
    print ('timezone::',timezone.now())	
    activate(TIME_ZONE)
    print TIME_ZONE
    print ('timezone::',timezone.now())	
    print  USE_TZ
    return render_to_response(
            'project_data/all_complain_list.html',
            {'complains':complains,'complain_mgt':'complain_mgt',
             'branches':branches, 'all_complain':'all_complain',
            'page_header':'All Requests'},
            context)

@login_required
def complain_unlock(request, complain_id, user_id):
    context = RequestContext(request)
    complain = Complain.objects.filter(pk = complain_id).first()
    if complain:
        # if request user is django superuser can unlock
        # if request user is locker then can unlock
        # if request user's role can over ride lock then can unlock
        # otherwise just redirect to complain page without doin anything
        if request.user.is_superuser:
            complain.locker = None
            complain.save(update_fields=["locker"]) 
            #complain.save()
            return HttpResponseRedirect('/project/new-complain/?unlock=unlock')
        current_user = UserModuleProfile.objects.filter(user = request.user).first()
        can_change_status = False
        can_override_lock = False
        if current_user:
            can_change_status = TaskRolePermissionMap.objects.filter(name__name = 'Change Complain Status',role = current_user.account_type).first()
            can_override_lock = TaskRolePermissionMap.objects.filter(name__name = 'Override Complain Lock',role = current_user.account_type).first()
        if can_change_status or can_override_lock:
            complain.locker = None
            complain.save(update_fields=["locker"]) 
            #complain.save()
            return HttpResponseRedirect('/project/new-complain/?unlock=unlock')

    return HttpResponseRedirect('/project/new-complain/')

@login_required
def complain_unlock_home(request, complain_id, user_id):
    context = RequestContext(request)
    complain = Complain.objects.filter(pk = complain_id).first()
    if complain:
        # if request user is django superuser can unlock
        # if request user is locker then can unlock
        # if request user's role can over ride lock then can unlock
        # otherwise just redirect to complain page without doin anything
        if request.user.is_superuser:
            complain.locker = None
            complain.save(update_fields=["locker"]) 
            #complain.save()
            return HttpResponseRedirect('/project/new-complain/?unlock=unlock')
        current_user = UserModuleProfile.objects.filter(user = request.user).first()
        can_change_status = False
        can_override_lock = False
        if current_user:
            can_change_status = TaskRolePermissionMap.objects.filter(name__name = 'Change Complain Status',role = current_user.account_type).first()
            can_override_lock = TaskRolePermissionMap.objects.filter(name__name = 'Override Complain Lock',role = current_user.account_type).first()
        if can_change_status or can_override_lock:
            complain.locker = None
            complain.save(update_fields=["locker"]) 
            return HttpResponseRedirect('/project/new-complain/?unlock=unlock')

@login_required
def complain_filter_list(request):
    problem_type = request.GET.get('problem_type', 'custom')
    branch = request.GET.get('branch' , 'custom')
    status = request.GET.get('status', 'custom')
    start_time = request.GET.get('start', 'custom')
    end_time = request.GET.get('end', 'custom')
    #end_time= end_time + " 23:59:59"
    print end_time
    #q_objects = Q(transaction_date_time__range=(start_time, end_time)) # Create an empty Q object to start with
    q_objects = Q(received_time__range=(start_time, end_time)) # Create an empty Q object to start with

    source = request.GET.get('order', 'asc')
    ordering = 'pk' if source == 'asc' else '-pk'
    if problem_type != 'custom':
        q_objects &= Q(service_type = problem_type) # 
    if branch != 'custom':
        q_objects &= Q(pin__usermoduleprofile__branch__pk = branch) # 
    if status != 'custom':
        if status=="Pending":
            q_objects &= Q(execution_status = 'New') | Q(execution_status = 'Read') # 
        else:
            q_objects &= Q(execution_status = status) # 

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
    #print '==========================='
    # print 'branch',branch
    # print 'status',status  
    # print 'query',complain_list.query  
    
    response_data = []
    # complain_list = Complain.objects.filter(service_type = problem_type, execution_status = status, pin__usermoduleprofile__branch__pk = branch).order_by("-pk")
    #print complain_list
    for complain in complain_list:
        data = dict()
        if complain.pin.usermoduleprofile.branch is not None:
            data["serial"] = complain.pin.usermoduleprofile.branch.name + ('%05d' % complain.id)
        else:
            data["serial"] = '%05d' % complain.id

        #data["date"] = complain.transaction_date_time.strftime("%A %d %B %Y")
        #data["time"] = complain.transaction_date_time.strftime("%H : %M")
        print '&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&' 
        print complain.received_time

        data["date"] = localize_datetime(complain.received_time)#.strftime("%a %d %b %Y %H:%M %X") #timezone.localtime(complain.received_time) #complain.received_time.replace(tzinfo='Asia/Dhaka').strftime("%a %d %b %Y %H:%M %X")
        data["time"] = complain.received_time.strftime("%H : %M")
        #print data["time"] + "    " + data["date"]
        data["account_no"] = complain.account_no
        data["service_type"] = complain.service_type
        if complain.service_type=="Transaction Confirmation":
            data["transaction_id"] = complain.transaction_id
            data["tdate"] = complain.transaction_date_time.strftime("%a %d %b %Y %H:%M")
        else:
            data["transaction_id"] = ""
            data["tdate"] = ""
        data["status"] = complain.execution_status
        data["view"] = complain.id



        response_data.append(data)
    print response_data
    return HttpResponse(json.dumps(response_data), content_type="application/json")


def add_complain(request):
    context = RequestContext(request)
    edit_check = False
    complain_form = ComplainForm(data=request.POST or None, edit_check = edit_check)
    if request.method == 'POST':
        if complain_form.is_valid():
            cmp_obj = complain_form.save(commit = False)
            cmp_obj.pin = request.user
            cmp_obj.save()
            return HttpResponseRedirect('/project/new-complain/')
        else:
            print complain_form.errors
    return render_to_response(
            'project_data/add_complain.html',
            {'complain_form':complain_form},
            context)

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
        valid = wallet_check(request,json_obj['AccountNumber'])
        if valid:
            complain_obj = Complain()
            complain_obj.account_no = json_obj['AccountNumber']
            complain_obj.service_type = json_obj['ServiceType'] 
            complain_obj.customer_name = json_obj['CustomerName']
            complain_obj.balance = json_obj['AccountBalance']
            complain_obj.id_type = json_obj['IdCardType']
            complain_obj.id_no = json_obj['IdCardNumber']
            complain_obj.transaction_id = json_obj['TransactionId']
            complain_obj.transaction_date_time = json_obj['Date'] if json_obj['Date'] != '' else timezone.now()
            complain_obj.transaction_amount = json_obj['Amount']
            complain_obj.remarks_of_csa_customer = json_obj['Remarks']
            complain_obj.execution_status = 'New'
            complain_obj.pin = User.objects.filter(username = json_obj['pin']).first()
            complain_obj.save()
            return HttpResponse(complain_obj.id)
        else:
            return HttpResponse(status=201)    
    else:
        return HttpResponse(status=201)

@login_required
def edit_complain(request,complain_id):
    context = RequestContext(request)
    edit_check = True
    show_status_dropdown = False
    complain = Complain.objects.get(pk = complain_id)
    current_user = UserModuleProfile.objects.filter(user = request.user).first()
    is_bkash_exec = False
    can_change_status = False
    can_override_lock = False
    if current_user:
        can_change_status = TaskRolePermissionMap.objects.filter(name__name = 'Change Complain Status',role = current_user.account_type).first()
        can_override_lock = TaskRolePermissionMap.objects.filter(name__name = 'Override Complain Lock',role = current_user.account_type).first()

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
                    return HttpResponseRedirect('/project/new-complain/?locker='+complain.locker.username)
    complain_form = ComplainForm(data=request.POST or None,instance=complain, edit_check = edit_check, show_status_dropdown = show_status_dropdown, initial={'execution_status':complain.execution_status})
    if request.method == 'POST':
        if complain_form.is_valid():
            cmp_obj = complain_form.save(commit = False)
            if can_change_status or can_override_lock:
                cmp_obj.locker = None
            if cmp_obj.execution_status == 'Executed':
                cmp_obj.not_execute_reason = None
            cmp_obj.save()
            if is_bkash_exec:
                cmp_stat = ComplainStatusLog(complain = complain, bkash_agent = request.user, status = complain.execution_status)
                cmp_stat.save()
            return HttpResponseRedirect('/project/new-complain/?status=success')
        else:
            print complain_form.errors
    
    if current_user:
        is_previously_set = complain.execution_status in ['Executed','Not Executed','Read']
        if not is_previously_set:
            complain.execution_status = 'Read'
            #complain.save()
            complain.save(update_fields=["execution_status"]) 

            cmp_stat = ComplainStatusLog(complain = complain, bkash_agent = request.user, status = 'Read')
            cmp_stat.save()

    return render_to_response(
            'project_data/edit_complain.html',
            {'complain_form':complain_form,'id':complain_id,
            'complain':complain,'show_status_dropdown':show_status_dropdown},
            context)


@csrf_exempt
def user_login(request):
    '''
    receives pin and password and returns 200 if valid
	'''
    if request.method == 'GET':
        m_username = request.GET.get("pin", "xxx")
        m_password = request.GET.get("password", "xxx")
        user = authenticate(username=m_username, password=m_password)
        if user:
        	mobile_response = {}
        	mobile_response['username'] = m_username
        	mobile_response['password'] = m_password
        	return HttpResponse(json.dumps(mobile_response), content_type="application/json")
    	else:
            # raise Http404("No such user exists with that pin and password combination")
            return HttpResponse(content="No such user exists with that pin and password combination", status=401)
    else:
        return HttpResponse(content="Invalid Login", status=401)

@login_required
def branch_list(request):
    context = RequestContext(request)
    branches = Branch.objects.all().order_by("pk")
    return render_to_response(
            'project_data/branch_list.html',
            {'branches':branches,'branch_mgt':'branch_mgt','branch_list':'branch_list'},
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
            {'branch_form':branch_form,'branch_mgt':'branch_mgt','add_branch':'add_branch'},
            context)

@login_required
@user_passes_test(admin_check,login_url='/usermodule/')
def edit_branch(request, branch_id):
    context = RequestContext(request)
    edited = False
    branch = Branch.objects.filter(pk=branch_id).first()
    if request.method == 'POST':
        branch_form = BranchForm(data=request.POST,instance=branch)
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
            {'id':branch_id, 'branch_form': branch_form,
            'edited': edited,'task_mgt':'task_mgt'},
            context)


@login_required
@user_passes_test(admin_check,login_url='/usermodule/')
def delete_branch(request, branch_id):
    context = RequestContext(request)
    branch = Branch.objects.get(pk = branch_id)
    branch.delete()
    return HttpResponseRedirect('/project/branch-list/')


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
        #print ('json_obj',json_obj)
        branch = Branch.objects.filter(branch_id = json_obj['code'],status = 'active').first()
        #branch = Branch.objects.filter(name__icontains = json_obj['branch'], branch_id = json_obj['code'],status = 'active').first()
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
        dj_user = User.objects.filter(username = json_obj['pin'], first_name = json_obj['name']).first()
        usermodule_user = UserModuleProfile.objects.filter(contact = json_obj['mobile']).first()
        if dj_user and usermodule_user:
            user_security_code = UserSecurityCode.objects.filter(user = dj_user).order_by('-generation_time').first()
            is_code_valid = False
            response_code = ''
            if user_security_code:
            	# print "system time:", timezone.now()
            	# print "db time:", user_security_code.generation_time
             	# print "time_diff", time_diff.seconds
            	time_diff= timezone.now() - user_security_code.generation_time
                validity_period = 5 * 60
                is_code_valid = time_diff.seconds <= validity_period
                
            if is_code_valid:
                response_code = user_security_code.code
            else:
                response_code = '{0:05}'.format(random.randint(1, 100000))
                new_user_security_code = UserSecurityCode(user = dj_user, code = response_code)
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
        dj_user = User.objects.filter(username = json_obj['pin'], first_name = json_obj['name']).first()
        usermodule_user = UserModuleProfile.objects.filter(contact = json_obj['mobile']).first()
        user_security_code = UserSecurityCode.objects.filter(user = dj_user, code = json_obj['securityCode']).order_by('-generation_time').first()
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
    return HttpResponse(content="Invalid Credentials", status = 403)

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
        print from_date,to_date,service_type,account_no,brac_csa_agent_id,bkash_exec_agent_id
        if service_type != 'custom':
            q_objects_first_query &= Q(service_type = service_type)
        if account_no :
            q_objects_first_query &= Q(account_no = account_no)
        if brac_csa_agent_id != 'custom':
            q_objects_first_query &= Q(pin__id = brac_csa_agent_id)
        if bkash_exec_agent_id != 'custom':
            q_objects_second_query &= Q(bkash_agent__id = bkash_exec_agent_id)
    

    q_objects_first_query &= Q(received_time__range=(from_date, to_date)) # Create an empty Q object to start with
    q_objects_second_query &= Q(change_time__range=(from_date, to_date))
    context = RequestContext(request)
    # complains = Complain.objects.filter(Q(execution_status='Executed') | Q(execution_status='Not Executed')).order_by("pk")
    complains = Complain.objects.filter(q_objects_first_query).order_by("pk")
    complain_list = []
    for complain in complains:
        # cmp_stat = ComplainStatusLog.objects.filter(Q(complain = complain) & Q(status='Executed') | Q(status='Not Executed')).order_by("-pk") # wrong query
        cmp_stat = ComplainStatusLog.objects.filter(Q(complain = complain) & q_objects_second_query).order_by("-pk").first()
        
        if cmp_stat:
            ret_obj = {}
            ret_obj['id'] = str(complain.id)
            ret_obj['account_no'] = complain.account_no
            ret_obj['service_type'] = complain.service_type
            ret_obj['execution_status'] = complain.execution_status
            ret_obj['pin'] = complain.pin.username
            ret_obj['agent'] = cmp_stat.bkash_agent.username
            #ret_obj['transaction_date_time'] = formats.date_format(complain.transaction_date_time, "D d M Y H:i")
            ret_obj['received_time'] = formats.date_format(complain.received_time,"d/m/Y & h:i a")
            ret_obj['replied_time'] = formats.date_format(cmp_stat.change_time,"d/m/Y & h:i a")
            seconds=(cmp_stat.change_time - complain.received_time).total_seconds()
            h=int(seconds // 3600)
            mn=int((seconds % 3600) // 60)
            sec = int((seconds % 3600) % 60)
            ret_obj['handling_time'] = "%d : %d : %d" %(h,mn,sec) #str((cmp_stat.change_time - complain.received_time).total_seconds() // 3600)
            ret_obj['remarks_of_csa_customer'] = complain.remarks_of_csa_customer
            ret_obj['remarks_of_bkash_cs'] = complain.not_execute_reason
            complain_list.append(ret_obj)

    return_type = request.POST.get('export', 'nothing')
    if request.method == 'POST' and return_type == 'export':
        return export_report_accounts(complain_list)
    elif request.method == 'POST':
        return HttpResponse(json.dumps(complain_list), content_type="application/json")

    # account no list
    accounts = Complain.objects.values('account_no').distinct()
    # csa users for filtering list
    csa_perm_map = TaskRolePermissionMap.objects.filter(name__name = 'Can Send Complain From App').first()
    brac_csa_users = UserModuleProfile.objects.filter(account_type = csa_perm_map.role)
    # bkash exec for filtering list
    bkash_exec_perm_map = TaskRolePermissionMap.objects.filter(name__name = 'Change Complain Status').first()
    bkash_exec_users = UserModuleProfile.objects.filter(account_type = bkash_exec_perm_map.role)

    return render_to_response(
            'project_data/report_accounts.html',
            {'reports':'reports','account':'account','complains':complain_list,'accounts':accounts,
            'brac_csa_users':brac_csa_users,'bkash_exec_users':bkash_exec_users
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

    options_query = '''select service_type,request_offered,(executed+not_executed) request_replied, executed,not_executed, (request_offered - (executed+not_executed)) request_rectified,max_handled_time, avg_handled_time, min_handled_time from (
select service_type,get_request_count(service_type,'''+ from_date +''' , '''+ to_date +''') as request_offered,
sum(executed_count) executed,sum(not_executed_count) not_executed,avg(solvetime) avg_handled_time,max(solvetime) max_handled_time,min(solvetime) min_handled_time from (
select *,(EXTRACT(EPOCH FROM resolvetime) - EXTRACT(EPOCH FROM transaction_date_time)) solvetime from (
select id,service_type,execution_status,executed_count,not_executed_count,transaction_date_time,max(change_time) resolvetime from (
select pdc.id,pdc.service_type,pdc.execution_status ,pdc.received_time transaction_date_time,pdcs.change_time,(CASE WHEN pdc.execution_status='Executed' THEN 1  ELSE 0  END) AS executed_count,
(CASE WHEN pdc.execution_status='Not Executed' THEN 1 ELSE 0  END) AS not_executed_count
from project_data_complain pdc inner join project_data_complainstatuslog pdcs on pdc.id = pdcs.complain_id
where (pdc.execution_status = 'Executed' or pdc.execution_status = 'Not Executed') AND pdc.received_time between '''+ from_date +''' AND '''+ to_date +''') t 
group by id,service_type,execution_status,executed_count,not_executed_count,transaction_date_time) resolve) complain_summary
group by service_type) inception
'''
    print options_query
    cursor.execute(options_query)
    data_list = dictfetchall(cursor)
    for data in data_list:
        data['min_handled_time'] = seconds_to_formatted_time(int(data['min_handled_time']))
        data['max_handled_time'] = seconds_to_formatted_time(int(data['max_handled_time']))
        data['avg_handled_time'] = seconds_to_formatted_time(int(data['avg_handled_time']))
    
    return_type = request.POST.get('export', 'nothing')
    if request.method == 'POST' and return_type == 'export':
        return export_report_services(data_list)
    elif request.method == 'POST':
        return HttpResponse(json.dumps(data_list), content_type="application/json")
    # print days, hours, minutes, seconds
    return render_to_response(
            'project_data/report_services.html',
            {'reports':'reports','service':'service',
            'page_header': 'Service Report',
            'data_list':data_list},
            context)


def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]


def seconds_to_formatted_time(seconds):
    #days, seconds = divmod(seconds, 24*60*60)
    hours, seconds = divmod(seconds, 60*60)
    minutes, seconds = divmod(seconds, 60)
    # return str(days) + "days " + str(hours) + "hours " + str(minutes) +"minutes" + str(seconds) + "seconds"
    #return str(days) + "d " + str(hours).zfill(2) + ":" + str(minutes).zfill(2) +":" + str(seconds).zfill(2)
    return str(hours).zfill(3) + ":" + str(minutes).zfill(2) +":" + str(seconds).zfill(2) 

@login_required
def report_agents(request):
    context = RequestContext(request)
    cursor = connection.cursor()
    agent_role =  TaskRolePermissionMap.objects.filter(name__name = 'Change Complain Status').first()
    userlist = UserModuleProfile.objects.filter(account_type = agent_role.role)

    start_time =  (timezone.now() - timedelta(days=7)).date()
    end_time =  (timezone.now() + timedelta(days=1)).date()
    print start_time
    print end_time

    from_date = "'1971-03-26'"
    to_date = "'2999-03-26'"
    options_query_extra = ''
    user_filter_query = ''
    data_exp_list = []
    if not request.user.is_superuser:
        logged_user = UserModuleProfile.objects.filter(user=request.user).first()
	current_user_role = UserRoleMap.objects.filter(user=logged_user).values('role_id').first()    
        #print "##########################################" + str(current_user_role["role_id"])
        if current_user_role["role_id"] == 3:
            user_filter_query = ' and user_login_summary.user_id=' + str(request.user.id)

    
    if request.method == 'POST':
        #print "################################" + request.user.user_id
        from_date = "'" + request.POST.get('start', from_date) + "'"
        to_date = "'" + request.POST.get('end', to_date) + "'"
        agent_id = request.POST.get('agent_id', 'custom')
        
        if agent_id and agent_id != 'custom':
            options_query_extra = 'and complain_status.bkash_agent_id = ' + agent_id
    #print ('from_date',from_date)
    #print ('to_date',to_date)
    options_query = '''select transaction_date_time,username,(executed+not_executed) request_offered,(executed+not_executed) as request_replied,complain_status.avg_handled_time,user_login_summary.total_log_time from (
select bkash_agent_id,date_trunc('day',  transaction_date_time) transaction_date_time,
sum(executed_count) executed,sum(not_executed_count) not_executed,avg(solvetime) avg_handled_time from (
select *,(EXTRACT(EPOCH FROM resolvetime) - EXTRACT(EPOCH FROM transaction_date_time)) solvetime from (
select id,bkash_agent_id,execution_status,executed_count,not_executed_count,transaction_date_time,max(change_time) resolvetime 
from ( select pdc.id,pdcs.bkash_agent_id,pdc.execution_status ,pdc.received_time transaction_date_time,pdcs.change_time,
(CASE WHEN pdc.execution_status='Executed' THEN 1  ELSE 0  END) AS executed_count,
(CASE WHEN pdc.execution_status='Not Executed' THEN 1 ELSE 0  END) AS not_executed_count
from project_data_complain pdc inner join project_data_complainstatuslog pdcs on pdc.id = pdcs.complain_id
where (pdc.execution_status = 'Executed' or pdc.execution_status = 'Not Executed') and (pdcs.status = 'Executed' or pdcs.status = 'Not Executed') AND pdc.received_time between '''+ from_date +''' AND '''+ to_date +''') t group by id,bkash_agent_id,execution_status,executed_count,not_executed_count,transaction_date_time
 ) resolve ) complain_summary
group by bkash_agent_id,date_trunc('day',  transaction_date_time)) complain_status,
(select login_summary.*,username from (Select user_id,date_trunc('day',  login_time) login_time, sum(EXTRACT (EPOCH FROM (logout_time::timestamp(0) - login_time::timestamp(0)))) total_log_time from usermodule_useraccesslog
where login_time>='''+ from_date +''' and logout_time<='''+ to_date +''' group by user_id,date_trunc('day',  login_time)
)login_summary,auth_user where login_summary.user_id=auth_user.id)user_login_summary
where user_login_summary.user_id=complain_status.bkash_agent_id and user_login_summary.login_time=complain_status.transaction_date_time
''' + options_query_extra + user_filter_query    
    #print ('options_query--------------------------------------')
    print options_query
    cursor.execute(options_query)
    data_list = dictfetchall(cursor)
    for data in data_list:
	#print data
        data_obj = {}
        data_obj['transaction_date_time'] = formats.date_format(data['transaction_date_time'], "d/m/Y") #str(data['transaction_date_time'])
        data_obj['username'] = data['username']
        data_obj['total_log_time'] = seconds_to_formatted_time(int(data['total_log_time']))
        data_obj['avg_handled_time'] = seconds_to_formatted_time(int(data['avg_handled_time']))
        data_obj['request_offered'] = int(data['request_offered'])
        data_obj['request_replied'] = int(data['request_replied'])
        data_exp_list.append(data_obj)


    
    return_type = request.POST.get('export', 'nothing')        
    if request.method == 'POST' and return_type == 'export':
        print('data export data_list')
        print data_exp_list
        return export_report_agents(data_exp_list)
    elif request.method == 'POST':
        return HttpResponse(json.dumps(data_exp_list), content_type="application/json")
   
    return render_to_response(
            'project_data/report_agents.html',
            {'reports':'reports','agent':'agent','userlist':userlist,
             'page_header': 'Agents Report','data_list':data_exp_list
            },
            context)

@login_required
def report_agents_performance(request):
    context = RequestContext(request)
    cursor = connection.cursor()
    agent_role =  TaskRolePermissionMap.objects.filter(name__name = 'Change Complain Status').first()
    userlist = UserModuleProfile.objects.filter(account_type = agent_role.role)

    start_time =  (timezone.now() - timedelta(days=7)).date()
    end_time =  (timezone.now() + timedelta(days=1)).date()
    #print start_time
    #print end_time

    from_date = "'1971-03-26'"
    to_date = "'2999-03-26'"
    options_query_extra = ''
    user_filter_query = ''
    if not request.user.is_superuser:
        logged_user = UserModuleProfile.objects.filter(user=request.user).first()
	current_user_role = UserRoleMap.objects.filter(user=logged_user).values('role_id').first()    
        #print "##########################################" + str(current_user_role["role_id"])
        if current_user_role["role_id"] == 3:
            user_filter_query = ' and cpsummary.bkash_agent_id=' + str(request.user.id)

    
    if request.method == 'POST':
        #print "################################" + request.user.user_id
        from_date = "'" + request.POST.get('start', from_date) + "  00:00:00'"
        to_date = "'" + request.POST.get('end', to_date) + " 23:59:59'"
        agent_id = request.POST.get('agent_id', 'custom')
        
        if agent_id and agent_id != 'custom':
            options_query_extra = 'and cpsummary.bkash_agent_id = ' + agent_id

    options_query = '''select cpsummary.id, account_no, service_type, received_time,execution_status,remarks_of_bkash_cs,change_time, bkash_agent_id,username from(
select cp.*,cplog.change_time, bkash_agent_id from (SELECT id, account_no, service_type, received_time,execution_status,remarks_of_bkash_cs       
FROM project_data_complain where (execution_status='Executed' or execution_status='Not Executed') and received_time between  '''+ from_date +''' and '''+ to_date +''') cp,
(SELECT  complain_id, change_time, bkash_agent_id FROM project_data_complainstatuslog where (status='Executed' or status='Not Executed'))cplog
where cp.id=cplog.complain_id) cpsummary,auth_user where auth_user.id=cpsummary.bkash_agent_id
''' + options_query_extra + user_filter_query


    #print options_query
    cursor.execute(options_query)
    data_list = dictfetchall(cursor)
    data_exp_list = []
    #print data_list
    for data in data_list:
        #data['Ticket_ID']
        data_obj = {}
        c_branch = UserModuleProfile.objects.filter(user=data['bkash_agent_id']).values('branch_id').first()
        branch = Branch.objects.filter(pk=c_branch["branch_id"]).first()

        if branch is not None:
            data_obj['Ticket_ID'] = str(branch) + ('%05d' % data['id'])
        else:
            data_obj["Ticket_ID"] = '%05d' % data['id']

	#current_user_role = UserRoleMap.objects.filter(user=logged_user).values('role_id').first()    
        data_obj['Request_Date']=str(formats.date_format(data['received_time'], "d/m/Y h:i a"))
        data_obj['Execution_Date']=str(formats.date_format(data['change_time'], "d/m/Y h:i a"))
        data_obj['account_no']=str(data['account_no'])
        data_obj['service_type']=str(data['service_type'])
        data_obj['execution_status']=str(data['execution_status'])
        data_obj['Executed_by']=str(data['username'])
        data_obj['remarks_of_bkash_cs']=str(data['remarks_of_bkash_cs'])

        data_exp_list.append(data_obj)
    #print data_exp_list
    return_type = request.POST.get('export', 'nothing')        
    if request.method == 'POST' and return_type == 'export':
        return export_report_agents_performance(data_exp_list)
    elif request.method == 'POST':
        return HttpResponse(json.dumps(data_exp_list), content_type="application/json")

    return render_to_response(
            'project_data/report_agents_performance.html',
            {'reports':'reports','agent_performance':'agent_performance','userlist':userlist,
             'page_header': 'Agents Performance Report','data_list':data_exp_list
            },
            context)


@login_required
def report_customer_service_status(request):
    from_date = '1971-03-26'
    to_date = '2999-03-26'
    q_objects_first_query = Q(execution_status='Executed') | Q(execution_status='Not Executed')
    if request.method == 'POST':
        #from_date = request.POST.get('start', from_date)
        #to_date = request.POST.get('end', to_date)
        service_type = request.POST.get('service_type', 'custom')
        status = request.POST.get('status', 'custom')
        branch = request.POST.get('branch' , 'custom')
        region = request.POST.get('region', 'custom')
        
        #brac_csa_agent_id = request.POST.get('brac_csa_agent_id', 'custom')
        #bkash_exec_agent_id = request.POST.get('bkash_exec_agent_id', 'custom')
        #print from_date,to_date,service_type,brac_csa_agent_id,bkash_exec_agent_id
        if status != 'custom':
            q_objects_first_query = Q(execution_status=status)
        else:
            q_objects_first_query = Q(execution_status='Executed') | Q(execution_status='Not Executed')

        if branch != 'custom':
            q_objects_first_query &= Q(pin__usermoduleprofile__branch__pk = branch) # 

        if service_type != 'custom':
            q_objects_first_query &= Q(service_type = service_type)
        if region != 'custom':
            q_objects_first_query &= Q(pin__usermoduleprofile__region__pk = region)
    else:
        q_objects_first_query = Q(execution_status='Executed') | Q(execution_status='Not Executed')
    branches = Branch.objects.filter(status = 'active').order_by("name")
    q_objects_first_query &= Q(transaction_date_time__range=(from_date, to_date)) # Create an empty Q object to start with
    context = RequestContext(request)
    complains = Complain.objects.filter(q_objects_first_query).order_by("pk")
    complain_list = []
    for complain in complains:
        ret_obj = {}
        ret_obj['token_no'] = str(complain.id)
        ret_obj['branch_name'] = complain.pin.usermoduleprofile.branch.name  if (hasattr(complain.pin, 'usermoduleprofile') and complain.pin.usermoduleprofile.branch is not None)  else 'N/A'
        ret_obj['region_name'] = complain.pin.usermoduleprofile.region.name  if (hasattr(complain.pin, 'usermoduleprofile') and complain.pin.usermoduleprofile.region is not None)  else 'N/A'        
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
    csa_perm_map = TaskRolePermissionMap.objects.filter(name__name = 'Can Send Complain From App').first()
    brac_csa_users = UserModuleProfile.objects.filter(account_type = csa_perm_map.role)
    # bkash exec for filtering list
    bkash_exec_perm_map = TaskRolePermissionMap.objects.filter(name__name = 'Change Complain Status').first()
    bkash_exec_users = UserModuleProfile.objects.filter(account_type = bkash_exec_perm_map.role)
    # regions names
    regions = Region.objects.order_by("name")

    return render_to_response(
            'project_data/report_customer_service_status.html',
            {'reports':'reports','customer_service':'customer_service','complains':complain_list,'branches':branches,
            'brac_csa_users':brac_csa_users,'bkash_exec_users':bkash_exec_users,
            'page_header': 'Customer Service Status Report','regions':regions,
            },
            context)


@login_required
@user_passes_test(admin_check,login_url='/usermodule/')
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
            {'form':form,'task_role_mgt':'task_role_mgt'},
            context)


@login_required
@user_passes_test(admin_check,login_url='/usermodule/')
def role_task_permission_list(request):
    user = UserModuleProfile.objects.filter(user_id=request.user.id).first()
    admin = user.admin if user else True
    context = RequestContext(request)
    task_roles = TaskRolePermissionMap.objects.all().order_by("pk")
    return render_to_response(
            'project_data/role_task_permission_list.html',
            {'task_roles':task_roles,'task_role_mgt':'task_role_mgt','admin':'admin'},
            context)


@login_required
@user_passes_test(admin_check,login_url='/usermodule/')
def edit_role_task_permission(request,tast_role_id):
    context = RequestContext(request)
    edited = False
    task_role = TaskRolePermissionMap.objects.filter(pk=tast_role_id).first()
    
    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        task_role_form = TaskRolePermissionMapForm(data=request.POST,instance=task_role)
        
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
            {'id':tast_role_id, 'task_role_form': task_role_form,
            'edited': edited,'task_role_mgt':'task_role_mgt'},
            context)


@login_required
@user_passes_test(admin_check,login_url='/usermodule/')
def delete_task_role(request,tast_role_id):
    context = RequestContext(request)
    task_role = TaskRolePermissionMap.objects.get(pk = tast_role_id)
    task_role.delete()
    return HttpResponseRedirect('/project/task-role-permission-list/')


@login_required
@user_passes_test(admin_check,login_url='/usermodule/')
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
            {'form':form,'task_mgt':'task_mgt'},
            context)


@login_required
@user_passes_test(admin_check,login_url='/usermodule/')
def task_list(request):
    user = UserModuleProfile.objects.filter(user_id=request.user.id).first()
    admin = user.admin if user else True
    context = RequestContext(request)
    tasks = Task.objects.all().order_by("pk")
    return render_to_response(
            'project_data/task_list.html',
            {'tasks':tasks,'task_mgt':'task_mgt','admin':admin},
            context)


@login_required
@user_passes_test(admin_check,login_url='/usermodule/')
def edit_task(request,task_id):
    context = RequestContext(request)
    edited = False
    task = Task.objects.filter(pk=task_id).first()
    if request.method == 'POST':
        task_form = TaskForm(data=request.POST,instance=task)
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
            {'id':task_id, 'task_form': task_form,
            'edited': edited,'task_mgt':'task_mgt'},
            context)


@login_required
@user_passes_test(admin_check,login_url='/usermodule/')
def delete_task(request,task_id):
    context = RequestContext(request)
    task_role = Task.objects.get(pk = tast_id)
    task_role.delete()
    return HttpResponseRedirect('/usermodule/roles-list')


@login_required
@user_passes_test(admin_check,login_url='/usermodule/')
def send_global_message(request):
    context = RequestContext(request)
    form = NotificationForm(data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            complain_topic =  "/CSA/1"
            notification = form.save(commit = False)
            send_push_msg(topic = complain_topic, payload = notification.message)
            notification.sender = request.user
            notification.save()
            return HttpResponseRedirect('/project/global-message-history/')
        else:
            print form.errors
    return render_to_response(
            'project_data/send_global_message.html',
            {'form':form,'notification_mgt':'notification_mgt','notification_add':'notification_add'},
            context)


@login_required
#@user_passes_test(admin_check,login_url='/usermodule/')
def global_message_history(request):
    context = RequestContext(request)
    notifications = Notification.objects.all().order_by("pk")
    return render_to_response(
            'project_data/global_message_history.html',
            {'notifications':notifications,'notification_mgt':'notification_mgt','notification_list':'notification_list'},
            context)

def sms_test(request):
# def sms_test(request, to_number = '', message = 'Hello'):
    url = 'http://mydesk.brac.net/sms/api/push' # Set destination URL here
    # url = 'http://kobo.mpower-social.com:8008/project/sms-status/' # Set destination URL here
    post_fields = {'t': SMS_API_TOKEN, 'to_number':'01985468227', 'message':'Hi 33'}

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
    print data 
    req = urllib2.Request(url, data)
    # req.add_header('HTTP_REFERER', 'http://kobo.mpower-social.com:8008/')
    print req
    response = urllib2.urlopen(req)
    the_page = response.read()
    print the_page
    return HttpResponse(the_page)

@csrf_exempt
def sms_status(request):
    # for i in request.POST:
        # print i
        # print "key: %s , value: %s" % (i, request.POST[i])
    print "######################################"
    print request.META.get('HTTP_REFERER')
    for key, value in request.POST.iteritems():
        print "####"
        print key
        print value
        print "####"

    return HttpResponse("200")

def export_report_customer_service_status(data_list):
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
    ws.write( (row), 0, "Token No.",style2)
    ws.write( (row), 1, "Region",style2)
    ws.write( (row), 2, "Branch Name",style2)
    ws.write( (row), 3, "Service Type",style2)
    ws.write( (row), 4, "Execution Status",style2)
    ws.write( (row), 5, "Not Execution Reason",style2)
    
    row += 1
    for data in data_list:
        col = 0
        ws.write( (row), col, data['token_no'],style2)
        ws.write( (row), col+1, data['region_name'],style2)
        ws.write( (row), col+2, data['branch_name'],style2)
        ws.write( (row), col+3, data['service_type'],style2)
        ws.write( (row), col+4, data['execution_status'],style2)
        ws.write( (row), col+5, data['not_execute_reason'],style2)
        row += 1
    wb.save(response)
    return response

def export_report_accounts(data_list):
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
    ws.write( (row), 0, "Serial",style2)
    ws.write( (row), 1, "Account No.",style2)
    ws.write( (row), 2, "Service Type",style2)
    ws.write( (row), 3, "Execution Status",style2)
    ws.write( (row), 4, "BRAC Agent",style2)
    ws.write( (row), 5, "bKash Agent",style2)
   # ws.write( (row), 6, "Date",style2)
    ws.write( (row), 7, "Request Time",style2)
    ws.write( (row), 8, "Replied Time",style2)
    ws.write( (row), 9, "Handling Time",style2)
    ws.write( (row), 10, "Remarks(BRAC CSA)",style2)
    ws.write( (row), 11, "Remarks(bKash Executive)",style2)
    row += 1
    for data in data_list:
        col = 0
        ws.write( (row), col, data['id'],style2)
        ws.write( (row), col+1, data['account_no'],style2)
        ws.write( (row), col+2, data['service_type'],style2)
        ws.write( (row), col+3, data['execution_status'],style2)
        ws.write( (row), col+4, data['pin'],style2)
        ws.write( (row), col+5, data['agent'],style2)
        #ws.write( (row), col+6, data['transaction_date_time'],style2)
        ws.write( (row), col+7, data['received_time'],style2)
        ws.write( (row), col+8, data['replied_time'],style2)
        ws.write( (row), col+9, data['handling_time'],style2)
        ws.write( (row), col+10, data['remarks_of_csa_customer'],style2)
        ws.write( (row), col+11, data['remarks_of_bkash_cs'],style2)
        row += 1
    wb.save(response)
    return response

def export_report_services(data_list):
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
    ws.write( (row), 0, "Service Type",style2)
    ws.write( (row), 1, "Request Offered",style2)
    ws.write( (row), 2, "Request Replied",style2)
    ws.write( (row), 3, "Request Executed",style2)
    ws.write( (row), 4, "Request Not Executed",style2)
    ws.write( (row), 5, "Request Rectified",style2)
    ws.write( (row), 6, "AHT(Average Handled Time)",style2)
    ws.write( (row), 7, "Longest Wait Time",style2)
    ws.write( (row), 8, "Lowest Wait Time",style2)
    row += 1
    for data in data_list:
        col = 0
        ws.write( (row), col, data['service_type'],style2)
        ws.write( (row), col+1, data['request_offered'],style2)
        ws.write( (row), col+2, data['request_replied'],style2)
        ws.write( (row), col+3, data['executed'],style2)
        ws.write( (row), col+4, data['not_executed'],style2)
        ws.write( (row), col+5, data['request_rectified'],style2)
        ws.write( (row), col+6, data['avg_handled_time'],style2)
        ws.write( (row), col+7, data['max_handled_time'],style2)
        ws.write( (row), col+8, data['min_handled_time'],style2)
        row += 1
    wb.save(response)
    return response


def export_report_agents(data_list):
    print ('data_list in export')
    print data_list
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
    ws.write( (row), 0, "Date",style2)
    ws.write( (row), 1, "bKash Agent Name(Emp)",style2)
    ws.write( (row), 2, "Total Login Time",style2)
    ws.write( (row), 3, "Average Handled Time",style2)
    ws.write( (row), 4, "Request Offered",style2)
    ws.write( (row), 5, "Request Replied",style2)
    row += 1
    for data in data_list:
        col = 0
        ws.write( (row), col, data['transaction_date_time'],style2)
        ws.write( (row), col+1, data['username'],style2)
        ws.write( (row), col+2, data['total_log_time'],style2)
        ws.write( (row), col+3, data['avg_handled_time'],style2)
        ws.write( (row), col+4, data['request_offered'],style2)
        ws.write( (row), col+5, data['request_replied'],style2)
        row += 1
    wb.save(response)
    return response

def export_report_agents_performance(data_list):
    print ('data_list in export')
    print data_list
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
    ws.write( (row), 0, "Ticket ID",style2)
    ws.write( (row), 1, "Request Date & Time",style2)
    ws.write( (row), 2, "Execution Date & Time",style2)
    ws.write( (row), 3, "Account No.",style2)
    ws.write( (row), 4, "Service Type",style2)
    ws.write( (row), 5, "Execution Status(Executed/not Executed)",style2)
    ws.write( (row), 6, "Executed By",style2)
    ws.write( (row), 7, "Remarks of bKash CS Agent",style2)
    row += 1
    for data in data_list:
        col = 0
        ws.write( (row), col, data['Ticket_ID'],style2)
        ws.write( (row), col+1, data['Request_Date'],style2)
        ws.write( (row), col+2, data['Execution_Date'],style2)
        ws.write( (row), col+3, data['account_no'],style2)
        ws.write( (row), col+4, data['service_type'],style2)
        ws.write( (row), col+5, data['execution_status'],style2)
        ws.write( (row), col+6, data['Executed_by'],style2)
        ws.write( (row), col+7, data['remarks_of_bkash_cs'],style2)
        row += 1
    wb.save(response)
    return response


# def wallet_check(request):
def wallet_check(request, wallet_no):
    url = 'http://wallet.brac.net/api/checkwallet/check' # Set destination URL here
    # {" WalletNo":"01816439950"," SecurityKey":"F6D3FD86-D1C5-4266-B0FA-671F3FC3D2C2"}    
    # post_fields = {'t': 'ab0bba166bc4f788db35d16563a8e15db103aa41', 'to_number':'01985468227', 'message':'Hi 33'}
    # post_fields = {'WalletNo': '01816439950', 'SecurityKey':WALLET_API_SECURITY_KEY}
    post_fields = {'WalletNo': wallet_no, 'SecurityKey':WALLET_API_SECURITY_KEY}
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
    print data 
    req = urllib2.Request(url, data)
    # req.add_header('HTTP_REFERER', 'http://kobo.mpower-social.com:8008/')
    print req
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
            return HttpResponse(content = "Password Changed Successfully", status = 200)
        else:
            return HttpResponse(content = "No such user exists with that pin and password combination", status = 201)
    else:
        return HttpResponse(content = "Invalid Request", status=201)


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
        dj_user = User.objects.filter(username = pin).first()
        if dj_user:
            user_security_code = UserSecurityCode.objects.filter(user = dj_user).order_by('-generation_time').first()
            is_code_valid = False
            response_code = ''
            
            if user_security_code:
                time_diff= timezone.now() - user_security_code.generation_time
                validity_period = 5 * 60
                is_code_valid = time_diff.seconds <= validity_period
                
            if is_code_valid:
                response_code = user_security_code.code
            else:
                response_code = '{0:05}'.format(random.randint(1, 100000))
                new_user_security_code = UserSecurityCode(user = dj_user, code = response_code)
                new_user_security_code.save()
            
            usermodule_user = UserModuleProfile.objects.filter(user = dj_user).first()
            if usermodule_user:
                try:
                    url = 'http://mydesk.brac.net/sms/api/push' # Set destination URL here
                    post_fields = {'t': SMS_API_TOKEN, 'to_number':usermodule_user.contact, 'message':response_code}

                    encoded_args = urllib.urlencode(post_fields)
                    post_response =  urllib2.urlopen(url, encoded_args).read()
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
        dj_user = User.objects.filter(username = json_obj['pin']).first()
        usermodule_user = UserModuleProfile.objects.filter(user = dj_user).first()
        user_security_code = UserSecurityCode.objects.filter(user = dj_user, code = json_obj['securityCode']).order_by('-generation_time').first()
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
    return HttpResponse(content="Invalid Credentials", status = 403)

def localize_datetime(dtime):
    print ('get_current_timezone()::::::',get_current_timezone())
    tz_aware = make_aware(dtime, get_current_timezone())#.astimezone(get_current_timezone()) #get_current_timezone()
    return datetime.strftime(tz_aware, '%a %d %b %Y %H:%M') #%Y-%m-%d %H:%M:%S
