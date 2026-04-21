"""
Tools used by billing agents.
"""

import requests
import urllib.parse
from google.auth import default
from google.auth.transport.requests import Request

def get_gcp_pricing(service_name: str, region: str = "") -> dict:
    """
    Fetches pricing information from the GCP Cloud Billing Catalog API v2beta.

    Args:
        service_name: The GCP service display name (e.g., "Compute Engine", "Cloud Storage").
        region: The GCP region for pricing (e.g., "us-central1"). If empty, the agent should ask the user.

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

    try:
        credentials, project = default()
        credentials.refresh(Request())
        access_token = credentials.token
    except Exception as e:
        return {
            "status": "error",
            "message": f"Authentication failed using Application Default Credentials: {e}"
        }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # First we need to find the service ID to build the filter string correctly.
    # The Cloud Billing catalog v2beta/skus API filter requires the format: services/{service_id}
    # It might be more complex to resolve Name to ID directly in v2beta without
    # v1 services.list, so we will try to resolve it using v1 first or 
    # we can use vertex ai search.
    # Wait, the v1 services list is unauthenticated for getting basic catalog.
    
    # We will use the v1 API just to quickly resolve the service ID first
    service_resource_name = ""
    service_display_name = ""
    service_id = ""
    
    try:
        from google.cloud import billing_v1
        client = billing_v1.CloudCatalogClient()
        matched_service = None
        for service in client.list_services():
            if service_name.lower() in service.display_name.lower():
                matched_service = service
                break
                
        if not matched_service:
            return {
                "status": "not_found",
                "message": f"Could not find a GCP service matching '{service_name}'. "
                           f"Try using the exact name like 'Compute Engine' or 'Cloud Storage'."
            }
        
        service_resource_name = matched_service.name  # returns "services/ID"
        service_display_name = matched_service.display_name
        service_id = matched_service.service_id
    except Exception as e:
        return {
             "status": "error",
             "message": f"Failed to map Service Name to Service ID: {e}"
        }


    # Step 2: Use v2beta API to list SKUs applying filter for the specific service
    filter_val = f'service="{service_resource_name}"'
    encoded_filter = urllib.parse.quote(filter_val)
    
    skus_url = f"https://cloudbilling.googleapis.com/v2beta/skus?filter={encoded_filter}"
    
    try:
        response = requests.get(skus_url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        # Fallback error mapping
        return {
            "status": "error",
            "message": f"Failed to retrieve SKUs via v2beta API: {e}"
        }

    skus_found = []
    count = 0
    max_skus = 15  # Keep it manageable
    
    all_skus = data.get('skus', [])
    
    for sku in all_skus:
        # Expected v2beta sku structure:
        # sku["name"], sku["skuId"], sku["displayName"], sku["geoTaxonomy"], sku["pricingInfo"]
        
        # Filter by region if the SKU has geoTaxonomy regions
        geo_taxonomy = sku.get("geoTaxonomy", {})
        regions = geo_taxonomy.get("regions", [])
        
        if regions:
            if not any(region.lower() in r.lower() for r in regions):
                continue

        # Extract pricing info (v2beta structure may slightly differ from v1, adjusting based on common rest patterns)
        # Assuming v2beta has similar structures or we extract what we can
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
            "description": sku.get("displayName", ""),
            "category": "N/A", # Category might not be explicitly populated the same way
            "pricing": pricing_info_list,
        })
        
        count += 1
        if count >= max_skus:
            break

    return {
        "status": "success",
        "service": service_display_name,
        "service_id": service_id,
        "region": region,
        "skus_count": len(skus_found),
        "skus": skus_found,
    }

