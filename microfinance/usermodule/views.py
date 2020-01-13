from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.db.models import Count,Q
from django.http import (
    HttpResponseRedirect, HttpResponse)
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext,loader
from django.contrib.auth.models import User
from datetime import date, timedelta, datetime
from django.utils import timezone
# from django.utils import simplejson
import json
import logging
import sys
from user_agents import parse
from django.core.urlresolvers import reverse
from django.contrib.sessions.models import Session

# Create your views here.
from django.db import (IntegrityError,transaction)
from django.db.models import ProtectedError
from django.shortcuts import redirect
# from onadata.apps.main.models.user_profile import UserProfile
from usermodule.forms import UserForm, UserProfileForm, ChangePasswordForm, UserEditForm,OrganizationForm,OrganizationDataAccessForm,ResetPasswordForm
from usermodule.models import UserModuleProfile, UserPasswordHistory, UserFailedLogin, UserAccessLog, Organizations, OrganizationRole, OrganizationDataAccess

from django.contrib.auth.decorators import login_required, user_passes_test
from django import forms
# Menu imports
from usermodule.forms import MenuForm,TimeForm
from usermodule.models import MenuItem, TaskRolePermissionMap
# Unicef Imports
# from onadata.apps.logger.models import Instance,XForm
# Organization Roles Import
from usermodule.models import OrganizationRole,MenuRoleMap,UserRoleMap,working_hour
from usermodule.forms import OrganizationRoleForm,RoleMenuMapForm,UserRoleMapForm,UserRoleMapfForm
from django.forms.models import inlineformset_factory,modelformset_factory
from django.forms.formsets import formset_factory

from django.core.exceptions import ObjectDoesNotExist
from usermodule.helpers import BRAC_ORD_ID, BRAC_CSA_ROLE_ID, BRAC_MF_ROLE_ID
from microfinance.settings import WALLET_API_SECURITY_KEY, SMS_API_TOKEN
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
import  pandas
from django.shortcuts import render
from project_data.models import Branch, Region
from django.db.models import Q
from django.contrib import messages
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.utils.crypto import get_random_string

def admin_check(user):
    current_user = UserModuleProfile.objects.filter(user=user)
    if current_user:
        current_user = current_user[0]
    else:
        return True
    print(current_user.admin)
    return current_user.admin

def sms_test(request, to_number = '', message = 'Hello'):
    url = 'http://mydesk.brac.net/sms/api/push' # Set destination URL here
    # url = 'http://kobo.mpower-social.com:8008/project/sms-status/' # Set destination URL here
    post_fields = {'t': SMS_API_TOKEN, 'to_number':'01985468227', 'message':message}

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
    #print data 
    req = urllib2.Request(url, data)
    # req.add_header('HTTP_REFERER', 'http://kobo.mpower-social.com:8008/')
    #print req
    response = urllib2.urlopen(req)
    the_page = response.read()
    #print the_page
    return HttpResponse(the_page)

@login_required
def index(request):
    current_user = request.user
    user = UserModuleProfile.objects.filter(user_id=current_user.id)
    
    admin = False
    if user:
        admin = user[0].admin
    if current_user.is_superuser:
        users = UserModuleProfile.objects.all().order_by("user__username")
        admin = True
        # json_posts = json.dumps(list(users.values('id','user__username' ,'organisation_name__organization','user__email')))
    elif admin:
        org_id_list = get_organization_by_user(request.user)
        users = UserModuleProfile.objects.filter(organisation_name__in=org_id_list).order_by("user__username")
        # json_posts = json.dumps(list(users))
        admin = True
    else:
        users = user
        admin = False
    template = loader.get_template('usermodule/index.html')
    success = request.GET.get("user", False)
    context = RequestContext(request, {
            'users': users,
            'admin': admin,
            'success': success,
            'user_mgt':'user_mgt',
            # 'json_posts' : json_posts
        })
    return HttpResponse(template.render(context))

