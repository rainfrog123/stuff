# GCP Manager

A command-line tool for managing Google Cloud Platform (GCP) virtual machine instances.

## Features

- List available regions and zones
- Create, delete, start, stop, and reset VM instances
- View instance details
- Test connection quality (ping and speed tests) to instances
- Rank instances by connection quality

## Prerequisites

- Python 3.6 or higher
- A Google Cloud Platform account
- A GCP project with the Compute Engine API enabled
- Service account credentials with appropriate permissions (optional)

## Installation

1. Clone this repository or download the `gcp_manager.py` file
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Authentication

The GCP Manager supports two authentication methods:

1. **Service Account Credentials**: Provide a path to your service account JSON key file using the `--credentials` flag
2. **Application Default Credentials**: If no credentials are provided, the tool will use your application default credentials

To set up application default credentials, run:

```bash
gcloud auth application-default login
```

## Usage

Run the GCP Manager with:

```bash
python gcp_manager.py --project YOUR_PROJECT_ID [--credentials PATH_TO_CREDENTIALS]
```

### Command-line Arguments

- `--project`: Your GCP Project ID (required)
- `--credentials`: Path to service account credentials JSON file (optional)

### Interactive Menu

The tool provides an interactive menu with the following options:

1. **List Regions and Zones**: Display all available GCP regions and their zones
2. **List Instances**: Show all VM instances in your project
3. **Create Instance**: Create a new VM instance with customizable options
4. **Delete Instance**: Delete an existing VM instance
5. **Start Instance**: Start a stopped VM instance
6. **Stop Instance**: Stop a running VM instance
7. **Reset Instance**: Reset (reboot) a VM instance
8. **Get Instance Details**: View detailed information about a VM instance
9. **Test Instance Connections**: Test and rank connection quality to all instances
0. **Exit**: Exit the program

## Creating a VM Instance

When creating a new VM instance, you can customize:

- Instance name
- Zone
- Machine type (e.g., e2-micro, n1-standard-1)
- OS image (e.g., Debian, Ubuntu, CentOS)
- Disk size
- Startup script

## Connection Testing

The connection testing feature:

1. Pings each instance to measure latency
2. Performs a speed test to measure download and upload speeds
3. Ranks instances by connection quality (primarily by ping time)

## Example

```bash
python gcp_manager.py --project my-gcp-project
```

## Permissions Required

The service account or user credentials should have the following permissions:

- `compute.instances.list`
- `compute.instances.get`
- `compute.instances.create`
- `compute.instances.delete`
- `compute.instances.start`
- `compute.instances.stop`
- `compute.instances.reset`
- `compute.regions.list`
- `compute.zones.list`

The easiest way to ensure these permissions is to use the `Compute Admin` role.

## License

This project is open source and available under the MIT License. 