from django.conf import settings
# from django.contrib.sites.models import Site
from usermodule.models import MenuItem,UserModuleProfile, OrganizationRole
from usermodule.models import MenuRoleMap,UserRoleMap
import sys 

# def site_name(request):
#     site_id = getattr(settings, 'SITE_ID', None)
#     try:
#         site = Site.objects.get(pk=site_id)
#     except Site.DoesNotExist:
#         site_name = 'example.org'
#     else:
#         site_name = site.name
#     return {'SITE_NAME': site_name}


def additional_menu_items(request):
    user = request.user._wrapped if hasattr(request.user,'_wrapped') else request.user
    menu_items = []
    sub_menu_items = []
    if not request.user.id == None:
        current_user = UserModuleProfile.objects.filter(user=request.user)
        if current_user:
            current_user = current_user[0]
            if request.user.is_superuser:
                menu_items = MenuItem.objects.exclude(parent_menu__isnull=False)
                sub_menu_items = MenuItem.objects.exclude(parent_menu__isnull=True)
            else:
                admin_menu = 0
                roles_list = UserRoleMap.objects.filter(user=current_user).values('role')
                for role in roles_list:
                    alist = MenuRoleMap.objects.filter(role=role['role']).values('menu')
                    mist = []
                    for i in alist:
                        mist.append( i['menu'])
                    role_menu_list = MenuItem.objects.filter(pk__in=mist).exclude(parent_menu__isnull=False)
                    role_submenu_list = MenuItem.objects.filter(pk__in=mist).exclude(parent_menu__isnull=True)
                    menu_items.extend(role_menu_list)
                    sub_menu_items.extend(role_submenu_list)
        else:
            menu_items = MenuItem.objects.exclude(parent_menu__isnull=False)
            sub_menu_items = MenuItem.objects.exclude(parent_menu__isnull=True)

    menu_items = list(set(menu_items))
    menu_items = sorted(menu_items, key=lambda x: x.sort_order)
    sub_menu_items = list(set(sub_menu_items))
    sub_menu_items = sorted(sub_menu_items, key=lambda x: x.sort_order)
    return {'main_menu_items': menu_items, 'sub_menu_items':sub_menu_items}


def is_admin(request):
    admin_menu = 0
    curr_user_role = ''
    user_id=''
    # user = request.user._wrapped if hasattr(request.user,'_wrapped') else request.user
    # if not user.is_anonymous():
    if request.user.is_authenticated():
        current_user = UserModuleProfile.objects.filter(user=request.user).first()
        current_user_role = UserRoleMap.objects.filter(user=current_user).values('role').first()
        #print ('roles_list',int(current_user_role['role']))

        if current_user is not None:
            # current_user = current_user[0]
            if current_user.admin:
                admin_menu = 1
                print('user is admin')
            else:
                admin_menu = 0
            #organization =  current_user.organisation_name.organization
            #print ('organisation',organization)
            org_curr_user_role = OrganizationRole.objects.filter(organization = current_user.organisation_name,id = current_user_role['role']).first()
            #for role in all_roles:

            #print ('organisation_all_roles::',all_roles)
            curr_user_role = str(org_curr_user_role.role)
            user_id = str(current_user.user_id)
            #print('current_user:: role', curr_user_role)
        else:
            admin_menu = 1
        user_id = request.user.id
    # print "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$" + user_id
    return {'admin_menu': admin_menu,'curr_user_role':curr_user_role,'user_id':user_id}
    