# rumman rb******8
@login_required
@user_passes_test(admin_check,login_url='/usermodule/')
def register(request):
    # Like before, get the request's context.
    context = RequestContext(request)
    admin_check = UserModuleProfile.objects.filter(user=request.user)

    if request.user.is_superuser:
        admin_check = True
    elif admin_check:
        admin_check = admin_check[0].admin
    # A boolean value for telling the template whether the registration was successful.
    # Set to False initially. Code changes value to True when registration succeeds.
    registered = False
    task_role_permission = TaskRolePermissionMap.objects.filter(name__name = 'Can Send Complain From App').first()
    js_role_id = task_role_permission.role.id if task_role_permission else '0'
    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST,admin_check=admin_check)

        # If the two forms are valid...
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            
            # form_bool_value = False
            # form_bool = request.POST.get("admin", "xxx")
            # if form_bool == "xxx":
            #     form_bool_value = False
            # else:
            #     form_bool_value = True
            
            #encrypted password is saved so that it can be saved in password history table
            tmp_pass = user.password
            encrypted_password = make_password(user.password)
            user.password = encrypted_password
            
            # if user is a brac csa type user then initially 
            # account should be inactive until verification.
            # if request.POST.get("account_type", "xxx") == str(BRAC_CSA_ROLE_ID):
            #     user.is_active = False
            # if request.POST.get("account_type", "xxx") == str(BRAC_MF_ROLE_ID):
            #     form_bool_value = True
            user.save()

            # Now sort out the UserProfile instance.
            # Since we need to set the user attribute ourselves, we set commit=False.
            # This delays saving the model until we're ready to avoid integrity problems.
            profile = profile_form.save(commit=False)
            # profile.organisation_name = request.POST.get("organisation_name", "-1")
            profile.user = user
            expiry_months_delta = 3
            # Date representing the next expiry date
            next_expiry_date = (datetime.today() + timedelta(expiry_months_delta*365/12))
            profile.expired = next_expiry_date
            # profile.admin = form_bool_value
            profile.admin = profile.account_type.is_admin
            # profile.organisation_name = Organizations.objects.filter(pk=BRAC_ORD_ID).first()
            profile.organisation_name = profile.account_type.organization
            branch = request.POST.get("branch", "xxx")
            if branch == "xxx":
                profile.branch = None
            # Now we save the UserProfile model instance.
            profile.save()

            # UserRoleMap
            user_role_map = UserRoleMap(user = profile,role = profile.account_type)
            user_role_map.save()

            # Update our variable to tell the template registration was successful.
            registered = True

            #insert password into password history
            passwordHistory = UserPasswordHistory(user_id = user.id,date = datetime.now())
            passwordHistory.password = encrypted_password
            passwordHistory.save()

            msg = "Your pin number is " + user.username + " password is " + tmp_pass +"."
            if profile.branch:
                msg += "\nYour branch code: " + profile.branch.branch_id + "\nBranch Name: " + profile.branch.name + "\nAddress: "+ profile.branch.address
            sms_test(request, to_number = profile.contact, message = msg)
            return HttpResponseRedirect('/usermodule/?user=success')
        # Invalid form or forms - mistakes or something else?
        # Print problems to the terminal.
        # They'll also be shown to the user.
        else:
            print user_form.errors, profile_form.errors
            # profile_form = UserProfileForm(admin_check=admin_check)

    # Not a HTTP POST, so we render our form using two ModelForm instances.
    # These forms will be blank, ready for user input.
    else:
        user_form = UserForm()
        # get request users org and the orgs he can see then pass it to model choice field
        org_id_list = get_organization_by_user(request.user)
        #print context
        current_user = UserModuleProfile.objects.filter(user=request.user).first()
        current_user_role = UserRoleMap.objects.filter(user=current_user).values('role_id').first()
        #user = UserModuleProfile.objects.filter(user_id=current_user.user_id)
        #alist = UserRoleMap.objects.filter(user=current_user) #.values('role')
        #print current_user_role["role_id"]

        if not request.user.is_superuser:
		if current_user_role["role_id"] == 4:
		    accessebile_role_list=[3]
		elif current_user_role["role_id"] == 5: #bKash Admin
		    accessebile_role_list = [3,4,5]
		elif current_user_role["role_id"] == 1:
		    accessebile_role_list=[2]
		elif current_user_role["role_id"] == 6: #Brac Admin
		    accessebile_role_list=[2,1,6]
		else:
		    accessebile_role_list=[]
        else:
        	accessebile_role_list=[]       
        #print accessebile_role_list      
       
        # org id list is not available for superuser's like kobo
        if not org_id_list:
            UserProfileForm.base_fields['account_type'] = forms.ModelChoiceField(queryset=OrganizationRole.objects.all(),empty_label="Select a Organization Role")
        else:
            UserProfileForm.base_fields['account_type'] = forms.ModelChoiceField(queryset=OrganizationRole.objects.filter(organization__pk__in=org_id_list,id__in=accessebile_role_list)
,empty_label="Select a Organization Role")
        profile_form = UserProfileForm(admin_check=admin_check)

    # Render the template depending on the context.
    return render_to_response(
            'usermodule/register.html',
            {'user_form': user_form, 'profile_form': profile_form,
             'registered': registered,'js_role_id':js_role_id},
            context)


@login_required
def edit_profile(request,user_id):
    context = RequestContext(request)
    edited = False
    task_role_permission = TaskRolePermissionMap.objects.filter(name__name = 'Can Send Complain From App').first()
    js_role_id = task_role_permission.role.id if task_role_permission else '0'
    user = get_object_or_404(User, id=user_id)
    profile = get_object_or_404(UserModuleProfile, user_id=user_id)
    admin_check = UserModuleProfile.objects.filter(user=request.user)
    if request.user.is_superuser:
        admin_check = True
    elif admin_check:
        admin_check = admin_check[0].admin
    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        user_form = UserEditForm(data=request.POST,instance=user,user=request.user)
        profile_form = UserProfileForm(data=request.POST,instance=profile, admin_check = admin_check)
        # If the two forms are valid...
        if user_form.is_valid() and profile_form.is_valid():
            edited_user = user_form.save(commit=False);
            # password_new = request.POST['password']
            # if password_new:
            #     edited_user.set_password(password_new)
            edited_user.save()
            # form_bool_value = False
            # if request.POST.get("account_type", "xxx") == str(BRAC_MF_ROLE_ID):
            #     form_bool_value = True
            # form_bool = request.POST.get("admin", "xxx")
            # if form_bool == "xxx":
            #     form_bool_value = False
            # else:
            #     form_bool_value = True
            # Now sort out the UserProfile instance.
            # Since we need to set the user attribute ourselves, we set commit=False.
            # This delays saving the model until we're ready to avoid integrity problems.
            profile = profile_form.save(commit=False)
            # profile.organisation_name = request.POST.get("organisation_name", "-1")
            # profile.admin = request.POST.get("admin", "False")
            profile.user = edited_user
            # profile.admin = form_bool_value
            profile.admin = profile.account_type.is_admin
            # profile.organisation_name = Organizations.objects.filter(pk=BRAC_ORD_ID).first()
            profile.organisation_name = profile.account_type.organization
            branch = request.POST.get("branch", "xxx")
            if branch == "xxx":
                profile.branch = None
            # Now we save the UserProfile model instance.
            profile.save()

            # Update our variable to tell the template registration was successful.
            edited = True
            user_role_map = UserRoleMap.objects.filter(user = profile).first()
            if user_role_map:
                user_role_map.role = profile.account_type
                user_role_map.save()
            else:
                user_role_map = UserRoleMap(user = profile,role = profile.account_type)
                user_role_map.save()
            return HttpResponseRedirect('/usermodule/?user=success')
        # Invalid form or forms - mistakes or something else?
        # Print problems to the terminal.
        # They'll also be shown to the user.
        else:
            # profile_form = UserProfileForm(admin_check=admin_check)
            print user_form.errors, profile_form.errors

    # Not a HTTP POST, so we render our form using two ModelForm instances.
    # These forms will be blank, ready for user input.
    else:
        user_form = UserEditForm(instance=user,user=request.user)
        org_id_list = get_organization_by_user(request.user)
        # org id list is not available for superuser's like kobo
        if not org_id_list:
            UserProfileForm.base_fields['account_type'] = forms.ModelChoiceField(queryset=OrganizationRole.objects.all(),empty_label="Select a Organization Role")
        else:
            UserProfileForm.base_fields['account_type'] = forms.ModelChoiceField(queryset=OrganizationRole.objects.filter(organization__pk__in=org_id_list)
,empty_label="Select a Organization Role")
        profile_form = UserProfileForm(instance = profile, admin_check = admin_check)

    return render_to_response(
            'usermodule/edit_user.html',
            {'id':user_id, 'user_form': user_form,'js_role_id':js_role_id,
             'profile_form': profile_form, 'edited': edited},
            context)


