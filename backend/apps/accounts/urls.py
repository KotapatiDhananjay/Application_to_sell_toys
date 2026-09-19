from django.urls import path
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import AddressViewSet, LoginView, MeView, RegisterView

router = SimpleRouter()
router.register("addresses", AddressViewSet, basename="address")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    *router.urls,
]