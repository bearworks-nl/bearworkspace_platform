# Admin Dashboard

Django + HTMX + Tailwind admin dashboard with customer management, product integrations (Recast Application Workspace, Windows 365, Microsoft Intune), usage-based subscriptions via Mollie, and PostgreSQL.

## Stack

| Layer | Technology |
|---|---|
| Backend | Django 5, Python 3.12 |
| Frontend | Django templates + HTMX + Tailwind CSS (CDN) |
| Database | PostgreSQL 16 |
| Task queue | Celery + Redis |
| Payments | Mollie (subscriptions + mandates) |
| MS integrations | MSAL + Microsoft Graph API |
| Deployment | Azure App Service + Azure DB for PostgreSQL |

## Project structure

```
dashboard/
├── config/              # Django settings, URLs, Celery, WSGI
├── apps/
│   ├── accounts/        # Custom user model, auth, password reset
│   ├── customers/       # Customer CRUD
│   ├── organisations/   # Organisations/teams + memberships
│   ├── products/        # Product instances, Recast/W365/Intune configs, Graph API
│   └── billing/         # Plans, subscriptions, usage snapshots, invoices, Mollie
├── templates/           # Django HTML templates
│   └── partials/        # HTMX partial fragments
├── static/              # CSS / JS / images
└── requirements/
    └── base.txt
```

## Local setup

### 1. Clone and configure environment

```bash
cp .env.example .env
# Edit .env with your values
```

### 2. Start with Docker Compose

```bash
docker compose up -d
```

### 3. Run migrations and create superuser

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

### 4. Set up billing schedule

```bash
docker compose exec web python manage.py setup_billing_schedule
```

### 5. Open the dashboard

Visit http://localhost:8000 and sign in.

## Data model hierarchy

```
Customer
└── Organisation (many per customer)
    └── ProductInstance (many per org, one per product type)
        ├── RecastWorkspaceConfig
        ├── Windows365Config → CloudPC[]
        ├── IntuneConfig → IntunePolicy[]
        └── Subscription → UsageSnapshot[] → Invoice[]
```

## RBAC roles

| Role | Access |
|---|---|
| `superadmin` | Full platform access, all customers |
| `customer_admin` | Full access within their customer |
| `org_admin` | Scoped to specific organisations (via OrganisationMembership) |
| `viewer` | Read-only within their customer |

## Billing flow

1. Product is enabled for an organisation → `Subscription` created (status: `trialing`)
2. Customer sets up payment mandate via Mollie first-payment flow
3. Celery beat runs on 1st of each month → `snapshot_usage` task captures unit count
4. Invoice is created → `charge_invoice` task triggers Mollie recurring payment
5. Mollie webhook fires → invoice marked `paid` or subscription set to `past_due`

### Usage units per product

| Product | Billed unit |
|---|---|
| Recast Application Workspace | Per organisation member |
| Windows 365 | Per provisioned Cloud PC |
| Microsoft Intune | Per organisation (flat) |

## Microsoft Graph API setup

1. Register an App Registration in Azure Entra ID
2. Grant application permissions: `CloudPC.Read.All`, `DeviceManagementConfiguration.ReadWrite.All`
3. Set `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` in `.env`

Each organisation stores its own `azure_tenant_id` — the app uses client credentials to call Graph on behalf of each tenant.

## Azure deployment

```bash
# Build and push Docker image to Azure Container Registry
az acr build --registry <acr-name> --image dashboard:latest .

# Deploy to App Service (assumes App Service Plan exists)
az webapp create --resource-group <rg> --plan <plan> --name <app-name> \
  --deployment-container-image-name <acr-name>.azurecr.io/dashboard:latest
```

Set all `.env` values as App Service environment variables, using Azure Key Vault references for secrets.
