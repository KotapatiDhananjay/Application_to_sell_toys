from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Address

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """The logged-in user's profile. Email and admin flag are read-only."""

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "phone", "is_admin", "date_joined")
        read_only_fields = ("id", "email", "is_admin", "date_joined")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "phone", "password", "password_confirm")
        extra_kwargs = {
            "email": {"validators": []},  # we check uniqueness (case-insensitive) ourselves
            "first_name": {"required": True, "allow_blank": False},
            "last_name": {"required": True, "allow_blank": False},
        }

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        candidate = User(
            email=attrs["email"],
            first_name=attrs["first_name"],
            last_name=attrs["last_name"],
        )
        try:  # runs Django's password rules (length, common, numeric, similarity)
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        try:
            return User.objects.create_user(password=password, **validated_data)
        except IntegrityError:  # two simultaneous sign-ups with the same email
            raise serializers.ValidationError(
                {"email": "An account with this email already exists."}
            )


class LoginSerializer(TokenObtainPairSerializer):
    """JWT login by email. Adds the user profile to the token response."""

    def validate(self, attrs):
        attrs[self.username_field] = attrs[self.username_field].strip().lower()
        data = super().validate(attrs)  # raises 401 for bad credentials / inactive user
        data["user"] = UserSerializer(self.user).data
        return data


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = (
            "id", "label", "full_name", "phone", "line1", "line2", "city",
            "state", "postal_code", "country", "is_default", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_is_default(self, value):
        # A user must always keep one default address once they have any.
        if self.instance and self.instance.is_default and value is False:
            raise serializers.ValidationError(
                "Choose another address as the default instead."
            )
        return value