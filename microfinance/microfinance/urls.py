"""microfinance URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Import the include() function: from django.conf.urls import url, include
    3. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""

from django.conf.urls import include, url
from django.contrib import admin
from usermodule import views
# from project_data import views
urlpatterns = [
    # url(r'^/', include('usermodule.urls')),
    url(r'^$', views.index, name='index'),
    # url(r'^$', views.sms_test, name='sms_test'),
    url(r'^admin/', admin.site.urls),
    url(r'^polls/', include('polls.urls')),
    url(r'^usermodule/', include('usermodule.urls')),
    url(r'^project/', include('project_data.urls')),
    url(r'^bkash/', include('bkashmodule.urls')),
]
