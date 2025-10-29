from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from django.db.models import Q
from .models import User, Company, CompanyMember
from .serializers import (
    UserSerializer,
    UserRegistrationSerializer,
    CompanySerializer,
    CompanyCreateSerializer,
    CompanyMemberSerializer,
    AddCompanyMemberSerializer
)


class RegisterView(generics.CreateAPIView):
    """API endpoint for user registration"""

    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({
            'user': UserSerializer(user).data,
            'message': 'User registered successfully. Please login to get your access token.'
        }, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """API endpoint for viewing and updating user profile"""

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class CompanyViewSet(viewsets.ModelViewSet):
    """API endpoint for managing companies"""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return CompanyCreateSerializer
        return CompanySerializer

    def get_queryset(self):
        """Return companies where user is a member"""
        user = self.request.user
        return Company.objects.filter(
            members__user=user
        ).distinct().order_by('-created_at')

    def perform_create(self, serializer):
        """Create company and add creator as admin"""
        serializer.save()

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get all members of a company"""
        company = self.get_object()
        members = CompanyMember.objects.filter(company=company)
        serializer = CompanyMemberSerializer(members, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """Add a member to the company"""
        company = self.get_object()

        # Check if requesting user is admin
        member = CompanyMember.objects.filter(
            company=company,
            user=request.user
        ).first()

        if not member or member.role != 'admin':
            return Response(
                {'error': 'Only administrators can add members.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AddCompanyMemberSerializer(
            data=request.data,
            context={'company': company}
        )
        serializer.is_valid(raise_exception=True)
        member = serializer.save()

        return Response(
            CompanyMemberSerializer(member).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['delete'])
    def remove_member(self, request, pk=None):
        """Remove a member from the company"""
        company = self.get_object()
        user_id = request.data.get('user_id')

        if not user_id:
            return Response(
                {'error': 'user_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if requesting user is admin
        requesting_member = CompanyMember.objects.filter(
            company=company,
            user=request.user
        ).first()

        if not requesting_member or requesting_member.role != 'admin':
            return Response(
                {'error': 'Only administrators can remove members.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Find and delete the member
        try:
            member = CompanyMember.objects.get(
                company=company,
                user_id=user_id
            )
            member.delete()
            return Response(
                {'message': 'Member removed successfully.'},
                status=status.HTTP_204_NO_CONTENT
            )
        except CompanyMember.DoesNotExist:
            return Response(
                {'error': 'Member not found.'},
                status=status.HTTP_404_NOT_FOUND
            )


class CompanyMemberViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing company memberships"""

    permission_classes = [IsAuthenticated]
    serializer_class = CompanyMemberSerializer

    def get_queryset(self):
        """Return memberships for the current user"""
        return CompanyMember.objects.filter(
            user=self.request.user
        ).select_related('company', 'user').order_by('-joined_at')