def get_organization_by_user(user):
    org_id_list = []
    current_user = UserModuleProfile.objects.filter(user_id=user.id)
    if current_user:
        current_user = current_user[0]
        all_organizations = get_recursive_organization_children(current_user.organisation_name,[])
        org_id_list = [org.pk for org in all_organizations]
    return org_id_list


# must pass an empty organization_list initally otherwise produces bug.
def get_recursive_organization_children(organization,organization_list=[]):
    organization_list.append(organization)
    observables = Organizations.objects.filter(parent_organization = organization)
    for org in observables:
        if org not in organization_list:
            organization_list = list((set(get_recursive_organization_children(org,organization_list))))
    return list(set(organization_list))


@login_required
#@user_passes_test(admin_check,login_url='/usermodule/')
def organization_index(request):
    context = RequestContext(request)
    all_organizations = []
    if request.user.is_superuser:
        all_organizations = Organizations.objects.all()
    else:
        current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
        if current_user:
            current_user = current_user[0]
        all_organizations = get_recursive_organization_children(current_user.organisation_name,[])
        all_organizations.remove(current_user.organisation_name)
    message = ""
    alert = ""
    org_del_message = request.GET.get('org_del_message')
    org_del_message2 = request.GET.get('org_del_message2')
    return render_to_response(
            'usermodule/organization_list.html',
            {'all_organizations':all_organizations,"message":message,"alert":alert,
            'org_del_message':org_del_message,'org_del_message2':org_del_message2,
            'organization_mgt':'organization_mgt'
            },
            context)


@login_required
@user_passes_test(admin_check,login_url='/')
def add_organization(request):
    # Like before, get the request's context.
    context = RequestContext(request)
    all_organizations = []
    if request.user.is_superuser:
        all_organizations = Organizations.objects.all()
        OrganizationForm.base_fields['parent_organization'] = forms.ModelChoiceField(queryset=all_organizations,empty_label="Select a Organization",required=False)
    else:
        current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
        if current_user:
            current_user = current_user[0]
        all_organizations = get_recursive_organization_children(current_user.organisation_name,[])
        org_id_list = [org.pk for org in all_organizations]
        # org_id_list = list(set(org_id_list))
        OrganizationForm.base_fields['parent_organization'] = forms.ModelChoiceField(queryset=Organizations.objects.filter(pk__in=org_id_list),empty_label="Select a Parent Organization")
    # A boolean value for telling the template whether the registration was successful.
    # Set to False initially. Code changes value to True when registration succeeds.
    is_added_organization = False
    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        organization_form = OrganizationForm(data=request.POST)
        if organization_form.is_valid():
            organization_form.save()
            is_added_organization = True
            return HttpResponseRedirect('/usermodule/organizations/')
        else:
            #print organization_form.errors
            return render_to_response(
            'usermodule/add_organization.html',
            {'all_organizations':all_organizations,'organization_form': organization_form,'is_added_organization': is_added_organization},
            context)
    else:
        organization_form =  OrganizationForm()
    # Render the template depending on the context.
        return render_to_response(
            'usermodule/add_organization.html',
            {'all_organizations':all_organizations,'organization_form': organization_form,
            'is_added_organization': is_added_organization,'organization_mgt':'organization_mgt'},
            context)


@login_required
@user_passes_test(admin_check,login_url='/')
def edit_organization(request,org_id):
    context = RequestContext(request)
    edited = False
    organization = get_object_or_404(Organizations, id=org_id)
    all_organizations = []
    if request.user.is_superuser:
        all_organizations = Organizations.objects.filter(~Q(id = organization.pk))
        OrganizationForm.base_fields['parent_organization'] = forms.ModelChoiceField(queryset=all_organizations,empty_label="Select a Organization",required=False)
    else:
        current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
        if current_user:
            current_user = current_user[0]
        all_organizations = get_recursive_organization_children(current_user.organisation_name,[])
        org_id_list = [org.pk for org in all_organizations]
        org_id_list.remove(organization.pk)
        OrganizationForm.base_fields['parent_organization'] = forms.ModelChoiceField(queryset=Organizations.objects.filter(pk__in=org_id_list),empty_label="Select a Parent Organization")
    
    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        organization_form = OrganizationForm(data=request.POST,instance=organization)
        if organization_form.is_valid():
            organization_form.save()
            edited = True
            return HttpResponseRedirect('/usermodule/organizations/')
        else:
            #print organization_form.errors
            return render_to_response(
            'usermodule/edit_organization.html',
            {'org_id':org_id,'organization_form': organization_form, 'edited': edited},
            context)
        # Not a HTTP POST, so we render our form using two ModelForm instances.
        # These forms will be blank, ready for user input.
    else:
        organization_form = OrganizationForm(instance=organization)
    return render_to_response(
            'usermodule/edit_organization.html',
            {'org_id':org_id,'organization_form': organization_form, 'edited': edited},
            context)


@login_required
@user_passes_test(admin_check,login_url='/')
def delete_organization(request,org_id):
    context = RequestContext(request)
    org = Organizations.objects.get(pk = org_id)
    try:
        org.delete()
    except ProtectedError:
        org_del_message = """User(s) are assigned to this organization,
        please delete those users or assign them a different organization
        before deleting this organization"""

        org_del_message2 = """Or, This Organization may be parent of 
        one or more organization(s), Change their parent to some other organization."""
        
        return HttpResponseRedirect('/usermodule/organizations/?org_del_message='+org_del_message+"&org_del_message2="+org_del_message2)
    return HttpResponseRedirect('/usermodule/organizations/')


@login_required
@user_passes_test(admin_check,login_url='/')
def organization_access_list(request):
    param_user_id = request.POST['id']
    response_data = []
    observer = get_object_or_404(Organizations, id=param_user_id)
    all_organizations = get_recursive_organization_children(observer,[])
    for org in all_organizations:
        data = {}
        data["observer"] = observer.organization
        data["observable"] = org.organization
        response_data.append(data)
    return HttpResponse(json.dumps(response_data), content_type="application/json")


