import os
import logging
import argparse
import json

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False

# Setup logging
logging.basicConfig(
    level=logging.INFO,  # Change this line to set the logging level to INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def load_azure_credentials(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        resource_id = data.get('id', '')
        resource_parts = resource_id.split('/')
        return {
            'subscription_id': data.get('subscription_id') or (resource_parts[2] if len(resource_parts) > 2 else None),
            'resource_group': data.get('resource_group') or (resource_parts[4] if len(resource_parts) > 4 else None),
            'managed_identity_client_id': data.get('managed_identity_client_id') or data.get('properties', {}).get('clientId'),
        }

def load_gcp_credentials(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def get_azure_settings():
    settings = {
        'subscription_id': os.getenv('AZURE_SUBSCRIPTION_ID'),
        'resource_group': os.getenv('AZURE_RESOURCE_GROUP'),
        'managed_identity_client_id': os.getenv('AZURE_MANAGED_IDENTITY_CLIENT_ID'),
    }
    credentials_file = os.getenv('AZURE_CREDENTIALS_FILE_PATH')
    if credentials_file:
        settings.update({key: value for key, value in load_azure_credentials(credentials_file).items() if value})
    return settings

def get_gcp_settings():
    settings = {
        'project_id': os.getenv('GCP_PROJECT_ID'),
        'service_account_key_path': os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
    }
    credentials_file = os.getenv('GCP_CREDENTIALS_FILE_PATH')
    if credentials_file:
        settings.update(load_gcp_credentials(credentials_file))
    return settings

def run_azure_cleanup(cleanup_types, hours, disk_hours, azure_credentials):
    from azu.main import AzureCleanupOrchestrator

    subscription_id = azure_credentials['subscription_id']
    resource_group = azure_credentials['resource_group']
    managed_identity_client_id = azure_credentials['managed_identity_client_id']

    if not subscription_id:
        raise ValueError("AZURE_SUBSCRIPTION_ID is required in the credentials file")
    
    logger.info("Starting Azure cleanup...")
    orchestrator = AzureCleanupOrchestrator(
        subscription_id=subscription_id,
        resource_group=resource_group,
        managed_identity_client_id=managed_identity_client_id,
        hours=hours,
        disk_hours=disk_hours
    )
    
    success = orchestrator.run_all_cleanups(cleanup_types=cleanup_types)
    
    if success:
        logger.info("Azure cleanup completed successfully")
    else:
        logger.warning("Azure cleanup completed with some errors")

def run_gcp_cleanup(cleanup_types, hours, disk_hours):
    from gcp.main import GCPCleanupOrchestrator

    gcp_credentials = get_gcp_settings()
    project_id = gcp_credentials.get('project_id')
    service_account_key_path = gcp_credentials.get('service_account_key_path')

    if service_account_key_path:
        os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', service_account_key_path)
    
    if not project_id:
        raise ValueError("GCP_PROJECT_ID is required in the credentials file")
    
    logger.info("Starting GCP cleanup...")
    orchestrator = GCPCleanupOrchestrator(
        project_id=project_id,
        service_account_key_path=service_account_key_path,
        hours=hours,
        disk_hours=disk_hours
    )
    
    success = orchestrator.run_all_cleanups(cleanup_types=cleanup_types)
    
    if success:
        logger.info("GCP cleanup completed successfully")
    else:
        logger.warning("GCP cleanup completed with some errors")

def parse_arguments():
    parser = argparse.ArgumentParser(description="Cloud cleanup script")
    parser.add_argument('--cloud-providers', type=str, help="Comma-separated list of cloud providers (e.g., azure,gcp)")
    parser.add_argument('--cleanup-types', type=str, help="Comma-separated list of cleanup types (e.g., vm,disk)")
    parser.add_argument('--hours', type=int, default=4, help="Hours threshold for VM, IP, NIC, NEG cleanup")
    parser.add_argument('--disk-hours', type=int, default=4, help="Hours threshold for Disk cleanup")
    parser.add_argument('--execute', action='store_true', help="Actually delete resources; without this flag the command only prints the plan")
    return parser.parse_args()

def main():
    # Load environment variables
    load_dotenv()
    
    args = parse_arguments()
    cloud_providers = args.cloud_providers.split(',') if args.cloud_providers else None
    cleanup_types = args.cleanup_types.split(',') if args.cleanup_types else None
    hours = args.hours
    disk_hours = args.disk_hours

    if hours <= 0 or disk_hours <= 0:
        raise ValueError("--hours and --disk-hours must be greater than zero")

    if not args.execute:
        logger.info("Dry-run mode: no cloud credentials were loaded and no resources will be changed.")
        logger.info("Providers: %s | Cleanup types: %s | VM threshold: %sh | Disk threshold: %sh", cloud_providers or 'azure,gcp', cleanup_types or 'all', hours, disk_hours)
        logger.info("Pass --execute after configuring cloud credentials to perform cleanup.")
        return
    
    logger.info("Starting the cleanup script...")
    logger.info(f"Cloud providers: {cloud_providers}, Cleanup types: {cleanup_types}, Hours: {hours}, Disk hours: {disk_hours}")
    
    try:
        if cloud_providers is None or 'azure' in cloud_providers:
            logger.info("Running Azure cleanup")
            azure_credentials = get_azure_settings()
            run_azure_cleanup(cleanup_types, hours, disk_hours, azure_credentials)
            
        if cloud_providers is None or 'gcp' in cloud_providers:
            logger.info("Running GCP cleanup")
            run_gcp_cleanup(cleanup_types, hours, disk_hours)
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise

if __name__ == "__main__":
    main()
