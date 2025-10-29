from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Company, CompanyMember


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for custom User model"""

    list_display = ['email', 'first_name', 'last_name', 'is_staff', 'is_active', 'created_at']
    list_filter = ['is_staff', 'is_active', 'created_at']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-created_at']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

    readonly_fields = ['created_at', 'updated_at']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Admin interface for Company model"""

    list_display = ['name', 'industry', 'location', 'currency', 'created_at', 'created_by']
    list_filter = ['industry', 'location', 'currency', 'created_at']
    search_fields = ['name', 'location']
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'industry', 'location')
        }),
        ('Configuration', {
            'fields': ('column_config', 'currency')
        }),
        ('Analysis Parameters', {
            'fields': ('top_products_threshold', 'dead_stock_days')
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by')
        }),
    )

    readonly_fields = ['created_at']


@admin.register(CompanyMember)
class CompanyMemberAdmin(admin.ModelAdmin):
    """Admin interface for CompanyMember model"""

    list_display = ['user', 'company', 'role', 'joined_at']
    list_filter = ['role', 'joined_at']
    search_fields = ['user__email', 'company__name']
    ordering = ['-joined_at']

    fieldsets = (
        (None, {
            'fields': ('company', 'user', 'role')
        }),
        ('Metadata', {
            'fields': ('joined_at',)
        }),
    )

    readonly_fields = ['joined_at']