@login_required
#@user_passes_test(admin_check,login_url='/usermodule/')
def timeconfig_view(request):
    context = RequestContext(request)
    all_organizations = []
    #if request.user.is_superuser:
    all_organizations = working_hour.objects.all()
    #else:
       # current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
      #  if current_user:
       #     current_user = current_user[0]
      #  all_organizations = get_recursive_organization_children(current_user.organisation_name,[])
      #  all_organizations.remove(current_user.organisation_name)
    message = ""
    alert = ""
    org_del_message = request.GET.get('org_del_message')
    org_del_message2 = request.GET.get('org_del_message2')
    query = "select given_sla_time from sla_time"
    df = pandas.DataFrame()
    df = pandas.read_sql(query,connection)
    if not df.empty:
        given_sla = df.given_sla_time.tolist()[0]
    else:
        given_sla = ""
    print(given_sla)
    return render_to_response(
            'usermodule/time_list.html',
            {'all_organizations':all_organizations,"message":message,"alert":alert,
            'org_del_message':org_del_message,'org_del_message2':org_del_message2,
            'time_mgt':'time_mgt','given_sla':given_sla
            },
            context)




@login_required
@user_passes_test(admin_check, login_url='/')
def edit_time(request, org_id):
    context = RequestContext(request)
    edited = False
    organization = get_object_or_404(working_hour, id=org_id)
    all_organizations = []
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        time_form = TimeForm(data=request.POST, instance=organization)

        # If the two forms are valid...
        if time_form.is_valid():
            edited_time = time_form.save(commit=False)
            edited_time.save()
            edited = True
            #return HttpResponseRedirect('/usermodule/timeconfig-view')
        else:
            print time_form.errors

    # Not a HTTP POST, so we render our form using two ModelForm instances.
    # These forms will be blank, ready for user input.
    else:
        time_form = TimeForm(instance=organization)

    return render_to_response(
        'usermodule/edit_time.html',
        {'id': org_id, 'time_form': time_form,
         'edited': edited, 'menu_mgt': 'menu_mgt'},
        context)


def __db_commit_query(query):
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    cursor.close()

@csrf_exempt
def insert_sla_time(request):
    given_sla_time = request.POST.get('given_sla_time')
    del_query = "delete from sla_time"
    __db_commit_query(del_query)
    insert_query = "insert into sla_time(given_sla_time)values('"+str(given_sla_time)+"')"
    __db_commit_query(insert_query)
    return HttpResponse()

@login_required
@user_passes_test(admin_check,login_url='/')
def delete_user(request,user_id):
    context = RequestContext(request)
    user = User.objects.get(pk = user_id)
    # deletes the user from both user and rango
    user.delete()
    return HttpResponseRedirect('/usermodule/')


def change_password(request):
    context = RequestContext(request)
    if request.GET.get('userid'):
        edit_user = get_object_or_404(User, pk = request.GET.get('userid')) 
        logged_in_user = edit_user.username
        change_password_form = ChangePasswordForm(logged_in_user=logged_in_user)
        #change_password_form.fields.['username'].widget.attrs['readonly']=True
    else:
        change_password_form = ChangePasswordForm()
    # change_password_form = ChangePasswordForm()
    # Take the user back to the homepage.
    if request.method == 'POST':
        # expiry_months_delta: password change after how many months
        expiry_months_delta = 3
        # Date representing the next expiry date
        next_expiry_date = (datetime.today() + timedelta(expiry_months_delta*365/12))

        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        change_password_form = ChangePasswordForm(data=request.POST)
        username = request.POST['username']
        old_password = request.POST['old_password']
        new_password = request.POST['new_password']
        current_user = authenticate(username=username, password=old_password)

        if change_password_form.is_valid() and current_user is not None:
            print("here")
            """ current user is authenticated and also new password
             is available so change the password and redirect to
             home page with notification to user """
            encrypted_password = make_password(new_password)
            current_user.password = encrypted_password
            current_user.save()

            passwordHistory = UserPasswordHistory(user_id = current_user.id,date = datetime.now())
            passwordHistory.password = encrypted_password
            passwordHistory.save()

            # profile = get_object_or_404(UserModuleProfile, user_id=current_user.id)
            # profile.expired = next_expiry_date
            # profile.save()
            login(request,current_user)
            return HttpResponseRedirect('/usermodule/')
            # else:
                #     return HttpResponse('changed your own password buddy')
                # return HttpResponse( (datetime.now()+ timedelta(days=30)) )
        else:

            return render_to_response(
                    'usermodule/change_password.html',
                    {'change_password_form': change_password_form,'invalid':True},
                    context)

    return render_to_response(
                'usermodule/change_password.html',
                {'change_password_form': change_password_form},
                context)

@login_required
@user_passes_test(admin_check,login_url='/')
def reset_password(request,reset_user_id):
    context = RequestContext(request)
    reset_password_form = ResetPasswordForm()
    reset_user = get_object_or_404(User, pk=reset_user_id)
    reset_user_profile = get_object_or_404(UserModuleProfile,user=reset_user)
    if request.method == 'POST':
        # expiry_months_delta: password change after how many months
        expiry_months_delta = 3
        # Date representing the next expiry date
        next_expiry_date = (datetime.today() + timedelta(expiry_months_delta*365/12))

        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        reset_password_form = ResetPasswordForm(data=request.POST)
        
        if reset_password_form.is_valid() and reset_user is not None:
            """ current user is authenticated and also new password
             is available so change the password and redirect to
             home page with notification to user """
            encrypted_password = make_password(request.POST['new_password'])
            reset_user.password = encrypted_password
            reset_user.save()

            passwordHistory = UserPasswordHistory(user_id = reset_user.id,date = datetime.now())
            passwordHistory.password = encrypted_password
            passwordHistory.save()

            reset_user_profile.expired = next_expiry_date
            reset_user_profile.save()
            
            return HttpResponseRedirect('/usermodule/')
        else:
            return render_to_response(
                    'usermodule/reset_password.html',
                    {'reset_user':reset_user,'reset_password_form': reset_password_form,'invalid':True},
                    context)

    return render_to_response(
                'usermodule/reset_password.html',
                {'reset_password_form': reset_password_form,
                'reset_user':reset_user,'id':reset_user_id,
                },
                context)


