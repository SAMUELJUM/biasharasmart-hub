from django.http import JsonResponse

def report_list(request):
    return JsonResponse({"message": "Reports endpoint working"})
