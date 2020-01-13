from django.contrib.auth.hashers import make_password, check_password
from usermodule.models import UserModuleProfile, UserPasswordHistory,Organizations,OrganizationDataAccess,MenuItem
from project_data.models import Branch, Region
from django.contrib.auth.models import User
from django import forms
from datetime import datetime, timedelta
from usermodule.models import OrganizationRole
from usermodule.models import MenuRoleMap
from usermodule.models import UserRoleMap
from usermodule.models import Task, TaskRolePermissionMap,working_hour

from django.utils.translation import ugettext as _, ugettext_lazy
from usermodule.helpers import COUNTRIES

class UserForm(forms.ModelForm):
    password = forms.CharField(label='Create a password',widget=forms.PasswordInput(),min_length=8)
    password_repeat = forms.CharField(label='Confirm your password',widget=forms.PasswordInput())
    email = forms.EmailField(required=True)
    username = forms.CharField(label="User Name", help_text='',max_length=20,widget=forms.TextInput(attrs={'pattern': '[a-z._0-9]+','title':'only lowercase letter, numbers and underscore(_) is allowed. example: user_2009'}))
    first_name = forms.CharField(label="Name", help_text='',max_length=30,widget=forms.TextInput(attrs={'pattern': '[.a-zA-Z\s]+','title':'only letters dot and space are allowed. example: Alam'}))
    is_active = forms.BooleanField(required=False,help_text='',initial=True,label='Account Active')
    # date_joined = forms.CharField(widget=forms.HiddenInput(),initial=datetime.now()) 
    def clean_password_repeat(self):
        password1 = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password_repeat')

        if password1 and password1!=password2:
            raise forms.ValidationError('Passwords Do not match')
        return self.cleaned_data

    class Meta:
        model = User
        # fields = ('username', 'email', 'password','user_permissions','is_staff','is_active','is_superuser','date_joined','groups')
        fields = ('username', 'first_name','is_active', 'email', 'password') # ,'is_superuser' 'date_joined',


class UserEditForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    username = forms.CharField(label="User Name",help_text='',max_length=20)
    first_name = forms.CharField(label="Name", help_text='',max_length=30,widget=forms.TextInput(attrs={'pattern': '[.a-zA-Z\s]+','title':'only letters dot and space are allowed. example: Alam'}))
    is_active = forms.BooleanField(required=False,help_text='',initial=True,label='Account Active')
    
    class Meta:
        model = User
        fields = ('username','first_name','is_active', 'email') # ,'is_superuser','date_joined'
        
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['readonly'] = 'true'
        

class UserProfileForm(forms.ModelForm):
    # admin = forms.BooleanField(label="Make this User Admin",widget=forms.CheckboxInput(),required=False)
    # employee_id = forms.CharField(label="Employee Id ")
    # organisation_name = forms.ModelChoiceField(label='Organisation Name',required=True,queryset=Organizations.objects.all(),empty_label="Select an Organization")
    # country = forms.ChoiceField(choices=COUNTRIES, required=True, label='Country')
    # position = forms.CharField(label="Position")

    # expired = forms.DateTimeField(label="Expiry Date",required=False,initial=datetime.now()+ timedelta(days=90))
    branch = forms.ModelChoiceField(label='Branch',required=False,queryset=Branch.objects.none(), empty_label = "Select a Branch")
    region = forms.ModelChoiceField(label='Region',required=False,queryset=Region.objects,empty_label="Select a Region")
    contact = forms.CharField(label="Contact", help_text='',widget=forms.TextInput(attrs={'pattern': '(01)[0-9]{9}','title':'only numbers are allowed, must start with 01 .'}))
    class Meta:
        model = UserModuleProfile
        # fields = ('admin','employee_id','organisation_name','country','position','psu')
        fields = ('address', 'contact', 'account_type','region','branch')
    def __init__(self, *args, **kwargs):
        admin_check = kwargs.pop('admin_check', False)
        super(UserProfileForm, self).__init__(*args, **kwargs)
        if not admin_check:
            del self.fields['account_type']
        if 'region' in self.data:
            try:
                region_id = int(self.data.get('region'))
                self.fields['branch'].queryset = Branch.objects.filter(region=region_id).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty City queryset
        elif self.instance.pk:
            try:
                self.fields['branch'].queryset = self.instance.region.branch_set.order_by('name')
            except:
                self.fields['region'].queryset = Region.objects
                self.fields['branch'].queryset = Branch.objects.none()

class OrganizationForm(forms.ModelForm):
    organization = forms.CharField(label='Organization',required=True)
    # parent_organization = forms.ModelChoiceField(label='Parent Organization',required=True,queryset=Organizations.objects.all(),empty_label="Select an Organization")
    class Meta:
        model = Organizations
        fields = ('organization','parent_organization')


class OrganizationDataAccessForm(forms.ModelForm):
    observer_organization = forms.ModelChoiceField(label='Parent Organization',required=True,queryset=Organizations.objects.all(),empty_label="Select an Organization")
    observable_organization = forms.ModelChoiceField(label='Partner Organization',required=True,queryset=Organizations.objects.all(),empty_label="Select an Organization")
    class Meta:
        model = OrganizationDataAccess
        fields = ('observer_organization','observable_organization')