def user_login(request):
    # Like before, obtain the context for the user's request.
    context = RequestContext(request)
    logger = logging.getLogger(__name__)
    redirect_url = '/project/dashboard/'
    # If the request is a HTTP POST, try to pull out the relevant information.
    if request.method == 'POST':
        # Gather the username and password provided by the user.
        # This information is obtained from the login form.
        username = request.POST['username']
        password = request.POST['password']

        # Use Django's machinery to attempt to see if the username/password
        # combination is valid - a User object is returned if it is.
        user = authenticate(username=username, password=password)

        # If we have a User object, the details are correct.
        # If None (Python's way of representing the absence of a value), no user
        # with matching credentials was found.
        if user:
            # number of login attempts allowed
            max_allowed_attempts = 5
            # count of invalid logins in db
            counter_login_attempts = UserFailedLogin.objects.filter(user_id=user.id).count()
            # check for number of allowed logins if it crosses limit do not login.
            if counter_login_attempts > max_allowed_attempts:
                # return HttpResponse("Your account is locked for multiple invalid logins, contact admin to unlock")
                return error_page(request,"Your account is locked for multiple invalid logins, contact admin to unlock")
                
            # Is the account active? It could have been disabled.
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            print x_forwarded_for
            if x_forwarded_for:
                 ip = x_forwarded_for.split(',')[0]
            else:
                 ip = request.META.get('REMOTE_ADDR')

            if user.is_active:
                if hasattr(user, 'usermoduleprofile'):
                    current_user = user.usermoduleprofile
                    # if date.today() > current_user.expired.date():
                    #     return HttpResponseRedirect('/usermodule/change-password')
                login(request, user)
                user_access = UserAccessLog()
                user_access.user = user
                user_access.login_time = user.last_login
                user_access.logout_time = request.session.get_expiry_date()
                user_access.user_ip=ip
                user_access.user_browser=request.user_agent.browser.family
                user_access.save()
                # print "last login",user.last_login
                # print "next logout",request.session.get_expiry_date()
                UserFailedLogin.objects.filter(user_id=user.id).delete()
                #print "##########################################"
                if not request.user.is_superuser:
		    logged_user = UserModuleProfile.objects.filter(user=request.user).first()
		    current_user_role = UserRoleMap.objects.filter(user=logged_user).values('role_id').first()
                    #print "##########################################" + str(current_user_role["role_id"])
                    if current_user_role["role_id"] == 2:
                        logout(request)
                        return error_page(request,"You are not authorized")
		    if current_user_role["role_id"] == 3 or current_user_role["role_id"] == 4 :

                        return HttpResponseRedirect('/project/new-complain/')
                    else:
                        redirect_url = '/project/dashboard/'
		        #return HttpResponseRedirect('/usermodule/')
                        return HttpResponseRedirect(request.POST['redirect_url'])
                else:
                    redirect_url = '/project/dashboard/'
		    #return HttpResponseRedirect('/usermodule/')
                    return HttpResponseRedirect(request.POST['redirect_url'])

            else:
                # An inactive account was used - no logging in!
                # return HttpResponse("Your User account is disabled.")
                return error_page(request,"Your User account is disabled")
        else:
            # Bad login details were provided. So we c an't log the user in.
            try:
                attempted_user_id = User.objects.get(username=username).pk
            except User.DoesNotExist:
                return HttpResponse("Invalid login details supplied when login attempted.")
            UserFailedLogin(user_id = attempted_user_id).save()
            # #print "Invalid login details: {0}, {1}".format(username, password)
            # return HttpResponse("Invalid login details supplied.")
            return error_page(request,"Invalid login details supplied")

    # The request is not a HTTP POST, so display the login form.
    # This scenario would most likely be a HTTP GET.
    else:
        #print "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%"
        if not request.user.is_anonymous:
            logged_user = UserModuleProfile.objects.filter(user=request.user).first()
            current_user_role = UserRoleMap.objects.filter(user=logged_user).values('role_id').first()
            if request.GET.get('next'):
                # print request.GET.get('next')
                redirect_url = request.GET.get('next')
            else:
                # redirect_url = '/usermodule/'
                if current_user_role["role_id"] == 3 or current_user_role["role_id"] == 4 :
                    redirect_url = '/project/new-complain/'
                else:
                    redirect_url = '/project/dashboard/'
        # No context variables to pass to the template system, hence the
        # blank dictionary object...
        return render_to_response('usermodule/login.html', {'redirect_url':redirect_url}, context)


@login_required
@user_passes_test(admin_check,login_url='/')
def locked_users(request):
    # Since we know the user is logged in, we can now just log them out.
    current_user = request.user
    users = []
    message = ''
    max_failed_login_attempts = 5

    user = UserModuleProfile.objects.filter(user_id=current_user.id)
    admin = False
    if user:
        admin = user[0].admin

    if current_user.is_superuser or admin:
        failed_logins = UserFailedLogin.objects.all().values('user_id').annotate(total=Count('user_id')).order_by('user_id')
        for f_login in failed_logins:
            if f_login['total'] > max_failed_login_attempts:
                user = UserModuleProfile.objects.filter(user_id=f_login['user_id'])[0]
                users.append(user)
    else:
        return HttpResponseRedirect("/usermodule/")
    if not users:
        message = "All the user accounts are unlocked"

    # Take the user back to the homepage.
    template = loader.get_template('usermodule/locked_users.html')
    context = RequestContext(request, {
            'users': users,
            'message':message,
            'locked_users':'locked_users'
        })
    return HttpResponse(template.render(context))


@login_required
def unlock(request):
    param_user_id = request.POST['id']
    current_user = request.user
    response_data = {}
    
    user = UserModuleProfile.objects.filter(user_id=current_user.id)
    admin = False
    if user:
        admin = user[0].admin

    if current_user.is_superuser or admin:
        UserFailedLogin.objects.filter(user_id=param_user_id).delete()
        response_data['message'] = 'User unlocked'
    else:
        response_data['message'] = 'You are not authorized to unlock'

    return HttpResponse(json.dumps(response_data), content_type="application/json")


@login_required
def user_logout(request):
    # Since we know the user is logged in, we can now just log them out.
    user_access = UserAccessLog.objects.filter(user = request.user).order_by("-login_time").first()
    if user_access:
        user_access.logout_time = timezone.now()
        user_access.save()
    logout(request)
    # Take the user back to the homepage.
    return HttpResponseRedirect('/usermodule/login/')


