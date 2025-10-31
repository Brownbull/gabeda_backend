#!/usr/bin/env python
"""
Promote a user to superuser status.
Usage: python promote_superuser.py
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from apps.accounts.models import User

def promote_to_superuser(email):
    """Promote user to superuser."""
    try:
        user = User.objects.get(email=email)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print(f"✅ SUCCESS: {email} is now a superuser!")
        print(f"   - is_staff: {user.is_staff}")
        print(f"   - is_superuser: {user.is_superuser}")
        return True
    except User.DoesNotExist:
        print(f"❌ ERROR: User with email {email} does not exist.")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    EMAIL = "carcamo.gabriel@gmail.com"
    print(f"Promoting {EMAIL} to superuser...")
    promote_to_superuser(EMAIL)
