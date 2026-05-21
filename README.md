# WorkspaceManager

A full-stack Django 5 workspace management platform for Recast, Windows 365, and Intune — with usage-based billing via Mollie and RBAC access control.

## Stack

- **Backend**: Django 5 + Celery
- **Frontend**: HTMX-ready + Tailwind CDN + custom CSS design system
- **Database**: SQLite (dev) / PostgreSQL (production)
- **Billing**: Mollie recurring payments
- **APIs**: Microsoft Graph API (Windows 365 + Intune), Recast API
- **Hosting**: Azure-ready

---

## Quick Start (Windows, local dev, no Docker)

```powershell
# 1. Clone & setup
python -m venv venv
venv\Scripts\activate
pip install -r requirements/base.txt

# 2. Configure environment
copy .env.example .env
# Edit .env with your values (SQLite works out of the box)

# 3. Run migrations
python manage.py migrate

# 4. Create superuser
python manage.py createsuperuser

# 5. Set up billing schedule
python manage.py setup_billing_schedule

# 6. Start dev server
python manage.py runserver
```

Open http://127.0.0.1:8000

---

## Project Structure

```
workspace_manager/
├── apps/
│   ├── accounts/        # Custom User (email login), RBAC roles, avatars
│   ├── users/           # Profile, Company info, User management
│   ├── environments/    # Environments + memberships
│   ├── services/        # Recast, W365, Intune services + configurations
│   ├── billing/         # Plans, Subscriptions, Usage snapshots, Invoices
│   └── core/            # Dashboard, landing, context processors
├── templates/
│   ├── base.html        # Main layout: sidebar, topbar, theme system
│   ├── accounts/        # Login, register, password reset
│   ├── users/           # Profile (with avatar picker), user management
│   ├── environments/    # Environment CRUD
│   ├── services/        # Service enable, configure
│   ├── billing/         # Overview, invoices, plans
│   └── core/            # Dashboard, landing page
├── static/
│   └── img/avatars/     # 12 SVG avatars
└── workspace_manager/
    ├── settings.py
    ├── urls.py
    └── celery.py
```

---

## RBAC Roles

| Role | Access |
|------|--------|
| `superadmin` | Full access, user deletion, Django admin |
| `customer_admin` | User management, all environments & services |
| `env_admin` | Assigned environments only |
| `customer_member` | Read-only on assigned environments |

---

## Services

| Service | Config | Billed per |
|---------|--------|------------|
| Recast Application Workspace | URL + API key | Per workspace |
| Recast User License | URL + API key | Per org member |
| Windows 365 Cloud PC | App ID + Tenant ID | Per provisioned device |
| Microsoft Intune | App ID + Tenant ID + JSON policy | Per environment (flat) |

---

## Billing Flow

1. Superadmin creates Plans in Django admin (`/admin/`)
2. User enables a Service → Subscription auto-created (status: trialing)
3. Customer sets up Mollie payment mandate (first-payment flow)
4. Celery beat runs on the 1st of each month:
   - Snapshots usage per subscription
   - Creates Invoice records
   - Triggers Mollie recurring charge
5. Mollie webhook → updates invoice/subscription status

---

## Theme System

- **Dark / Light / System** mode (saved to `localStorage`)
- **6 preset accent colors** + custom hex picker
- **Collapsible sidebar** (mini/full modes)
- Theme panel: click the ⊞ sliders icon in the topbar

---

## Environment Variables

See `.env.example` for all options. Key ones:

```env
SECRET_KEY=your-secret-key
DEBUG=True
CELERY_TASK_ALWAYS_EAGER=True   # No Redis needed for local dev
MOLLIE_API_KEY=test_xxxx        # Mollie test key
```

---

## Production (Azure)

1. Set `DEBUG=False`
2. Configure PostgreSQL via `DB_*` env vars
3. Set up Redis for Celery: `REDIS_URL=redis://...`
4. Set `CELERY_TASK_ALWAYS_EAGER=False`
5. Run `python manage.py collectstatic`
6. Configure Mollie webhook URL: `https://yourdomain.com/billing/webhook/`
