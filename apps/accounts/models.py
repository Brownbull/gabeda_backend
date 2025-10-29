"""
User and Company models for multi-tenant authentication.
"""
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication"""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with email and password"""
        if not email:
            raise ValueError('Email address is required')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with email and password"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with email as username"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField('email address', unique=True, max_length=255)
    first_name = models.CharField('first name', max_length=100, blank=True)
    last_name = models.CharField('last name', max_length=100, blank=True)

    is_active = models.BooleanField('active', default=True)
    is_staff = models.BooleanField('staff status', default=False)
    is_superuser = models.BooleanField('superuser status', default=False)

    created_at = models.DateTimeField('date joined', default=timezone.now)
    updated_at = models.DateTimeField('last updated', auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'user'
        verbose_name_plural = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        """Return user's full name"""
        return f"{self.first_name} {self.last_name}".strip() or self.email


class Company(models.Model):
    """Multi-tenant company model"""

    INDUSTRY_CHOICES = [
        ('retail', 'Retail'),
        ('food_beverage', 'Food & Beverage'),
        ('services', 'Services'),
        ('manufacturing', 'Manufacturing'),
        ('wholesale', 'Wholesale'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('company name', max_length=255)
    industry = models.CharField(
        'industry',
        max_length=50,
        choices=INDUSTRY_CHOICES,
        default='retail'
    )
    location = models.CharField('location', max_length=100, default='Santiago, Chile')

    # Column mapping configuration (stored as JSON)
    column_config = models.JSONField(
        'column configuration',
        default=dict,
        blank=True,
        help_text="CSV column name mappings"
    )

    # Analysis parameters
    currency = models.CharField('currency', max_length=10, default='CLP')
    top_products_threshold = models.DecimalField(
        'top products threshold',
        max_digits=3,
        decimal_places=2,
        default=0.20,
        help_text="Percentage threshold for top products (0.20 = 20%)"
    )
    dead_stock_days = models.IntegerField(
        'dead stock days',
        default=30,
        help_text="Days without sales to consider product as dead stock"
    )

    created_at = models.DateTimeField('created at', auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='companies_created',
        verbose_name='created by'
    )

    class Meta:
        db_table = 'companies'
        verbose_name = 'company'
        verbose_name_plural = 'companies'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return self.name

    def get_column_config(self):
        """Get column config with defaults"""
        default_config = {
            'date_col': 'fecha',
            'product_col': 'producto',
            'description_col': 'glosa',
            'revenue_col': 'total',
            'quantity_col': 'cantidad',
            'transaction_col': 'trans_id',
            'cost_col': 'costo',
            'customer_col': 'customer_id',
        }
        return {**default_config, **self.column_config}


class CompanyMember(models.Model):
    """User membership in companies with roles (RBAC)"""

    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('business_owner', 'Business Owner'),
        ('analyst', 'Business Analyst'),
        ('operations_manager', 'Operations Manager'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name='company'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='user'
    )
    role = models.CharField('role', max_length=50, choices=ROLE_CHOICES)
    joined_at = models.DateTimeField('joined at', auto_now_add=True)

    class Meta:
        db_table = 'company_members'
        verbose_name = 'company member'
        verbose_name_plural = 'company members'
        unique_together = [('company', 'user')]
        indexes = [
            models.Index(fields=['company', 'user']),
            models.Index(fields=['user']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.company.name} ({self.get_role_display()})"
