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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class LinodeRegion:
    id: str
    label: str
    country: str
    capabilities: List[str]
    resolvers: Dict[str, List[str]]

@dataclass
class LinodeInstance:
    id: int
    label: str
    region: str
    type: str
    ipv4: List[str]
    ipv6: str
    status: str

class LinodeManager:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.linode.com/v4"
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make an API request to Linode."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {str(e)}")
            raise

    def get_regions(self) -> List[LinodeRegion]:
        """Get available Linode regions."""
        response = self._make_request("GET", "regions")
        regions = []
        for region in response.get("data", []):
            regions.append(LinodeRegion(
                id=region["id"],
                label=region["label"],
                country=region["country"],
                capabilities=region["capabilities"],
                resolvers={
                    "ipv4": str(region["resolvers"]["ipv4"]).split(","),
                    "ipv6": str(region["resolvers"]["ipv6"]).split(",")
                }
            ))
        return regions

    def create_instance(
        self,
        label: str,
        region: str,
        type_id: str = "g6-nanode-1",  # Default to Nanode 1GB
        image: str = "linode/ubuntu22.04",
        root_pass: Optional[str] = None,
        authorized_keys: Optional[List[str]] = None,
        stackscript_id: Optional[int] = None,
        stackscript_data: Optional[Dict] = None,
        backups_enabled: bool = False
    ) -> LinodeInstance:
        """Create a new Linode instance."""
        data = {
            "label": label,
            "region": region,
            "type": type_id,
            "image": image,
            "backups_enabled": backups_enabled
        }

        if root_pass:
            data["root_pass"] = root_pass
        if authorized_keys:
            data["authorized_keys"] = authorized_keys
        if stackscript_id:
            data["stackscript_id"] = stackscript_id
        if stackscript_data:
            data["stackscript_data"] = stackscript_data

        response = self._make_request("POST", "linode/instances", data)
        return LinodeInstance(
            id=response["id"],
            label=response["label"],
            region=response["region"],
            type=response["type"],
            ipv4=response["ipv4"],
            ipv6=response["ipv6"],
            status=response["status"]
        )

    def delete_instance(self, instance_id: int) -> bool:
        """Delete a Linode instance."""
        try:
            self._make_request("DELETE", f"linode/instances/{instance_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to delete instance {instance_id}: {str(e)}")
            return False

    def get_instance(self, instance_id: int) -> Optional[LinodeInstance]:
        """Get information about a specific Linode instance."""
        try:
            response = self._make_request("GET", f"linode/instances/{instance_id}")
            return LinodeInstance(
                id=response["id"],
                label=response["label"],
                region=response["region"],
                type=response["type"],
                ipv4=response["ipv4"],
                ipv6=response["ipv6"],
                status=response["status"]
            )
        except Exception as e:
            logging.error(f"Failed to get instance {instance_id}: {str(e)}")
            return None

    def list_instances(self) -> List[LinodeInstance]:
        """List all Linode instances."""
        response = self._make_request("GET", "linode/instances")
        instances = []
        for instance in response.get("data", []):
            instances.append(LinodeInstance(
                id=instance["id"],
                label=instance["label"],
                region=instance["region"],
                type=instance["type"],
                ipv4=instance["ipv4"],
                ipv6=instance["ipv6"],
                status=instance["status"]
            ))
        return instances

    def reboot_instance(self, instance_id: int) -> bool:
        """Reboot a Linode instance."""
        try:
            self._make_request("POST", f"linode/instances/{instance_id}/reboot")
            return True
        except Exception as e:
            logging.error(f"Failed to reboot instance {instance_id}: {str(e)}")
            return False

    def ping_instance(self, ip: str, count: int = 5) -> Optional[float]:
        """Ping an instance and return average response time."""
        try:
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
            ip = instance.ipv4[0]
            print(f"\nTesting {instance.label} ({ip})...")
            
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
                "label": instance.label,
                "id": instance.id,
                "region": instance.region,
                "ip": ip,
                "ping": ping_time,
                "download_speed": download_speed,
                "upload_speed": upload_speed
            })

        # Sort results by ping time (if available) or region
        results.sort(key=lambda x: (
            float('inf') if x['ping'] is None else x['ping'],
            x['region']
        ))

        return results

def print_menu():
    """Print the main menu."""
    print("\n=== Linode Manager ===")
    print("1. List Regions")
    print("2. List Instances")
    print("3. Create Instance")
    print("4. Delete Instance")
    print("5. Reboot Instance")
    print("6. Get Instance Details")
    print("7. Test Instance Connections")
    print("0. Exit")
    print("===================")

