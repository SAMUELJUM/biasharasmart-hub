from django.http import JsonResponse

def integration_status(request):
    return JsonResponse({"message": "Integrations endpoint working"})
