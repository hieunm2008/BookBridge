from django.db import OperationalError
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin

class DatabaseBusyMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if isinstance(exception, OperationalError) and 'locked' in str(exception).lower():
            return render(request, 'error.html', {
                'code': '503', 'title': 'Hệ thống đang bận',
                'description': 'Dữ liệu chưa được lưu. Vui lòng quay lại và thử lại sau ít giây.',
            }, status=503)
