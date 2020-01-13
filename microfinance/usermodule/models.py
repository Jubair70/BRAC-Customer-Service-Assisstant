from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
from django.utils import timezone
# Create your models here.
from django.db.models import Count
from django.core.validators import RegexValidator

# extra imports 
# from onadata.apps.unicef.models import GeoPSU

class UserModuleProfile(models.Model):
    user = models.OneToOneField(User)
    expired = models.DateTimeField()
    # designation = models.CharField(max_length=200)
    # The additional attributes we wish to include.
    admin = models.BooleanField(default=False)
    # employee_id = models.CharField(max_length=50)
    organisation_name = models.ForeignKey('Organizations', on_delete=models.PROTECT)
    address = models.CharField(max_length=400, null=True)
    contact = models.CharField(max_length=100, null=True)
    # position = models.CharField(max_length=100, null=True)
    account_type = models.ForeignKey('OrganizationRole',related_name='user_role', on_delete=models.PROTECT)
    branch = models.ForeignKey('project_data.Branch',related_name='user_branch', on_delete=models.PROTECT,null=True)
    region = models.ForeignKey('project_data.Region',related_name='user_region', on_delete=models.PROTECT,null=True)
    security_code = models.CharField(max_length=100, null=True)
    # Override the __unicode__() method to return out something meaningful!
    def __str__(self):
        return self.user.username

    class Meta:
       app_label = 'usermodule'


class UserPasswordHistory(models.Model):
    user_id = models.IntegerField()
    password = models.CharField(max_length=150)
    # designation = models.CharField(max_length=200)
    date = models.DateTimeField()

    # Override the __unicode__() method to return out something meaningful!
    def __str__(self):
        return self.user


class UserFailedLogin(models.Model):
    user_id = models.IntegerField()
    login_attempt_time= models.DateTimeField(auto_now_add=True)


    def was_username(self):
        current_user= User.objects.get(id=self.user_id)
        return current_user;
    was_username.short_description = 'Username'

class UserAccessLog(models.Model):
    user = models.ForeignKey(User,related_name='auth_user_log_fk', on_delete=models.CASCADE)
    login_time = models.DateTimeField(default = timezone.now, blank=True, null=True)
    logout_time = models.DateTimeField(default = timezone.now, blank=True, null=True)
    user_ip=models.CharField(max_length=150)
    user_browser=models.CharField(max_length=150)

class UserSecurityCode(models.Model):
    user = models.ForeignKey(User,related_name='auth_user_fk', on_delete=models.CASCADE)
    code = models.CharField(max_length=10, null=True)
    generation_time = models.DateTimeField(default = timezone.now, blank=True)


class OrganizationDataAccess(models.Model):
    observer_organization = models.ForeignKey('Organizations',related_name='user_observer_organization', on_delete=models.CASCADE)
    observable_organization = models.ForeignKey('Organizations',related_name='user_observable_organization', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('observer_organization', 'observable_organization',)


class Organizations(models.Model):
    organization = models.CharField(max_length=150)
    parent_organization = models.ForeignKey('Organizations',blank=True, null=True,related_name='parent_org', on_delete=models.PROTECT)
    # Override the __unicode__() method to return out something meaningful!
    def __str__(self):
        return self.organization

    class Meta:
       app_label = 'usermodule'


class MenuItem(models.Model):
    title = models.CharField(max_length=150)
    url = models.CharField(max_length=150)
    list_class = models.CharField(max_length=150)
    icon_class = models.CharField(max_length=150)
    parent_menu = models.ForeignKey('MenuItem',blank=True, null=True, on_delete=models.CASCADE)
    sort_order = models.PositiveSmallIntegerField(default=0)
    def __str__(self):
        return self.title

# Role + Organization model
class OrganizationRole(models.Model):
    organization = models.ForeignKey('Organizations',related_name='role_organization_name', on_delete=models.CASCADE)
    role = models.CharField(max_length=150)
    is_admin = models.BooleanField(default=False)

    class Meta:
        unique_together = ('organization', 'role',)

    def __str__(self):
        return self.organization.organization + " => "+ self.role

# Role-Menu Permission Mapping
class MenuRoleMap(models.Model):
    role = models.ForeignKey('OrganizationRole',related_name='model_map_role', on_delete=models.CASCADE)
    menu = models.ForeignKey('MenuItem',related_name='model_map_menu', on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('role', 'menu',)
    
    def __str__(self):
        return self.role


# User-Role Permission Mapping
class UserRoleMap(models.Model):
    user = models.ForeignKey('UserModuleProfile',related_name='usermodule_role', on_delete=models.CASCADE)
    role = models.ForeignKey('OrganizationRole',related_name='map_user_role', on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('user','role',)
    
    def __str__(self):
        return self.user

class TaskRolePermissionMap(models.Model):
    name = models.ForeignKey('Task',related_name='taskname_map', on_delete=models.CASCADE)
    role = models.ForeignKey('OrganizationRole',related_name='taskrole_map', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name','role',)
    
    def __str__(self):
        return self.name

class Task(models.Model):
    name = models.CharField(max_length=150,unique = True)

    def __str__(self):
        return self.name

class working_hour(models.Model):
    day_name = models.CharField(max_length=150,unique = True)

    start_time = models.CharField(max_length=150, validators=[
            RegexValidator(
                regex='^[0-9][0-9]:[0-9][0-9]:[0-9][0-9]$',
                message='Invalid Start Time Format',
            ),
        ])
    end_time = models.CharField(max_length=150,
                                validators=[
                                    RegexValidator(
                                        regex='^[0-9][0-9]:[0-9][0-9]:[0-9][0-9]$',
                                        message='Invalid End Time Format',
                                    ),
                                ])

    def __str__(self):
        return self.day_name