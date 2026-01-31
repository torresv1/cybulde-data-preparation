"""Diagnostic script to check GCP setup for Dask cluster creation."""

import logging
import sys
from google.cloud import compute_v1
from google.api_core import exceptions

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def check_project_exists(project_id: str) -> bool:
    """Check if the GCP project exists and is accessible."""
    try:
        from google.cloud import resourcemanager_v3
        client = resourcemanager_v3.ProjectsClient()
        project = client.get_project(name=f"projects/{project_id}")
        logger.info(f"✓ Project '{project_id}' exists and is accessible")
        logger.info(f"  State: {project.state.name}")
        return True
    except exceptions.NotFound:
        logger.error(f"✗ Project '{project_id}' not found")
        return False
    except exceptions.PermissionDenied:
        logger.error(f"✗ Permission denied accessing project '{project_id}'")
        return False
    except Exception as e:
        logger.error(f"✗ Error checking project: {e}")
        return False


def check_compute_api_enabled(project_id: str) -> bool:
    """Check if Compute Engine API is enabled."""
    try:
        client = compute_v1.ZonesClient()
        # Try to list zones - if API is disabled, this will fail
        request = compute_v1.ListZonesRequest(project=project_id, max_results=1)
        list(client.list(request=request))
        logger.info(f"✓ Compute Engine API is enabled")
        return True
    except exceptions.PermissionDenied as e:
        logger.error(f"✗ Compute Engine API permission denied: {e.message}")
        return False
    except Exception as e:
        error_msg = str(e)
        if "disabled" in error_msg.lower() or "not enabled" in error_msg.lower():
            logger.error(f"✗ Compute Engine API is not enabled")
            logger.info("  Enable it at: https://console.cloud.google.com/apis/library/compute.googleapis.com")
        else:
            logger.error(f"✗ Error checking Compute Engine API: {e}")
        return False


def check_zone_availability(project_id: str, zone: str) -> bool:
    """Check if the specified zone is available."""
    try:
        client = compute_v1.ZonesClient()
        zone_info = client.get(project=project_id, zone=zone)
        logger.info(f"✓ Zone '{zone}' is available")
        logger.info(f"  Status: {zone_info.status}")
        logger.info(f"  Region: {zone_info.region.split('/')[-1]}")
        return zone_info.status == "UP"
    except exceptions.NotFound:
        logger.error(f"✗ Zone '{zone}' not found")
        return False
    except Exception as e:
        logger.error(f"✗ Error checking zone: {e}")
        return False


def check_network_exists(project_id: str, network_name: str) -> bool:
    """Check if the network exists."""
    try:
        client = compute_v1.NetworksClient()
        network = client.get(project=project_id, network=network_name)
        logger.info(f"✓ Network '{network_name}' exists")
        logger.info(f"  Auto-create subnets: {network.auto_create_subnetworks}")
        return True
    except exceptions.NotFound:
        logger.error(f"✗ Network '{network_name}' not found")
        return False
    except Exception as e:
        logger.error(f"✗ Error checking network: {e}")
        return False


def check_machine_type_availability(project_id: str, zone: str, machine_type: str) -> bool:
    """Check if the machine type is available in the zone."""
    try:
        client = compute_v1.MachineTypesClient()
        machine = client.get(project=project_id, zone=zone, machine_type=machine_type)
        logger.info(f"✓ Machine type '{machine_type}' is available in zone '{zone}'")
        logger.info(f"  CPUs: {machine.guest_cpus}, Memory: {machine.memory_mb} MB")
        return True
    except exceptions.NotFound:
        logger.error(f"✗ Machine type '{machine_type}' not found in zone '{zone}'")
        return False
    except Exception as e:
        logger.error(f"✗ Error checking machine type: {e}")
        return False


def check_quotas(project_id: str, region: str) -> None:
    """Check relevant quotas for the region."""
    try:
        from google.cloud import compute_v1
        client = compute_v1.RegionsClient()
        region_info = client.get(project=project_id, region=region)
        
        logger.info(f"✓ Quota information for region '{region}':")
        relevant_quotas = ['CPUS', 'INSTANCES', 'IN_USE_ADDRESSES', 'DISKS_TOTAL_GB']
        
        for quota in region_info.quotas:
            if any(q in quota.metric for q in relevant_quotas):
                usage_pct = (quota.usage / quota.limit * 100) if quota.limit > 0 else 0
                status = "⚠" if usage_pct > 80 else " "
                logger.info(f"  {status} {quota.metric}: {quota.usage:.0f}/{quota.limit:.0f} ({usage_pct:.1f}%)")
                
    except Exception as e:
        logger.warning(f"⚠ Could not check quotas: {e}")


def check_service_account_permissions(project_id: str) -> None:
    """Check basic service account permissions."""
    try:
        # Try to list instances as a permission check
        client = compute_v1.InstancesClient()
        request = compute_v1.ListInstancesRequest(project=project_id, zone="us-central1-a", max_results=1)
        list(client.list(request=request))
        logger.info(f"✓ Service account has permission to list compute instances")
    except exceptions.PermissionDenied:
        logger.error(f"✗ Service account lacks 'compute.instances.list' permission")
        logger.info("  Required IAM role: 'Compute Instance Admin (v1)' or 'Compute Admin'")
    except Exception as e:
        logger.warning(f"⚠ Could not fully verify permissions: {e}")


def main() -> int:
    """Run all diagnostic checks."""
    # Configuration from your project
    project_id = "emkademy-vladimir"
    zone = "us-central1-a"
    region = zone.rsplit('-', 1)[0]  # Extract region from zone
    network = "default"
    machine_type = "n1-standard-1"
    
    logger.info("="*60)
    logger.info("GCP Dask Cluster Setup Diagnostic")
    logger.info("="*60)
    logger.info(f"Project ID: {project_id}")
    logger.info(f"Zone: {zone}")
    logger.info(f"Network: {network}")
    logger.info(f"Machine Type: {machine_type}")
    logger.info("="*60)
    
    all_passed = True
    
    # Run checks
    logger.info("\n1. Checking project access...")
    all_passed &= check_project_exists(project_id)
    
    logger.info("\n2. Checking Compute Engine API...")
    all_passed &= check_compute_api_enabled(project_id)
    
    logger.info("\n3. Checking zone availability...")
    all_passed &= check_zone_availability(project_id, zone)
    
    logger.info("\n4. Checking network...")
    all_passed &= check_network_exists(project_id, network)
    
    logger.info("\n5. Checking machine type...")
    all_passed &= check_machine_type_availability(project_id, zone, machine_type)
    
    logger.info("\n6. Checking service account permissions...")
    check_service_account_permissions(project_id)
    
    logger.info("\n7. Checking resource quotas...")
    check_quotas(project_id, region)
    
    logger.info("\n" + "="*60)
    if all_passed:
        logger.info("✓ All critical checks passed!")
        logger.info("  If you're still having issues, check:")
        logger.info("  - Service account has 'compute.instances.create' permission")
        logger.info("  - Firewall rules allow your network traffic")
        logger.info("  - Billing is enabled for the project")
    else:
        logger.error("✗ Some checks failed. Fix the issues above and try again.")
        return 1
    
    logger.info("="*60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
