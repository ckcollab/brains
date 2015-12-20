from django.http import HttpResponse


def index(request):
    return HttpResponse("Hey I am brains!")
