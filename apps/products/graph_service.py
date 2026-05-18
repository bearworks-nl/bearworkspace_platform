"""
Microsoft Graph API service for Windows 365 and Intune product integrations.
Uses MSAL for app-only (client credentials) auth scoped to each org's tenant.
"""
import msal
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
GRAPH_BETA = "https://graph.microsoft.com/beta"


def _get_token(tenant_id):
    """Acquire an access token for the given tenant via client credentials."""
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        settings.AZURE_CLIENT_ID,
        authority=authority,
        client_credential=settings.AZURE_CLIENT_SECRET,
    )
    result = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )
    if "access_token" not in result:
        raise RuntimeError(f"MSAL token error: {result.get('error_description')}")
    return result["access_token"]


def _headers(tenant_id):
    return {
        "Authorization": f"Bearer {_get_token(tenant_id)}",
        "Content-Type": "application/json",
    }


def _get(url, tenant_id):
    r = requests.get(url, headers=_headers(tenant_id), timeout=30)
    r.raise_for_status()
    return r.json()


def _post(url, tenant_id, payload):
    r = requests.post(url, headers=_headers(tenant_id), json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def _patch(url, tenant_id, payload):
    r = requests.patch(url, headers=_headers(tenant_id), json=payload, timeout=30)
    r.raise_for_status()
    return r.json() if r.content else {}


# ── Windows 365 ───────────────────────────────────────────────────────────────

def list_cloud_pcs(tenant_id):
    """Fetch all Cloud PCs for the tenant."""
    data = _get(f"{GRAPH_BETA}/deviceManagement/virtualEndpoint/cloudPCs", tenant_id)
    return data.get("value", [])


def sync_cloud_pcs(product):
    """Sync Cloud PC records from Graph into local DB."""
    from .models import CloudPC
    from django.utils import timezone

    tenant_id = product.organisation.azure_tenant_id
    if not tenant_id:
        logger.warning("No Azure tenant ID for org %s", product.organisation)
        return 0

    remote = list_cloud_pcs(tenant_id)
    synced = 0
    for item in remote:
        CloudPC.objects.update_or_create(
            graph_id=item["id"],
            defaults={
                "config": product.windows365_config,
                "display_name": item.get("displayName", ""),
                "user_principal_name": item.get("userPrincipalName", ""),
                "status": item.get("status", "not_provisioned").lower(),
                "last_modified": item.get("lastModifiedDateTime"),
            },
        )
        synced += 1

    product.windows365_config.last_sync = timezone.now()
    product.windows365_config.save(update_fields=["last_sync"])
    return synced


# ── Intune ────────────────────────────────────────────────────────────────────

def deploy_intune_policy(policy):
    """Push a local IntunePolicy JSON to the Graph API."""
    from django.utils import timezone

    tenant_id = policy.config.product.organisation.azure_tenant_id
    payload = policy.json_payload

    if policy.graph_id:
        # Update existing
        url = f"{GRAPH_BETA}/deviceManagement/deviceConfigurations/{policy.graph_id}"
        _patch(url, tenant_id, payload)
    else:
        # Create new
        result = _post(
            f"{GRAPH_BETA}/deviceManagement/deviceConfigurations",
            tenant_id,
            payload,
        )
        policy.graph_id = result.get("id", "")

    policy.is_deployed = True
    policy.last_deployed = timezone.now()
    policy.save(update_fields=["graph_id", "is_deployed", "last_deployed"])
    logger.info("Deployed Intune policy %s to tenant %s", policy.name, tenant_id)
    return policy