# =======================================================================================
@login_required
@user_passes_test(admin_check,login_url='/')
def add_menu(request):
    context = RequestContext(request)
    all_menu = MenuItem.objects.all()
    # A boolean value for telling the template whether the registration was successful.
    # Set to False initially. Code changes value to True when registration succeeds.
    is_added_menu = False

    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        menu_form = MenuForm(data=request.POST)
        # If the two forms are valid...
        if menu_form.is_valid():
            menu =menu_form.save()
            menu.save()
            is_added_menu = True
            return HttpResponseRedirect('/usermodule/menu-list/')
        else:
            print menu_form.errors

    # Not a HTTP POST, so we render our form using two ModelForm instances.
    # These forms will be blank, ready for user input.
    else:
        menu_form = MenuForm()
    
    # Render the template depending on the context.
    return render_to_response(
        'usermodule/add_menu.html',
        {'all_menu':all_menu,'menu_form': menu_form,
        'is_added_menu': is_added_menu,'menu_mgt':'menu_mgt'},
        context)


@login_required
@user_passes_test(admin_check,login_url='/')
def menu_index(request):
    context = RequestContext(request)
    all_menu = MenuItem.objects.all().order_by("sort_order")
    return render_to_response(
            'usermodule/menu_list.html',
            {'all_menu':all_menu,'menu_mgt':'menu_mgt'},
            context)


@login_required
@user_passes_test(admin_check,login_url='/')
def edit_menu(request,menu_id):
    context = RequestContext(request)
    edited = False

    menu = get_object_or_404(MenuItem, id=menu_id)
    
    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        menu_form = MenuForm(data=request.POST,instance=menu)
        
        # If the two forms are valid...
        if menu_form.is_valid():
            edited_user = menu_form.save(commit=False);
            edited_user.save()
            edited = True
            return HttpResponseRedirect('/usermodule/menu-list')
        else:
            print menu_form.errors

    # Not a HTTP POST, so we render our form using two ModelForm instances.
    # These forms will be blank, ready for user input.
    else:
        menu_form = MenuForm(instance=menu)

    return render_to_response(
            'usermodule/edit_menu.html',
            {'id':menu_id, 'menu_form': menu_form,
            'edited': edited,'menu_mgt':'menu_mgt'},
            context)


@login_required
@user_passes_test(admin_check,login_url='/')
def delete_menu(request,menu_id):
    context = RequestContext(request)
    menu = MenuItem.objects.get(pk = menu_id)
    # deletes the user from both user and rango
    menu.delete()
    return HttpResponseRedirect('/usermodule/menu-list')


# =========================================================
# Roles based on Organization CRUD
@login_required
@user_passes_test(admin_check,login_url='/')
def add_role(request):
    context = RequestContext(request)
    # A boolean value for telling the template whether the registration was successful.
    # Set to False initially. Code changes value to True when registration succeeds.
    is_added_role = False

    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        role_form = OrganizationRoleForm(data=request.POST)
        # If the two forms are valid...
        if role_form.is_valid():
            role_form.save()
            is_added_role = True
        else:
            print role_form.errors

    # Not a HTTP POST, so we render our form using two ModelForm instances.
    # These forms will be blank, ready for user input.
        return HttpResponseRedirect('/usermodule/roles-list/')
    else:
        if request.user.is_superuser:
            OrganizationRoleForm.base_fields['organization'] = forms.ModelChoiceField(queryset=Organizations.objects.all(),empty_label="Select a Organization")
            role_form = OrganizationRoleForm()
        else:
            org_id_list = get_organization_by_user(request.user)
            OrganizationRoleForm.base_fields['organization'] = forms.ModelChoiceField(queryset=Organizations.objects.filter(pk__in=org_id_list),empty_label="Select a Organization")
            role_form = OrganizationRoleForm()
    # Render the template depending on the context.
        return render_to_response(
            'usermodule/add_role.html',
            {'role_form': role_form,
            'is_added_role': is_added_role,
            'roles_mgt':'roles_mgt'},
            context)


@login_required
@user_passes_test(admin_check,login_url='/')
def roles_index(request):
    context = RequestContext(request)
    # filter orgs based on logged in user
    if request.user.is_superuser:
        all_roles = OrganizationRole.objects.all().order_by("organization")
    else:
        user = get_object_or_404(UserModuleProfile, user=request.user)
        all_roles = OrganizationRole.objects.filter(organization = user.organisation_name)
    return render_to_response(
            'usermodule/roles_list.html',
            {'all_roles':all_roles,'roles_mgt':'roles_mgt'},
            context)


@login_required
@user_passes_test(admin_check, login_url='/')
def edit_role(request, role_id):
    context = RequestContext(request)
    edited = False
    role = get_object_or_404(OrganizationRole, id=role_id)
    if request.method == 'POST':
        role_form = OrganizationRoleForm(data=request.POST,instance=role)
        prev_admin_status = role.is_admin
        if role_form.is_valid():
            role_obj = role_form.save()
            if prev_admin_status != role_obj.is_admin:
                users = UserModuleProfile.objects.filter(account_type=role_obj)
                for user in users:
                    user.admin = role_obj.is_admin
                    user.save()
            edited = True
        else:
            print role_form.errors
    else:
        if request.user.is_superuser:
            OrganizationRoleForm.base_fields['organization'] = forms.ModelChoiceField(queryset=Organizations.objects.all(),empty_label="Select a Organization")
        else:
            org_id_list = get_organization_by_user(request.user)
            OrganizationRoleForm.base_fields['organization'] = forms.ModelChoiceField(queryset=Organizations.objects.filter(pk__in=org_id_list),empty_label="Select a Organization")
        role_form = OrganizationRoleForm(instance=role,initial = {'organization': role.organization,'role': role.role })    
        # role_form = OrganizationRoleForm(instance=role)
    return render_to_response(
            'usermodule/edit_role.html',
            {'id':role_id, 'role_form': role_form,
            'edited': edited,'roles_mgt':'roles_mgt'},
            context)


@login_required
@user_passes_test(admin_check,login_url='/')
def delete_role(request,role_id):
    context = RequestContext(request)
    role = OrganizationRole.objects.get(pk = role_id)
    # deletes the user from both user and rango
    role.delete()
    return HttpResponseRedirect('/usermodule/roles-list')