# Roles based on organization Form
class OrganizationRoleForm(forms.ModelForm):
    # organization = forms.ModelChoiceField(label='Organization',required=True,queryset=Organizations.objects.all(),empty_label="Select an Organization")
    # role = forms.CharField(label='Role',required=True)
    class Meta:
        model = OrganizationRole
        fields = ('organization','role','is_admin')        


class ChangePasswordForm(forms.Form):
    username = forms.CharField(label="Username",required=True)
    old_password = forms.CharField(label="Old",required=True,widget=forms.PasswordInput(),min_length=8)
    new_password = forms.CharField(label="New",required=True,widget=forms.PasswordInput(),min_length=8)
    retype_new_password = forms.CharField(label="Retype new",required=True,widget=forms.PasswordInput())
    def clean_retype_new_password(self):
        old_password = self.cleaned_data.get('old_password')
        new_password = self.cleaned_data.get('new_password')
        retype_new_password = self.cleaned_data.get('retype_new_password')
        username = self.cleaned_data.get('username')

        if old_password and new_password == old_password:
            raise forms.ValidationError('New Password Cannot be same as old password')

        if new_password and new_password!=retype_new_password:
            raise forms.ValidationError('Passwords Do not match')

        # check password history (last 25) if it already existed before
        #get current user id
        try:
            current_user_id = User.objects.get(username=username).pk
        except User.DoesNotExist:
            raise forms.ValidationError('Username you entered is incorrect')
        # get list of last 24 password
        count_unusable_recent_password = 24
        password_list = UserPasswordHistory.objects.filter(user_id=current_user_id).order_by('-date').values('password')[:count_unusable_recent_password][::-1]

        for i in password_list:
            flag = check_password(new_password,i['password'])
            if(flag):
                raise forms.ValidationError('You cannot reuse your last '+str(count_unusable_recent_password)+ 'password as your new password')

        # UserModuleProfile.objects.filter(position='Junior Software Engineer').order_by('-id').values()[:3][::-1]
        # UserPasswordHistory.objects.filter(user_id=5).order_by('-date').values()[:2][::-1]
        return self.cleaned_data


    def __init__(self, *args, **kwargs):
        logged_in_user = kwargs.pop('logged_in_user', None)
        super(ChangePasswordForm, self).__init__(*args, **kwargs)
        if logged_in_user:
            self.fields['username'].initial = logged_in_user
        self.fields['username'].widget.attrs['readonly'] = True


class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(label="New",required=True,widget=forms.PasswordInput(),min_length=8)
    retype_new_password = forms.CharField(label="Retype new",required=True,widget=forms.PasswordInput())
    def clean_retype_new_password(self):
        new_password = self.cleaned_data.get('new_password')
        retype_new_password = self.cleaned_data.get('retype_new_password')
        
        if new_password and new_password!=retype_new_password:
            raise forms.ValidationError('Passwords Do not match')

        return self.cleaned_data   
        

class MenuForm(forms.ModelForm):
    title = forms.CharField(label="Title",required=True)
    url = forms.CharField(label="Url",required=True)
    list_class = forms.CharField(label="Menu List Class")
    icon_class = forms.CharField(label="Menu Icon Class")
    parent_menu = forms.ModelChoiceField(label='Parent Menu',required=False,queryset=MenuItem.objects.all(),empty_label="Parent Menu")

    class Meta:
        model = MenuItem
        fields = ('title','url','list_class','icon_class','parent_menu','sort_order')

# Roles based on organization Form
class RoleMenuMapForm(forms.ModelForm):
    class Meta:
        model = MenuRoleMap
        fields = ('role', 'menu')


# Roles based on organization Form
class UserRoleMapForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=UserModuleProfile.objects.all(), empty_label="(Nothing)")
    role = forms.ModelChoiceField(queryset=OrganizationRole.objects.all(), empty_label="(Nothing)")
    class Meta:
        model = UserRoleMap
        fields = ('user', 'role')

class UserRoleMapfForm(forms.Form):
    # user = forms.ModelChoiceField(queryset=UserModuleProfile.objects.all(), empty_label="(Nothing)")
    user = forms.CharField(label='user', widget=forms.HiddenInput())
    role = forms.ModelChoiceField(queryset=OrganizationRole.objects.all(), empty_label=None,widget=forms.CheckboxSelectMultiple())    

PERM_CHOICES = (
        ('view', ugettext_lazy('Can view')),
        ('edit', ugettext_lazy('Can edit')),
        ('report', ugettext_lazy('Can submit to')),
    )

class ProjectPermissionForm(forms.Form):
    user = forms.CharField(label='user', widget=forms.HiddenInput())
    # role = forms.ModelChoiceField(queryset=OrganizationRole.objects.all(), empty_label=None,widget=forms.CheckboxSelectMultiple())
    perm_type = forms.ChoiceField(choices=PERM_CHOICES, widget=forms.CheckboxSelectMultiple())


# Roles based on organization Form
class TaskRolePermissionMapForm(forms.ModelForm):
    class Meta:
        model = TaskRolePermissionMap
        fields = ('name', 'role')

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ('name',)

class TimeForm(forms.ModelForm):
    day_name = forms.CharField(label="Day Name",required=True)
    start_time = forms.CharField(label="Start Time(HH:MM:SS)",required=True)
    end_time = forms.CharField(label="End Time(HH:MM:SS)", required=True)


    class Meta:
        model = working_hour
        fields = ('day_name','start_time','end_time')