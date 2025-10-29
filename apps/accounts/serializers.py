from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Company, CompanyMember


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""

    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label='Confirm Password')

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'password2']

    def validate(self, attrs):
        """Validate that passwords match"""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        """Create new user"""
        validated_data.pop('password2')
        user = User.objects.create_user(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password']
        )
        return user


class CompanySerializer(serializers.ModelSerializer):
    """Serializer for Company model"""

    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'industry', 'location', 'column_config', 'currency',
            'top_products_threshold', 'dead_stock_days', 'created_at',
            'created_by', 'created_by_email', 'member_count'
        ]
        read_only_fields = ['id', 'created_at', 'created_by']

    def get_member_count(self, obj):
        """Get count of company members"""
        return obj.members.count()


class CompanyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a company"""

    class Meta:
        model = Company
        fields = [
            'name', 'industry', 'location', 'column_config', 'currency',
            'top_products_threshold', 'dead_stock_days'
        ]

    def create(self, validated_data):
        """Create company and add creator as admin member"""
        user = self.context['request'].user
        company = Company.objects.create(
            created_by=user,
            **validated_data
        )
        # Add creator as admin member
        CompanyMember.objects.create(
            company=company,
            user=user,
            role='admin'
        )
        return company


class CompanyMemberSerializer(serializers.ModelSerializer):
    """Serializer for CompanyMember model"""

    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = CompanyMember
        fields = ['id', 'company', 'company_name', 'user', 'user_email', 'user_name', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']

    def get_user_name(self, obj):
        """Get full name of user"""
        return f"{obj.user.first_name} {obj.user.last_name}".strip()


class AddCompanyMemberSerializer(serializers.Serializer):
    """Serializer for adding a member to a company"""

    email = serializers.EmailField(required=True)
    role = serializers.ChoiceField(choices=CompanyMember.ROLE_CHOICES, required=True)

    def validate_email(self, value):
        """Validate that user exists"""
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")
        return value

    def create(self, validated_data):
        """Add user to company"""
        company = self.context['company']
        user = User.objects.get(email=validated_data['email'])

        # Check if user is already a member
        if CompanyMember.objects.filter(company=company, user=user).exists():
            raise serializers.ValidationError("User is already a member of this company.")

        member = CompanyMember.objects.create(
            company=company,
            user=user,
            role=validated_data['role']
        )
        return member
