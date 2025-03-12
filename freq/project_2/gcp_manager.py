import requests
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
import argparse
import sys
from getpass import getpass
import subprocess
import statistics
import concurrent.futures
import socket
import speedtest
from google.oauth2 import service_account
from google.cloud import compute_v1

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class GCPRegion:
    id: str
    name: str
    description: str
    status: str
    zones: List[str]

@dataclass
class GCPInstance:
    id: str
    name: str
    zone: str
    machine_type: str
    status: str
    internal_ips: List[str]
    external_ips: List[str]
    creation_timestamp: str

class GCPManager:
    def __init__(self, credentials_file: Optional[str] = None, project_id: Optional[str] = None):
        """Initialize the GCP Manager with credentials and project ID."""
        self.project_id = project_id
        
        # Initialize clients
        if credentials_file:
            self.credentials = service_account.Credentials.from_service_account_file(credentials_file)
            self.instance_client = compute_v1.InstancesClient(credentials=self.credentials)
            self.region_client = compute_v1.RegionsClient(credentials=self.credentials)
            self.zone_client = compute_v1.ZonesClient(credentials=self.credentials)
            self.operation_client = compute_v1.ZoneOperationsClient(credentials=self.credentials)
            self.global_operation_client = compute_v1.GlobalOperationsClient(credentials=self.credentials)
        else:
            self.instance_client = compute_v1.InstancesClient()
            self.region_client = compute_v1.RegionsClient()
            self.zone_client = compute_v1.ZonesClient()
            self.operation_client = compute_v1.ZoneOperationsClient()
            self.global_operation_client = compute_v1.GlobalOperationsClient()

    def get_regions(self) -> List[GCPRegion]:
        """Get available GCP regions."""
        request = compute_v1.ListRegionsRequest(project=self.project_id)
        regions_list = self.region_client.list(request=request)
        
        regions = []
        for region in regions_list:
            regions.append(GCPRegion(
                id=region.id,
                name=region.name,
                description=region.description,
                status=region.status,
                zones=[zone.split('/')[-1] for zone in region.zones]
            ))
        return regions

    def get_zones(self, region: Optional[str] = None) -> List[str]:
        """Get available zones, optionally filtered by region."""
        request = compute_v1.ListZonesRequest(project=self.project_id)
        zones_list = self.zone_client.list(request=request)
        
        zones = []
        for zone in zones_list:
            if region is None or region in zone.name:
                zones.append(zone.name)
        return zones

    def create_instance(
        self,
        name: str,
        zone: str,
        machine_type: str = "e2-micro",  # Default to e2-micro (2 vCPU, 1 GB memory)
        image_project: str = "debian-cloud",
        image_family: str = "debian-11",
        disk_size_gb: int = 10,
        network_tags: Optional[List[str]] = None,
        startup_script: Optional[str] = None,
        service_account: Optional[str] = None
    ) -> GCPInstance:
        """Create a new GCP instance."""
        # Get the latest image
        image_client = compute_v1.ImagesClient()
        image_response = image_client.get_from_family(
            project=image_project, family=image_family
        )
        source_disk_image = image_response.self_link

        # Configure the machine
        machine_type_full = f"zones/{zone}/machineTypes/{machine_type}"
        
        # Configure the network interface
        network_interface = compute_v1.NetworkInterface()
        network_interface.name = "global/networks/default"
        access_config = compute_v1.AccessConfig()
        access_config.name = "External NAT"
        access_config.type_ = "ONE_TO_ONE_NAT"
        access_config.network_tier = "PREMIUM"
        network_interface.access_configs = [access_config]
        
        # Configure the boot disk
        disk = compute_v1.AttachedDisk()
        disk.boot = True
        disk.auto_delete = True
        disk.initialize_params = compute_v1.AttachedDiskInitializeParams()
        disk.initialize_params.source_image = source_disk_image
        disk.initialize_params.disk_size_gb = disk_size_gb
        
        # Configure instance metadata
        metadata = compute_v1.Metadata()
        metadata_items = []
        
        if startup_script:
            metadata_items.append(
                compute_v1.Metadata.ItemsEntry(
                    key="startup-script", value=startup_script
                )
            )
        
        if metadata_items:
            metadata.items = metadata_items
        
        # Configure service account if provided
        service_accounts = None
        if service_account:
            sa = compute_v1.ServiceAccount()
            sa.email = service_account
            sa.scopes = ["https://www.googleapis.com/auth/cloud-platform"]
            service_accounts = [sa]
        
        # Create the instance
        instance = compute_v1.Instance()
        instance.name = name
        instance.machine_type = machine_type_full
        instance.disks = [disk]
        instance.network_interfaces = [network_interface]
        
        if network_tags:
            instance.tags = compute_v1.Tags()
            instance.tags.items = network_tags
        
        if metadata_items:
            instance.metadata = metadata
            
        if service_accounts:
            instance.service_accounts = service_accounts
        
        # Create the instance
        request = compute_v1.InsertInstanceRequest(
            project=self.project_id,
            zone=zone,
            instance_resource=instance
        )
        
        operation = self.instance_client.insert(request=request)
        self._wait_for_operation(operation, zone)
        
        # Get the created instance
        return self.get_instance(name, zone)

    def delete_instance(self, name: str, zone: str) -> bool:
        """Delete a GCP instance."""
        try:
            request = compute_v1.DeleteInstanceRequest(
                project=self.project_id,
                zone=zone,
                instance=name
            )
            operation = self.instance_client.delete(request=request)
            self._wait_for_operation(operation, zone)
            return True
        except Exception as e:
            logging.error(f"Failed to delete instance {name}: {str(e)}")
            return False

    def get_instance(self, name: str, zone: str) -> Optional[GCPInstance]:
        """Get information about a specific GCP instance."""
        try:
            request = compute_v1.GetInstanceRequest(
                project=self.project_id,
                zone=zone,
                instance=name
            )
            instance = self.instance_client.get(request=request)
            
            # Extract IP addresses
            internal_ips = []
            external_ips = []
            
            for nic in instance.network_interfaces:
                if nic.network_ip:
                    internal_ips.append(nic.network_ip)
                
                for config in nic.access_configs:
                    if config.nat_ip:
                        external_ips.append(config.nat_ip)
            
            return GCPInstance(
                id=instance.id,
                name=instance.name,
                zone=zone,
                machine_type=instance.machine_type.split('/')[-1],
                status=instance.status,
                internal_ips=internal_ips,
                external_ips=external_ips,
                creation_timestamp=instance.creation_timestamp
            )
        except Exception as e:
            logging.error(f"Failed to get instance {name}: {str(e)}")
            return None

    def list_instances(self, zone: Optional[str] = None) -> List[GCPInstance]:
        """List all GCP instances, optionally filtered by zone."""
        instances = []
        
        if zone:
            zones_to_check = [zone]
        else:
            zones_to_check = self.get_zones()
        
        for current_zone in zones_to_check:
            request = compute_v1.ListInstancesRequest(
                project=self.project_id,
                zone=current_zone
            )
            
            try:
                instance_list = self.instance_client.list(request=request)
                
                for instance in instance_list:
                    # Extract IP addresses
                    internal_ips = []
                    external_ips = []
                    
                    for nic in instance.network_interfaces:
                        if nic.network_ip:
                            internal_ips.append(nic.network_ip)
                        
                        for config in nic.access_configs:
                            if config.nat_ip:
                                external_ips.append(config.nat_ip)
                    
                    instances.append(GCPInstance(
                        id=instance.id,
                        name=instance.name,
                        zone=current_zone,
                        machine_type=instance.machine_type.split('/')[-1],
                        status=instance.status,
                        internal_ips=internal_ips,
                        external_ips=external_ips,
                        creation_timestamp=instance.creation_timestamp
                    ))
            except Exception as e:
                logging.error(f"Failed to list instances in zone {current_zone}: {str(e)}")
        
        return instances

    def start_instance(self, name: str, zone: str) -> bool:
        """Start a GCP instance."""
        try:
            request = compute_v1.StartInstanceRequest(
                project=self.project_id,
                zone=zone,
                instance=name
            )
            operation = self.instance_client.start(request=request)
            self._wait_for_operation(operation, zone)
            return True
        except Exception as e:
            logging.error(f"Failed to start instance {name}: {str(e)}")
            return False

    def stop_instance(self, name: str, zone: str) -> bool:
        """Stop a GCP instance."""
        try:
            request = compute_v1.StopInstanceRequest(
                project=self.project_id,
                zone=zone,
                instance=name
            )
            operation = self.instance_client.stop(request=request)
            self._wait_for_operation(operation, zone)
            return True
        except Exception as e:
            logging.error(f"Failed to stop instance {name}: {str(e)}")
            return False

    def reset_instance(self, name: str, zone: str) -> bool:
        """Reset (reboot) a GCP instance."""
        try:
            request = compute_v1.ResetInstanceRequest(
                project=self.project_id,
                zone=zone,
                instance=name
            )
            operation = self.instance_client.reset(request=request)
            self._wait_for_operation(operation, zone)
            return True
        except Exception as e:
            logging.error(f"Failed to reset instance {name}: {str(e)}")
            return False

    def _wait_for_operation(self, operation, zone):
        """Wait for a zone-specific operation to complete."""
        if operation.name:
            request = compute_v1.GetZoneOperationRequest(
                project=self.project_id,
                zone=zone,
                operation=operation.name
            )
            
            while True:
                result = self.operation_client.get(request=request)
                if result.status == compute_v1.Operation.Status.DONE:
                    if result.error:
                        raise Exception(result.error.errors)
                    return result
                time.sleep(1.0)

    def ping_instance(self, ip: str, count: int = 5) -> Optional[float]:
        """Ping an instance and return average response time."""
        try:
            # Adjust ping command for Windows compatibility
            if sys.platform == "win32":
                output = subprocess.check_output(
                    ["ping", "-n", str(count), ip],
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
            else:
                output = subprocess.check_output(
                    ["ping", "-c", str(count), ip],
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                
            if "time=" in output:
                # Extract average time from ping output
                times = [float(x.split('time=')[1].split()[0]) 
                        for x in output.splitlines() 
                        if 'time=' in x]
                return statistics.mean(times) if times else None
            return None
        except subprocess.CalledProcessError:
            return None

    def test_instance_speed(self, ip: str) -> Tuple[Optional[float], Optional[float]]:
        """Test download and upload speeds to the instance."""
        try:
            st = speedtest.Speedtest()
            st.get_best_server()
            download_speed = st.download() / 1_000_000  # Convert to Mbps
            upload_speed = st.upload() / 1_000_000      # Convert to Mbps
            return download_speed, upload_speed
        except Exception as e:
            print(f"Speed test failed for {ip}: {str(e)}")
            return None, None

    def test_all_instances(self) -> List[Dict]:
        """Test and rank all instances by connection quality."""
        instances = self.list_instances()
        results = []

        print("\nTesting connection quality for all instances...")
        for instance in instances:
            if not instance.external_ips:
                print(f"\nSkipping {instance.name} (no external IP)")
                continue
                
            ip = instance.external_ips[0]
            print(f"\nTesting {instance.name} ({ip})...")
            
            # Test ping
            ping_time = self.ping_instance(ip)
            ping_status = f"{ping_time:.1f}ms" if ping_time else "Failed"
            print(f"Ping: {ping_status}")

            # Test speed
            download_speed, upload_speed = self.test_instance_speed(ip)
            if download_speed and upload_speed:
                print(f"Download: {download_speed:.1f} Mbps")
                print(f"Upload: {upload_speed:.1f} Mbps")
            else:
                print("Speed test failed")

            results.append({
                "name": instance.name,
                "id": instance.id,
                "zone": instance.zone,
                "ip": ip,
                "ping": ping_time,
                "download_speed": download_speed,
                "upload_speed": upload_speed
            })

        # Sort results by ping time (if available) or zone
        results.sort(key=lambda x: (
            float('inf') if x['ping'] is None else x['ping'],
            x['zone']
        ))

        return results

def print_menu():
    """Print the main menu."""
    print("\n=== GCP Manager ===")
    print("1. List Regions and Zones")
    print("2. List Instances")
    print("3. Create Instance")
    print("4. Delete Instance")
    print("5. Start Instance")
    print("6. Stop Instance")
    print("7. Reset Instance")
    print("8. Get Instance Details")
    print("9. Test Instance Connections")
    print("0. Exit")
    print("===================")

def select_zone(manager: GCPManager) -> Optional[str]:
    """Interactive zone selection."""
    regions = manager.get_regions()
    print("\nAvailable Regions:")
    for i, region in enumerate(regions, 1):
        print(f"{i}. {region.name} - {region.description} ({region.status})")
    
    try:
        region_choice = int(input("\nSelect region number (0 to cancel): "))
        if region_choice == 0:
            return None
        if 1 <= region_choice <= len(regions):
            selected_region = regions[region_choice - 1]
            
            print(f"\nZones in {selected_region.name}:")
            for i, zone in enumerate(selected_region.zones, 1):
                print(f"{i}. {zone}")
            
            zone_choice = int(input("\nSelect zone number (0 to cancel): "))
            if zone_choice == 0:
                return None
            if 1 <= zone_choice <= len(selected_region.zones):
                return selected_region.zones[zone_choice - 1]
            
        print("Invalid selection!")
        return None
    except ValueError:
        print("Invalid input!")
        return None

def select_instance(manager: GCPManager) -> Optional[Tuple[str, str]]:
    """Interactive instance selection, returns (name, zone)."""
    instances = manager.list_instances()
    if not instances:
        print("No instances found!")
        return None
    
    print("\nAvailable Instances:")
    for i, instance in enumerate(instances, 1):
        print(f"{i}. {instance.name} (Zone: {instance.zone}) - Status: {instance.status}")
    
    try:
        choice = int(input("\nSelect instance number (0 to cancel): "))
        if choice == 0:
            return None
        if 1 <= choice <= len(instances):
            selected = instances[choice - 1]
            return (selected.name, selected.zone)
        print("Invalid selection!")
        return None
    except ValueError:
        print("Invalid input!")
        return None

def handle_create_instance(manager: GCPManager):
    """Handle instance creation workflow."""
    print("\n=== Create New Instance ===")
    
    # Get zone
    zone = select_zone(manager)
    if not zone:
        return
    
    # Get instance details
    name = input("Enter instance name: ")
    
    # Select machine type
    print("\nCommon Machine Types:")
    machine_types = [
        ("e2-micro", "2 vCPU, 1 GB memory"),
        ("e2-small", "2 vCPU, 2 GB memory"),
        ("e2-medium", "2 vCPU, 4 GB memory"),
        ("n1-standard-1", "1 vCPU, 3.75 GB memory"),
        ("n1-standard-2", "2 vCPU, 7.5 GB memory"),
        ("n1-standard-4", "4 vCPU, 15 GB memory")
    ]
    
    for i, (machine_type, desc) in enumerate(machine_types, 1):
        print(f"{i}. {machine_type} - {desc}")
    
    try:
        machine_choice = int(input("\nSelect machine type (0 to cancel): "))
        if machine_choice == 0:
            return
        if 1 <= machine_choice <= len(machine_types):
            machine_type = machine_types[machine_choice - 1][0]
        else:
            print("Invalid selection, using default (e2-micro)")
            machine_type = "e2-micro"
    except ValueError:
        print("Invalid input, using default (e2-micro)")
        machine_type = "e2-micro"
    
    # Select OS image
    print("\nCommon OS Images:")
    images = [
        ("debian-cloud", "debian-11"),
        ("ubuntu-os-cloud", "ubuntu-2204-lts"),
        ("centos-cloud", "centos-7"),
        ("rocky-linux-cloud", "rocky-linux-8"),
        ("windows-cloud", "windows-2022")
    ]
    
    for i, (project, family) in enumerate(images, 1):
        print(f"{i}. {family} from {project}")
    
    try:
        image_choice = int(input("\nSelect OS image (0 to cancel): "))
        if image_choice == 0:
            return
        if 1 <= image_choice <= len(images):
            image_project, image_family = images[image_choice - 1]
        else:
            print("Invalid selection, using default (Debian 11)")
            image_project, image_family = "debian-cloud", "debian-11"
    except ValueError:
        print("Invalid input, using default (Debian 11)")
        image_project, image_family = "debian-cloud", "debian-11"
    
    # Get disk size
    try:
        disk_size = int(input("\nEnter disk size in GB (default 10): ") or "10")
    except ValueError:
        print("Invalid input, using default (10 GB)")
        disk_size = 10
    
    # Optional startup script
    use_script = input("\nDo you want to provide a startup script? (y/n): ").lower() == 'y'
    startup_script = None
    if use_script:
        print("Enter startup script (end with a line containing only 'END'):")
        lines = []
        while True:
            line = input()
            if line == "END":
                break
            lines.append(line)
        startup_script = "\n".join(lines)
    
    try:
        instance = manager.create_instance(
            name=name,
            zone=zone,
            machine_type=machine_type,
            image_project=image_project,
            image_family=image_family,
            disk_size_gb=disk_size,
            startup_script=startup_script
        )
        print(f"\nInstance created successfully!")
        print(f"Name: {instance.name}")
        print(f"ID: {instance.id}")
        print(f"Zone: {instance.zone}")
        print(f"Machine Type: {instance.machine_type}")
        print(f"Internal IPs: {', '.join(instance.internal_ips)}")
        print(f"External IPs: {', '.join(instance.external_ips)}")
    except Exception as e:
        print(f"Failed to create instance: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="GCP Manager CLI")
    parser.add_argument("--credentials", help="Path to service account credentials JSON file")
    parser.add_argument("--project", help="GCP Project ID")
    args = parser.parse_args()

    # Get project ID
    project_id = args.project
    if not project_id:
        project_id = input("Enter your GCP Project ID: ")
    
    # Initialize manager
    manager = GCPManager(credentials_file=args.credentials, project_id=project_id)

    while True:
        print_menu()
        choice = input("Enter your choice (0-9): ")

        try:
            if choice == "0":
                print("Goodbye!")
                break
            elif choice == "1":
                regions = manager.get_regions()
                print("\nAvailable Regions and Zones:")
                for region in regions:
                    print(f"- {region.name} - {region.description}")
                    print(f"  Status: {region.status}")
                    print(f"  Zones: {', '.join(region.zones)}")
                    print()
            elif choice == "2":
                instances = manager.list_instances()
                print("\nYour Instances:")
                for instance in instances:
                    print(f"- {instance.name} (ID: {instance.id})")
                    print(f"  Status: {instance.status}")
                    print(f"  Zone: {instance.zone}")
                    print(f"  Machine Type: {instance.machine_type}")
                    print(f"  Internal IPs: {', '.join(instance.internal_ips)}")
                    print(f"  External IPs: {', '.join(instance.external_ips)}")
                    print(f"  Created: {instance.creation_timestamp}")
                    print()
            elif choice == "3":
                handle_create_instance(manager)
            elif choice == "4":
                instance_info = select_instance(manager)
                if instance_info:
                    name, zone = instance_info
                    confirm = input(f"Are you sure you want to delete {name}? (y/n): ")
                    if confirm.lower() == 'y':
                        if manager.delete_instance(name, zone):
                            print("Instance deleted successfully!")
                        else:
                            print("Failed to delete instance!")
            elif choice == "5":
                instance_info = select_instance(manager)
                if instance_info:
                    name, zone = instance_info
                    if manager.start_instance(name, zone):
                        print("Instance started successfully!")
                    else:
                        print("Failed to start instance!")
            elif choice == "6":
                instance_info = select_instance(manager)
                if instance_info:
                    name, zone = instance_info
                    if manager.stop_instance(name, zone):
                        print("Instance stopped successfully!")
                    else:
                        print("Failed to stop instance!")
            elif choice == "7":
                instance_info = select_instance(manager)
                if instance_info:
                    name, zone = instance_info
                    if manager.reset_instance(name, zone):
                        print("Instance reset successfully!")
                    else:
                        print("Failed to reset instance!")
            elif choice == "8":
                instance_info = select_instance(manager)
                if instance_info:
                    name, zone = instance_info
                    instance = manager.get_instance(name, zone)
                    if instance:
                        print(f"\nInstance Details:")
                        print(f"Name: {instance.name}")
                        print(f"ID: {instance.id}")
                        print(f"Status: {instance.status}")
                        print(f"Zone: {instance.zone}")
                        print(f"Machine Type: {instance.machine_type}")
                        print(f"Internal IPs: {', '.join(instance.internal_ips)}")
                        print(f"External IPs: {', '.join(instance.external_ips)}")
                        print(f"Created: {instance.creation_timestamp}")
            elif choice == "9":
                results = manager.test_all_instances()
                print("\nConnection Quality Rankings:")
                for i, result in enumerate(results, 1):
                    print(f"\n{i}. {result['name']} ({result['zone']})")
                    print(f"   IP: {result['ip']}")
                    print(f"   Ping: {result['ping']:.1f}ms" if result['ping'] else "   Ping: Failed")
                    if result['download_speed'] and result['upload_speed']:
                        print(f"   Download: {result['download_speed']:.1f} Mbps")
                        print(f"   Upload: {result['upload_speed']:.1f} Mbps")
                    else:
                        print("   Speed test failed")
            else:
                print("Invalid choice!")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 