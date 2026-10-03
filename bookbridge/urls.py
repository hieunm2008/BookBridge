from django.contrib import admin
from django.urls import include, path
from django.contrib.auth.views import LogoutView
from bridge.views import BookBridgeLoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', BookBridgeLoginView.as_view(), name='login'),
    path('accounts/logout/', LogoutView.as_view(), name='logout'),
    path('', include('bridge.urls')),
]
handler403 = 'bridge.views.error403'
handler404 = 'bridge.views.error404'
handler500 = 'bridge.views.error500'
