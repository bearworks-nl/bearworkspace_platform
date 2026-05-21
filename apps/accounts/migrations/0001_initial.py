from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False)),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
                ('email', models.EmailField(unique=True)),
                ('role', models.CharField(choices=[('superadmin','Super Admin'),('customer_admin','Customer Admin'),('env_admin','Environment Admin'),('customer_member','Customer Member')], default='customer_admin', max_length=20)),
                ('avatar', models.CharField(choices=[('avatar_1','Astronaut'),('avatar_2','Robot'),('avatar_3','Fox'),('avatar_4','Owl'),('avatar_5','Bear'),('avatar_6','Lion'),('avatar_7','Dragon'),('avatar_8','Penguin'),('avatar_9','Ninja'),('avatar_10','Wizard'),('avatar_11','Pirate'),('avatar_12','Cat')], default='avatar_1', max_length=20)),
                ('phone', models.CharField(blank=True, max_length=30)),
                ('job_title', models.CharField(blank=True, max_length=100)),
                ('is_onboarded', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('groups', models.ManyToManyField(blank=True, related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={'verbose_name': 'User', 'verbose_name_plural': 'Users'},
        ),
    ]
