from django.shortcuts import render,render_to_response

# Create your views here.
from django.http import HttpResponse
from django.template import RequestContext,loader
from microfinance.settings import *
import sys

def index(request):
    context = RequestContext(request)
    # return HttpResponse(xxx)
    return render_to_response(
            'base.html',
            {},
            context)