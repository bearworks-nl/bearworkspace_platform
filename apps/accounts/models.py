from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


AVATAR_CHOICES = [
    ('avatar_1', 'Astronaut'),
    ('avatar_2', 'Robot'),
    ('avatar_3', 'Fox'),
    ('avatar_4', 'Owl'),
    ('avatar_5', 'Bear'),
    ('avatar_6', 'Lion'),
    ('avatar_7', 'Dragon'),
    ('avatar_8', 'Penguin'),
    ('avatar_9', 'Ninja'),
    ('avatar_10', 'Wizard'),
    ('avatar_11', 'Pirate'),
    ('avatar_12', 'Cat'),
]

# Simplified role hierarchy:
#   superadmin   – full platform access, Django admin
#   env_admin    – manages assigned environments, sees only their users
#   env_member   – read access on assigned environments
ROLE_CHOICES = [
    ('superadmin', 'Super Admin'),
    ('env_admin',  'Environment Admin'),
    ('env_member', 'Environment Member'),
]


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'superadmin')
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='env_admin')
    avatar = models.CharField(max_length=20, choices=AVATAR_CHOICES, default='avatar_1')
    phone = models.CharField(max_length=30, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    is_onboarded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        return self.get_full_name() or self.email.split('@')[0]

    @property
    def is_superadmin(self):
        return self.role == 'superadmin' or self.is_superuser

    @property
    def is_env_admin(self):
        """True for superadmin and env_admin."""
        return self.role in ('superadmin', 'env_admin') or self.is_superuser

    # Keep old property name as alias so existing templates don't break immediately
    @property
    def is_customer_admin(self):
        return self.is_env_admin

    @property
    def avatar_url(self):
        return f'/static/img/avatars/{self.avatar}.svg'