def select_region(manager: LinodeManager) -> Optional[str]:
    """Interactive region selection."""
    regions = manager.get_regions()
    print("\nAvailable Regions:")
    for i, region in enumerate(regions, 1):
        print(f"{i}. {region.label} ({region.id}) - {region.country}")
    
    try:
        choice = int(input("\nSelect region number (0 to cancel): "))
        if choice == 0:
            return None
        if 1 <= choice <= len(regions):
            return regions[choice - 1].id
        print("Invalid selection!")
        return None
    except ValueError:
        print("Invalid input!")
        return None

def select_instance(manager: LinodeManager) -> Optional[int]:
    """Interactive instance selection."""
    instances = manager.list_instances()
    if not instances:
        print("No instances found!")
        return None
    
    print("\nAvailable Instances:")
    for i, instance in enumerate(instances, 1):
        print(f"{i}. {instance.label} (ID: {instance.id}) - Status: {instance.status}")
    
    try:
        choice = int(input("\nSelect instance number (0 to cancel): "))
        if choice == 0:
            return None
        if 1 <= choice <= len(instances):
            return instances[choice - 1].id
        print("Invalid selection!")
        return None
    except ValueError:
        print("Invalid input!")
        return None

def handle_create_instance(manager: LinodeManager):
    """Handle instance creation workflow."""
    print("\n=== Create New Instance ===")
    
    # Get region
    region_id = select_region(manager)
    if not region_id:
        return
    
    # Get instance details
    label = input("Enter instance label: ")
    root_pass = getpass("Enter root password: ")
    
    try:
        instance = manager.create_instance(
            label=label,
            region=region_id,
            type_id="g6-nanode-1",
            root_pass=root_pass
        )
        print(f"\nInstance created successfully!")
        print(f"ID: {instance.id}")
        print(f"Label: {instance.label}")
        print(f"IPv4: {', '.join(instance.ipv4)}")
        print(f"IPv6: {instance.ipv6}")
    except Exception as e:
        print(f"Failed to create instance: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Linode Manager CLI")
    parser.add_argument("--token", help="Linode API token")
    args = parser.parse_args()

    # Get API token
    api_token = args.token or "085f18ba0344aa246b8202761fbb4da201c131dc93985b97b5fa6da9c4576db9"

    manager = LinodeManager(api_token)

    while True:
        print_menu()
        choice = input("Enter your choice (0-7): ")

        try:
            if choice == "0":
                print("Goodbye!")
                break
            elif choice == "1":
                regions = manager.get_regions()
                print("\nAvailable Regions:")
                for region in regions:
                    print(f"- {region.label} ({region.id}) - {region.country}")
            elif choice == "2":
                instances = manager.list_instances()
                print("\nYour Instances:")
                for instance in instances:
                    print(f"- {instance.label} (ID: {instance.id})")
                    print(f"  Status: {instance.status}")
                    print(f"  Region: {instance.region}")
                    print(f"  IPv4: {', '.join(instance.ipv4)}")
                    print(f"  IPv6: {instance.ipv6}")
                    print()
            elif choice == "3":
                handle_create_instance(manager)
            elif choice == "4":
                instance_id = select_instance(manager)
                if instance_id:
                    if manager.delete_instance(instance_id):
                        print("Instance deleted successfully!")
                    else:
                        print("Failed to delete instance!")
            elif choice == "5":
                instance_id = select_instance(manager)
                if instance_id:
                    if manager.reboot_instance(instance_id):
                        print("Instance rebooted successfully!")
                    else:
                        print("Failed to reboot instance!")
            elif choice == "6":
                instance_id = select_instance(manager)
                if instance_id:
                    instance = manager.get_instance(instance_id)
                    if instance:
                        print(f"\nInstance Details:")
                        print(f"Label: {instance.label}")
                        print(f"ID: {instance.id}")
                        print(f"Status: {instance.status}")
                        print(f"Region: {instance.region}")
                        print(f"Type: {instance.type}")
                        print(f"IPv4: {', '.join(instance.ipv4)}")
                        print(f"IPv6: {instance.ipv6}")
            elif choice == "7":
                results = manager.test_all_instances()
                print("\nConnection Quality Rankings:")
                for i, result in enumerate(results, 1):
                    print(f"\n{i}. {result['label']} ({result['region']})")
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