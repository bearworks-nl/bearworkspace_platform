from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from apps.accounts.models import User, AVATAR_CHOICES, ROLE_CHOICES
from apps.environments.models import Environment, EnvironmentMembership
from .models import Company


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone', 'job_title')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-input'}),
            'phone':      forms.TextInput(attrs={'class': 'form-input'}),
            'job_title':  forms.TextInput(attrs={'class': 'form-input'}),
        }


class AvatarForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('avatar',)


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        exclude = ('user', 'mollie_customer_id', 'created_at', 'updated_at')
        widgets = {f: forms.TextInput(attrs={'class': 'form-input'}) for f in
                   ['name', 'address_line1', 'address_line2', 'city',
                    'postal_code', 'country', 'vat_number', 'kvk_number', 'phone']}


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
    )
    # Environments to assign this user to (multi-select)
    environments = forms.ModelMultipleChoiceField(
        queryset=Environment.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Assign to environments',
    )
    membership_role = forms.ChoiceField(
        choices=[('env_admin', 'Environment Admin'), ('env_member', 'Environment Member')],
        initial='env_member',
        widget=forms.Select(attrs={'class': 'form-input'}),
        label='Role in selected environments',
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role', 'password')
        widgets = {
            'email':      forms.EmailInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-input'}),
            'role':       forms.Select(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, requesting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if requesting_user and requesting_user.is_superadmin:
            self.fields['environments'].queryset = Environment.objects.all()
            # Superadmin can assign any role including superadmin
            self.fields['role'].choices = ROLE_CHOICES
        elif requesting_user:
            # env_admin: only their own environments, only non-superadmin roles
            admin_env_ids = EnvironmentMembership.objects.filter(
                user=requesting_user, role='env_admin'
            ).values_list('environment_id', flat=True)
            self.fields['environments'].queryset = Environment.objects.filter(pk__in=admin_env_ids)
            self.fields['role'].choices = [
                ('env_admin',  'Environment Admin'),
                ('env_member', 'Environment Member'),
            ]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    environments = forms.ModelMultipleChoiceField(
        queryset=Environment.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Assign to environments',
    )
    membership_role = forms.ChoiceField(
        choices=[('env_admin', 'Environment Admin'), ('env_member', 'Environment Member')],
        widget=forms.Select(attrs={'class': 'form-input'}),
        label='Role in selected environments',
        required=False,
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role', 'is_active')
        widgets = {
            'email':      forms.EmailInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-input'}),
            'role':       forms.Select(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, requesting_user=None, target_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if requesting_user and requesting_user.is_superadmin:
            self.fields['environments'].queryset = Environment.objects.all()
            self.fields['role'].choices = ROLE_CHOICES
        elif requesting_user:
            admin_env_ids = EnvironmentMembership.objects.filter(
                user=requesting_user, role='env_admin'
            ).values_list('environment_id', flat=True)
            self.fields['environments'].queryset = Environment.objects.filter(pk__in=admin_env_ids)
            self.fields['role'].choices = [
                ('env_admin',  'Environment Admin'),
                ('env_member', 'Environment Member'),
            ]

        # Pre-select environments the target user is already a member of
        if target_user:
            current_memberships = EnvironmentMembership.objects.filter(user=target_user)
            self.fields['environments'].initial = [m.environment_id for m in current_memberships]
            # Pre-fill membership_role from the first membership found (most common role)
            first = current_memberships.first()
            if first:
                self.fields['membership_role'].initial = first.role


def _visible_users(requesting_user):
    """
    Return the queryset of users visible to the requesting user.
    - Superadmin: all users.
    - env_admin: only users who share at least one environment membership with them.
    """
    if requesting_user.is_superadmin:
        return User.objects.all().order_by('-created_at')

    # Get all environment IDs this admin manages
    admin_env_ids = EnvironmentMembership.objects.filter(
        user=requesting_user, role='env_admin'
    ).values_list('environment_id', flat=True)

    # Get all user IDs that are members of those environments
    member_user_ids = EnvironmentMembership.objects.filter(
        environment_id__in=admin_env_ids
    ).values_list('user_id', flat=True)

    return User.objects.filter(pk__in=member_user_ids).order_by('-created_at')


def _sync_memberships(user, environments, membership_role):
    """
    Replace the user's memberships in the given environments.
    Memberships in other environments are left untouched.
    """
    env_ids = [e.pk for e in environments]
    # Remove memberships in the selected set (we'll re-create them)
    EnvironmentMembership.objects.filter(user=user, environment_id__in=env_ids).delete()
    # Add new memberships
    for env in environments:
        EnvironmentMembership.objects.create(user=user, environment=env, role=membership_role)


# ────────────────────────────────────────────────
# Profile views
# ────────────────────────────────────────────────

@login_required
def profile(request):
    company, _ = Company.objects.get_or_create(
        user=request.user, defaults={'name': request.user.display_name}
    )
    memberships = EnvironmentMembership.objects.filter(
        user=request.user
    ).select_related('environment')
    return render(request, 'users/profile.html', {
        'profile_form':  ProfileForm(instance=request.user),
        'avatar_form':   AvatarForm(instance=request.user),
        'company_form':  CompanyForm(instance=company),
        'avatar_choices': AVATAR_CHOICES,
        'current_avatar': request.user.avatar,
        'memberships':   memberships,
    })


@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
    return redirect('users:profile')


@login_required
def avatar_edit(request):
    if request.method == 'POST':
        form = AvatarForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Avatar updated.')
    return redirect('users:profile')


@login_required
def company_edit(request):
    company, _ = Company.objects.get_or_create(
        user=request.user, defaults={'name': request.user.display_name}
    )
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Company information updated.')
    return redirect('users:profile')


# ────────────────────────────────────────────────
# User management views
# ────────────────────────────────────────────────

@login_required
def user_list(request):
    if not request.user.is_env_admin:
        messages.error(request, 'Access denied.')
        return redirect('core:dashboard')

    users = _visible_users(request.user)

    # Annotate each user with their memberships for display
    users_with_memberships = []
    for u in users:
        memberships = EnvironmentMembership.objects.filter(
            user=u
        ).select_related('environment')
        users_with_memberships.append((u, memberships))

    return render(request, 'users/user_list.html', {
        'users_with_memberships': users_with_memberships,
    })


@login_required
def user_create(request):
    if not request.user.is_env_admin:
        messages.error(request, 'Access denied.')
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = UserCreateForm(request.POST, requesting_user=request.user)
        if form.is_valid():
            user = form.save()
            environments   = form.cleaned_data.get('environments', [])
            membership_role = form.cleaned_data.get('membership_role', 'env_member')
            if environments:
                _sync_memberships(user, environments, membership_role)
            messages.success(request, f'User {user.email} created.')
            return redirect('users:user_list')
    else:
        form = UserCreateForm(requesting_user=request.user)

    return render(request, 'users/user_form.html', {
        'form': form,
        'title': 'Create User',
    })


@login_required
def user_edit(request, pk):
    if not request.user.is_env_admin:
        messages.error(request, 'Access denied.')
        return redirect('core:dashboard')

    # env_admin can only edit users visible to them
    visible_ids = _visible_users(request.user).values_list('pk', flat=True)
    user = get_object_or_404(User, pk=pk)
    if not request.user.is_superadmin and user.pk not in list(visible_ids):
        messages.error(request, 'Access denied.')
        return redirect('users:user_list')

    if request.method == 'POST':
        form = UserEditForm(
            request.POST,
            instance=user,
            requesting_user=request.user,
            target_user=user,
        )
        if form.is_valid():
            form.save()
            environments    = form.cleaned_data.get('environments', [])
            membership_role = form.cleaned_data.get('membership_role', 'env_member')
            if environments is not None:
                _sync_memberships(user, environments, membership_role)
            messages.success(request, 'User updated.')
            return redirect('users:user_list')
    else:
        form = UserEditForm(
            instance=user,
            requesting_user=request.user,
            target_user=user,
        )

    return render(request, 'users/user_form.html', {
        'form': form,
        'title': 'Edit User',
        'edit_user': user,
    })


@login_required
def user_delete(request, pk):
    if not request.user.is_superadmin:
        messages.error(request, 'Access denied.')
        return redirect('core:dashboard')
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted.')
        return redirect('users:user_list')
    return render(request, 'users/user_confirm_delete.html', {'target_user': user})
