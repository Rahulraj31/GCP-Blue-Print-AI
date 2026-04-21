"""
Tools used by billing agents.
"""

import requests
import urllib.parse
import difflib
import os
from dotenv import load_dotenv
from google.auth import default
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# Load environment variables (PROJECT_ID, GOOGLE_APPLICATION_CREDENTIALS, etc.)
load_dotenv()

# Common GCP Service Aliases mapping common abbreviations to display names
SERVICE_ALIASES = {
    "gce": "Compute Engine",
    "gcs": "Cloud Storage",
    "gke": "Kubernetes Engine",
    "bq": "BigQuery",
    "cloud sql": "Cloud SQL",
    "cloud run": "Cloud Run", # Cloud Run is often used for serverless
    "pubsub": "Cloud Pub/Sub",
    "spanner": "Cloud Spanner",
    "functions": "Cloud Functions",
}

def get_gcp_pricing(service_name: str, region: str = "", sku_keyword: str = "", start_index: int = 0) -> dict:
    """
    Fetches pricing information from the GCP Cloud Billing Catalog API.

    Args:
        service_name: The GCP service display name (e.g., "Compute Engine", "Cloud Storage").
        region: The GCP region for pricing (e.g., "us-central1"). If empty, the agent should ask the user.
        sku_keyword: Optional keyword to filter SKUs (e.g., "E2", "vCPU", "RAM").
        start_index: Optional offset to skip the first N matches (useful for pagination if the result isn't in the top 20).

    Returns:
        A dict with service info, matching SKUs, and pricing details.
    """
    
    # If region is missing, ask the user
    if not region:
        return {
            "status": "needs_input",
            "message": f"I found the service '{service_name}', but I need a region to get accurate pricing. "
                       f"Please specify a GCP region (e.g., us-central1, europe-west1, asia-east1)."
        }

    # Short-circuit broad searches for massive services to save TPM and prevent 429s
    service_lower = service_name.lower()
    if ("compute" in service_lower or "sql" in service_lower):
        broad_terms = ["linux", "windows", "vm", "server", "database", "db"]
        if not sku_keyword or sku_keyword.lower() in broad_terms:
            return {
                "status": "needs_input",
                "message": f"The service '{service_name}' has thousands of SKUs. "
                           f"You must specify a precise machine family or tier in 'sku_keyword' (e.g., 'E2', 'N2D', 'PostgreSQL Enterprise'). "
                           f"If the user didn't specify one, STOP and ask them to clarify (e.g., 'Do you want a standard E2 machine or something compute-optimized like C3?')."
            }

    try:
        scopes = ['https://www.googleapis.com/auth/cloud-platform']
        
        # Priority: GOOGLE_APPLICATION_CREDENTIALS path if provided in .env
        sa_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        if sa_path and os.path.exists(sa_path):
            credentials = service_account.Credentials.from_service_account_file(
                sa_path, scopes=scopes
            )
        else:
            # Fallback to standard ADC (Environment variables, gcloud login, etc.)
            credentials, project = default(scopes=scopes)
            
        credentials.refresh(Request())
        access_token = credentials.token
    except Exception as e:
        return {
            "status": "error",
            "message": f"Authentication failed: {e}. Check your .env file and GOOGLE_APPLICATION_CREDENTIALS path."
        }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Step 1: Resolve Service Name to Service ID using v1 Catalog Client
    service_resource_name = ""
    service_display_name = ""
    service_id = ""
    
    try:
        from google.cloud import billing_v1
        client = billing_v1.CloudCatalogClient()
        
        # 1. Check aliases first
        lookup_name = SERVICE_ALIASES.get(service_name.lower(), service_name)
        
        services_list = list(client.list_services())
        display_names = [s.display_name for s in services_list]
        
        # 2. Try exact/substring match
        matched_service = None
        for service in services_list:
            if lookup_name.lower() in service.display_name.lower():
                matched_service = service
                break
        
        # 3. If not found, try fuzzy matching
        if not matched_service:
            close_matches = difflib.get_close_matches(lookup_name, display_names, n=1, cutoff=0.6)
            if close_matches:
                best_match = close_matches[0]
                for service in services_list:
                    if service.display_name == best_match:
                        matched_service = service
                        break

        if not matched_service:
            return {
                "status": "not_found",
                "message": f"Could not find a GCP service matching '{service_name}'. "
                           f"I tried fuzzy matching but found no close results. "
                           f"Available services samples: {', '.join(display_names[:5])}..."
            }
        
        service_resource_name = matched_service.name  # returns "services/ID"
        service_display_name = matched_service.display_name
        service_id = matched_service.service_id
    except Exception as e:
        return {
             "status": "error",
             "message": f"Failed to map Service Name to Service ID: {e}"
        }


    # Step 2: Use v1 API which natively includes pricingInfo and geoTaxonomy in a single call.
    base_skus_url = f"https://cloudbilling.googleapis.com/v1/{service_resource_name}/skus?pageSize=500"
    
    skus_found = []
    page_token = ""
    matches_seen = 0
    
    while len(skus_found) < 20:
        skus_url = base_skus_url
        if page_token:
            import urllib.parse
            skus_url += f"&pageToken={urllib.parse.quote(page_token)}"
            
        try:
            response = requests.get(skus_url, headers=headers)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            if not skus_found:  # Return error only if we haven't found ANY SKUs yet
                return {
                    "status": "error",
                    "message": f"Failed to retrieve SKUs via v1 API: {e}"
                }
            break

        all_skus = data.get('skus', [])
        if not all_skus:
            break
        
        for sku in all_skus:
            # v1 API uses 'description' instead of 'displayName'
            display_name = sku.get("description", "")
            
            # Filter by region
            geo_taxonomy = sku.get("geoTaxonomy", {})
            regions = geo_taxonomy.get("regions", [])
            
            if regions:
                if not any(region.lower() in r.lower() for r in regions):
                    continue

            # Optional keyword filter (Python-side)
            if sku_keyword:
                if sku_keyword.lower() not in display_name.lower():
                    continue

            # We found a match, but we need to respect the start_index offset
            matches_seen += 1
            if matches_seen <= start_index:
                continue

            # Extract pricing info
            pricing_data = sku.get('pricingInfo', [])
            pricing_info_list = []
            
            for price in pricing_data:
                pricing_expression = price.get('pricingExpression', {})
                tiered_rates = []
                for rate in pricing_expression.get('tieredRates', []):
                    unit_price = rate.get('unitPrice', {})
                    units = unit_price.get('units', '0')
                    nanos = unit_price.get('nanos', 0)
                    currency = unit_price.get('currencyCode', 'USD')
                    tiered_rates.append({
                        "start_usage": rate.get('startUsageAmount', 0),
                        "unit_price": f"{units}.{str(nanos).zfill(9)} {currency}",
                    })
                
                pricing_info_list.append({
                    "usage_unit": pricing_expression.get('usageUnit', ''),
                    "display_quantity": pricing_expression.get('displayQuantity', 0),
                    "rates": tiered_rates,
                })

            skus_found.append({
                "sku_id": sku.get("skuId", ""),
                "description": display_name,
                "category": "N/A",
                "pricing": pricing_info_list,
            })
            
            # Cap results at 20 relevant ones to avoid overloading the LLM context
            if len(skus_found) >= 20:
                break
                
        # Get next page token for the next iteration of the while loop
        page_token = data.get('nextPageToken')
        if not page_token:
            break

    if not skus_found:
        return {
            "status": "no_results",
            "message": f"No SKUs found for '{service_name}' in '{region}' matching keyword '{sku_keyword}'."
        }

    return {
        "status": "success",
        "service": service_display_name,
        "service_id": service_id,
        "region": region,
        "skus_count": len(skus_found),
        "skus": skus_found,
    }

