from django.contrib.auth.models import User

def get_test_user():
    user, _ = User.objects.get_or_create(username="test")
    return user