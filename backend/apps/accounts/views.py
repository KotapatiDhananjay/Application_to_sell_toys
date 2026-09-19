from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Address
from .serializers import (
    AddressSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(CreateAPIView):
    """POST /api/auth/register/ - create an account and log the user in."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ - returns {access, refresh, user}."""

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class MeView(RetrieveUpdateAPIView):
    """GET / PATCH /api/auth/me/ - the current user's profile."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


class AddressViewSet(viewsets.ModelViewSet):
    """CRUD for the logged-in user's saved addresses (never anyone else's)."""

    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # a user only has a handful of addresses

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        with transaction.atomic():
            was_default, user = instance.is_default, instance.user
            instance.delete()
            if was_default:  # promote the newest remaining address
                newest = Address.objects.filter(user=user).order_by("-created_at").first()
                if newest:
                    newest.is_default = True
                    newest.save()

    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, pk=None):
        address = self.get_object()
        address.is_default = True
        address.save()  # Address.save() demotes the previous default
        return Response(self.get_serializer(address).data)