# =========================================================
@login_required
@user_passes_test(admin_check,login_url='/')
@csrf_exempt
def role_menu_map_index(request):
    context = RequestContext(request)
    insertList = []
    menu_dict = {}
    # filter orgs based on logged in user
    if request.method == 'POST':
        new_menu = request.POST.getlist('menu_id')
        print new_menu
        for val in new_menu:
            splitVal = val.split("__")
            instance = MenuRoleMap(role_id=splitVal[0], menu_id=splitVal[1])
            insertList.append(instance)

        MenuRoleMap.objects.all().delete()
        MenuRoleMap.objects.bulk_create(insertList)
        messages.success(request, '<i class="fa fa-check-circle"></i> Access List has been updated successfully!',
                         extra_tags='alert-success crop-both-side')
        return HttpResponseRedirect('/usermodule/role-menu-map-list/')
    else:
        if request.user.is_superuser:
            menu_items = MenuItem.objects.all()
            roles = OrganizationRole.objects.all()
            for role in roles:
                org_menu_list = MenuRoleMap.objects.filter(role=role.id).values_list('menu_id', flat=True)
                menu_dict[role.id] = org_menu_list

        else:
            menu_items = MenuItem.objects.all()
            current_user = UserModuleProfile.objects.filter(user_id=request.user.id)
            if current_user:
                current_user = current_user[0]
            all_organizations = get_recursive_organization_children(current_user.organisation_name, [])
            org_id_list = [org.pk for org in all_organizations]
            roles = OrganizationRole.objects.filter(organization__in=org_id_list)
            for role in roles:
                org_menu_list = MenuRoleMap.objects.filter(role=role.id).values_list('menu_id', flat=True)
                menu_dict[role.id] = org_menu_list
        return render_to_response(
            'usermodule/roles_menu_map_list.html',
            {'menu_items':menu_items, 'menu_dict':menu_dict,'roles':roles},context)


# Roles based on Organization CRUD
@login_required
@user_passes_test(admin_check,login_url='/')
def add_role_menu_map(request):
    context = RequestContext(request)
    is_added_role = False
    if request.method == 'POST':
        role_form = RoleMenuMapForm(data=request.POST)
        if role_form.is_valid():
            role_form.save()
            is_added_role = True
            messages.success(request, '<i class="fa fa-check-circle"></i> New access has been added successfully!',
                             extra_tags='alert-success crop-both-side')
            return HttpResponseRedirect('/usermodule/role-menu-map-list/')
        else:
            print
            role_form.errors
        return HttpResponseRedirect('/usermodule/role-menu-map-list/')
    else:
        if request.user.is_superuser:
            RoleMenuMapForm.base_fields['role'] = forms.ModelChoiceField(
                queryset=OrganizationRole.objects.all().order_by("organization"),
                empty_label="Select a Organization Role")

        else:
            org_id_list = get_organization_by_user(request.user)
            RoleMenuMapForm.base_fields['role'] = forms.ModelChoiceField(
                queryset=OrganizationRole.objects.filter(organization__in=org_id_list).order_by("organization"),
                empty_label="Select a Organization Role")
        role_form = RoleMenuMapForm()
        return render_to_response(
            'usermodule/add_role_menu_map.html',
            {'role_form': role_form,
             'is_added_role': is_added_role},
            context)


@login_required
@user_passes_test(admin_check, login_url='/')
def edit_role_menu_map(request, item_id):
    context = RequestContext(request)
    edited = False
    role_menu_map = get_object_or_404(MenuRoleMap, id=item_id)
    if request.method == 'POST':
        role_form = RoleMenuMapForm(data=request.POST, instance=role_menu_map)
        if role_form.is_valid():
            role_form.save()
            edited = True
            messages.success(request, '<i class="fa fa-check-circle"></i> This access has been edit successfully!',
                             extra_tags='alert-success crop-both-side')
            return HttpResponseRedirect('/usermodule/role-menu-map-list/')
        else:
            print
            role_form.errors
    else:
        if request.user.is_superuser:
            RoleMenuMapForm.base_fields['role'] = forms.ModelChoiceField(queryset=OrganizationRole.objects.all(),
                                                                         empty_label="Select a Organization Role")
        else:
            org_id_list = get_organization_by_user(request.user)
            RoleMenuMapForm.base_fields['role'] = forms.ModelChoiceField(
                queryset=OrganizationRole.objects.filter(organization__in=org_id_list),
                empty_label="Select a Organization Role")
        role_form = RoleMenuMapForm(instance=role_menu_map,
                                    initial={'role': role_menu_map.role, 'menu': role_menu_map.menu})
    return render_to_response(
        'usermodule/edit_role_menu_map.html',
        {'id': item_id, 'role_form': role_form,
         'edited': edited},
        context)


@login_required
@user_passes_test(admin_check, login_url='/')
def delete_role_menu_map(request, item_id):
    context = RequestContext(request)
    del_map_item = MenuRoleMap.objects.get(pk = item_id)
    del_map_item.delete()
    return HttpResponseRedirect('/usermodule/role-menu-map-list')


# =========================================================
@login_required
@user_passes_test(admin_check, login_url='/')
def organization_roles(request):
    context = RequestContext(request)
    if request.user.is_superuser:
        all_organizations = Organizations.objects.all()
    else:    
        org_id_list = get_organization_by_user(request.user)
        all_organizations = Organizations.objects.filter(pk__in=org_id_list)
    message = None
    if len(all_organizations) == 0:    
        message = "You do not have any Organizations under your supervision."
    return render_to_response(
            'usermodule/organization_roles.html',
            {'all_organizations':all_organizations,"message":message, 'organization_roles':'organization_roles'},
            context)


@login_required
@user_passes_test(admin_check, login_url='/')
def user_role_map(request, org_id=None):
    context = RequestContext(request)
    edited = False
    roles = OrganizationRole.objects.filter(organization=org_id)
    users = UserModuleProfile.objects.filter(organisation_name=org_id)
    message = None
    if len(roles) == 0 or len(users) == 0:    
        message = "Your organization must have atleast one user and one role before assignment."
    return render_to_response(
            'usermodule/user_role_map.html',
            {'id':org_id,
            'users' : users,
            'roles' : roles,
            'message':message,
            'organization_roles':'organization_roles',
            'edited': edited},
            context)


