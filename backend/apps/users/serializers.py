from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from apps.users.models import User, UserRole
from apps.organisations.serializers import OrganisationSimpleSerializer
from apps.organisations.services import OrganisationService


class UserSerializer(serializers.ModelSerializer):
    organisation = serializers.SerializerMethodField()
    organisations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'organisation', 'organisations']
        read_only_fields = ['id', 'email', 'name', 'role', 'organisation', 'organisations']

    def get_organisation(self, obj: User):
        if obj.role == UserRole.CLIENT_VIEWER and obj.organisation:
            return OrganisationSimpleSerializer(obj.organisation).data
        return None

    def get_organisations(self, obj: User):
        if obj.role == UserRole.CONSULTANT:
            orgs = OrganisationService.get_organisations_for_user(obj)
            return OrganisationSimpleSerializer(orgs, many=True).data
        return None


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data

