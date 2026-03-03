def log(level, source, message, detail='', user=None, request=None):

    try:
        from accounts.models import SystemLog
        ip = None
        if request:
            x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR')
        SystemLog.objects.create(
            level=level, source=source,
            message=message, detail=detail,
            user=user, ip=ip
        )
    except Exception:
        pass  # Never let logging crash the app