@login_required
@user_passes_test(admin_check, login_url='/')
def adjust_user_role_map(request, org_id=None):
    context = RequestContext(request)
    is_added = False
    roles = OrganizationRole.objects.filter(organization=org_id)
    users = UserModuleProfile.objects.filter(organisation_name=org_id)
    initial_list = []
    for user_item in users:
        alist = UserRoleMap.objects.filter(user=user_item.pk).values('role')
        mist = []
        for i in alist:
            mist.append( i['role'])
        initial_list.append({'user': user_item.pk,'role':mist,'username': user_item.user.username})

    UserRoleMapfForm.base_fields['role'] = forms.ModelChoiceField(queryset=roles,empty_label=None)
    PermisssionFormSet = formset_factory(UserRoleMapfForm,max_num=len(users))
    new_formset = PermisssionFormSet(initial=initial_list)
    
    if request.method == 'POST':
        new_formset = PermisssionFormSet(data=request.POST)
        for idx,user_role_form in enumerate(new_formset):
            # user_role_form = UserRoleMapfForm(data=request.POST)
            u_id = request.POST['form-'+str(idx)+'-user']
            mist = initial_list[idx]['role']
            current_user = UserModuleProfile.objects.get(pk=u_id)
            results = map(int, request.POST.getlist('role-'+str(idx+1)))
            deleter = list(set(mist) - set(results))
            for role_id in results:
                roley = OrganizationRole.objects.get(pk=role_id)
                try:
                    UserRoleMap.objects.get(user=current_user,role=roley)
                except ObjectDoesNotExist as e:
                    UserRoleMap(user=current_user,role=roley).save()
            for dely in deleter:
                loly = OrganizationRole.objects.get(pk=dely)
                ob = UserRoleMap.objects.get(user=current_user,role=loly).delete()
        return HttpResponseRedirect('/usermodule/user-role-map/'+org_id)
    
    return render_to_response(
            'usermodule/add_user_role_map.html',
            {
            'id':org_id,
            # 'formset':formset,
            'new_formset':new_formset,
            'roles':roles,
            'organization_roles':'organization_roles'
            },
            context)


def error_page(request,message = None):
    context = RequestContext(request)
    if not message:    
        message = "Something went wrong"
    return render_to_response(
            'usermodule/error_404.html',
            {'message':message,
            },
            context)


@csrf_exempt
def getBranches(request):
    region_id = request.GET.get('region')
    branches = Branch.objects.filter(Q(region=region_id)  & Q(status='active'))
    return render(request, 'usermodule/branch.html', {'branches': branches})

@csrf_exempt
def send_token_to_email(request):
    if request.method == 'POST':
        data = request.POST.get("data", "xxx")
        json_obj = json.loads(data)
        username = json_obj['username']
        print(json_obj)
        # username = request.POST.get('username')
        try:
            user = User.objects.get(username=username)
        except Exception:
            error_mes = {}
            error_mes['code'] = 403
            error_mes['message'] = 'Username Not Exists'
            return HttpResponse(json.dumps(error_mes), status=403)
        print(user.email)
        me = "demouserdev@gmail.com"
        my_password = r"demouser"
        recipient  = user.email

        msg = MIMEMultipart('alternative')
        msg['Subject'] = "BRAC CSA OTP"
        msg['From'] = me
        msg['To'] = recipient
        otp = get_random_string(length=32)


        html = '<html><body><p>Username: &nbsp;<strong>' + str(username) + '</strong><br>OTP: &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<strong>'+str(otp)+'</strong></p></body></html>'
        part2 = MIMEText(html, 'html')

        msg.attach(part2)

        # Send the message via gmail's regular server, over SSL - passwords are being sent, afterall
        s = smtplib.SMTP_SSL('smtp.gmail.com')
        # uncomment if interested in the actual smtp conversation
        # s.set_debuglevel(1)
        # do the smtp auth; sends ehlo if it hasn't been sent already
        s.login(me, my_password)

        s.sendmail(me, recipient, msg.as_string())
        s.quit()
        query = "insert into user_otp_token(username,otp_token,status)VALUES('"+str(username)+"','"+str(otp)+"',1)"
        __db_commit_query(query)
        return HttpResponse(1)
    error_mes = {}
    error_mes['code'] = 403
    error_mes['message'] = 'Failed'
    return HttpResponse(json.dumps(error_mes),status=403)

@csrf_exempt
def token_verification(request):
    if request.method == 'POST':
        data = request.POST.get("data", "xxx")
        json_obj = json.loads(data)
        username = json_obj['username']
        otp_token = json_obj['token']
        print(json_obj)
        # username = request.POST.get('username')
        # otp_token = request.POST.get('token')
        query = "select otp_token from  user_otp_token where status = 1 and username = '"+str(username)+"' order by created_at desc limit 1"
        df = pandas.DataFrame()
        df = pandas.read_sql(query,connection)
        if not df.empty:
            fetched_token = df.otp_token.tolist()[0]
            if otp_token == fetched_token:
                update_qry = "update user_otp_token set status = 0 where username = '"+str(username)+"'"
                __db_commit_query(update_qry)
                return HttpResponse(1)
            else:
                error_mes = {}
                error_mes['code'] = 403
                error_mes['message'] = 'OTP not matched'
                return HttpResponse(json.dumps(error_mes), status=403)
    error_mes = {}
    error_mes['code'] = 403
    error_mes['message'] = 'Failed'
    return HttpResponse(json.dumps(error_mes), status=403)


@csrf_exempt
def user_password_reset_mobile(request):
    if request.method == 'POST':
        data = request.POST.get("data", "xxx")
        json_obj = json.loads(data)
        print(json_obj)
        # username = request.POST.get('username')
        # password = request.POST.get('password')
        username = json_obj['username']
        password = json_obj['password']
        try:
            user = User.objects.get(username=username)
        except Exception:
            error_mes = {}
            error_mes['code'] = 403
            error_mes['message'] = 'Username Not Exists'
            return HttpResponse(json.dumps(error_mes), status=403)
        encrypted_password = make_password(password)
        user.password = encrypted_password
        user.save()
        return HttpResponse(1)
    error_mes = {}
    error_mes['code'] = 403
    error_mes['message'] = 'Failed'
    return HttpResponse(json.dumps(error_mes), status=403)