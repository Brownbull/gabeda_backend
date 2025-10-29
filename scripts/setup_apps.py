"""
Setup script to create Django app structure.
Run this with: python setup_apps.py
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

def create_app_files(app_name):
    """Create all files for a Django app"""
    app_dir = BASE_DIR / 'apps' / app_name
    app_dir.mkdir(parents=True, exist_ok=True)

    files = {
        '__init__.py': '',
        'admin.py': f'''from django.contrib import admin

# Register your models here.
''',
        'apps.py': f'''from django.apps import AppConfig


class {app_name.capitalize()}Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.{app_name}'
''',
        'models.py': f'''from django.db import models

# Create your models here.
''',
        'views.py': f'''from django.shortcuts import render
from rest_framework import viewsets

# Create your views here.
''',
        'serializers.py': f'''from rest_framework import serializers

# Create your serializers here.
''',
        'urls.py': f'''from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
]
''',
        'tests.py': f'''from django.test import TestCase

# Create your tests here.
''',
    }

    for filename, content in files.items():
        filepath = app_dir / filename
        if not filepath.exists():
            filepath.write_text(content)
            print(f"Created: {filepath}")

    # Create migrations folder
    migrations_dir = app_dir / 'migrations'
    migrations_dir.mkdir(exist_ok=True)
    (migrations_dir / '__init__.py').write_text('')
    print(f"Created: {migrations_dir}/__init__.py")

if __name__ == '__main__':
    # Create apps/__init__.py
    apps_init = BASE_DIR / 'apps' / '__init__.py'
    if not apps_init.exists():
        apps_init.write_text('# Apps package\n')
        print(f"Created: {apps_init}")

    # Create each app
    for app_name in ['accounts', 'analytics', 'common']:
        print(f"\n=== Creating {app_name} app ===")
        create_app_files(app_name)

    print("\n✅ All apps created successfully!")
    print("\nNext steps:")
    print("1. Add apps to INSTALLED_APPS in config/settings.py:")
    print("   'apps.accounts',")
    print("   'apps.analytics',")
    print("   'apps.common',")
    print("2. Run: python manage.py makemigrations")
    print("3. Run: python manage.py migrate")
