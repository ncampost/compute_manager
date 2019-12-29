import logging
import time

import click
from environs import Env
import googleapiclient.discovery
import yaml

log = logging.getLogger('compute_manager')

_ENVFILE_NAME = 'prod.env'

_GLOBAL_ENV = Env()

# raises errors if not found in root dir
_GLOBAL_ENV.read_env(_ENVFILE_NAME, recurse=False)

# raises errors if not defined
_GCP_PROJECT_ENVVAR = _GLOBAL_ENV.str('GCP_PROJECT')
_GCP_ZONE_ENVVAR = _GLOBAL_ENV.str('GCP_ZONE')


class ComputeResource():
    '''
    Unit of a Google Compute Engine instance
    '''
    def __init__(self, instance_name, project, zone):
        '''
        Opens the config.yml file pointed to by `instance_name` and populate attributes with config.
        '''
        try:
            with open(f'configs/{instance_name}/config.yml', 'r') as stream:
                info = yaml.safe_load(stream)

        except FileNotFoundError:
            log.error(f'Could not find config at path `configs/{instance_name}/config.yml`')
            raise

        self.instance_family = info['instance_family']
        self.instance_project = info['instance_project']
        self.machine_type = info['machine_type']
        self.instance_name = instance_name
        self.project = project
        self.zone = zone

    def __repr__(self):
        return f'ComputeResource<{self.instance_name} {self.instance_family} {self.instance_project}>'

    def create(self, gcp_compute_client):
        '''
        Create the instance.
        '''
        image_response = gcp_compute_client.images().getFromFamily(
            project=self.instance_project,
            family=self.instance_family).execute()

        source_disk_image = image_response['selfLink']

        machine_type_url = f'zones/{self.zone}/machineTypes/{self.machine_type}'

        config = {
            'name': self.instance_name,
            'machineType': machine_type_url,
            'disks': [
                {
                    'boot': True,
                    'autoDelete': True,
                    'initializeParams': {
                        'sourceImage': source_disk_image,
                    }
                }
            ],
            # Specify a network interface with NAT to access the public
            # internet.
            'networkInterfaces': [{
                'network': 'global/networks/default',
                'accessConfigs': [
                    {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
                ]
            }],
            # Allow the instance to access cloud storage and logging.
            'serviceAccounts': [{
                'email': 'default',
                'scopes': [
                    'https://www.googleapis.com/auth/devstorage.read_write',
                    'https://www.googleapis.com/auth/logging.write'
                ]
            }],
        }

        return gcp_compute_client.instances().insert(
            project=self.project,
            zone=self.zone,
            body=config).execute()

    def delete(self, gcp_compute_client):
        '''
        Delete the instance.
        '''
        return gcp_compute_client.instances().delete(
            project=self.project,
            zone=self.zone,
            instance=self.instance_name).execute()


def init_logging(logger):
    logging.basicConfig()
    logger.setLevel(logging.DEBUG)


def init_gcp_compute_client():
    # cache_discovery=False prevents "ModuleNotFoundError: No module named google.appengine" errors from being thrown.
    # I don't really understand this.
    # https://stackoverflow.com/questions/55561354
    return googleapiclient.discovery.build('compute', 'v1', cache_discovery=False)


@click.group()
def compute_manager():
    init_logging(log)


@compute_manager.command(help='Create the instance referred to by `instance_name`.')
@click.argument('instance_name')
@click.option('--project', default=_GCP_PROJECT_ENVVAR, help='GCP Project ID')
@click.option('--zone', default=_GCP_ZONE_ENVVAR, help='GCP Zone')
def create(instance_name, project, zone):
    '''
    Create the instance.

    Positional arguments:
        'instance_name' (string): Name of the Compute Engine instance

    All named arguments, if not provided, default to whatever is defined in `prod.env` in the root dir with a
    'GCP_' prefix. Eg, to change the default of `--project`, modify GCP_PROJECT in `prod.env`.
    Named arguments:
        'project' (string): GCP Project ID
        'zone' (string): GCP Zone
    '''
    compute_resource = ComputeResource(instance_name, project, zone)

    log.info(f'Issuing create command for instance `{instance_name}` in zone {zone} and project {project}...')
    gcp_compute_client = init_gcp_compute_client()

    create_operation = compute_resource.create(gcp_compute_client)

    # Block until operation completes.
    wait_for_operation(gcp_compute_client, project, zone, create_operation['name'])

    log.info('Instance created successfully!')


@compute_manager.command(help='Delete the instance referred to by `instance_name`.')
@click.argument('instance_name')
@click.option('--project', default=_GCP_PROJECT_ENVVAR, help='GCP Project ID')
@click.option('--zone', default=_GCP_ZONE_ENVVAR, help='GCP Zone')
def delete(instance_name, project, zone):
    '''
    Delete the instance.

    Positional arguments:
        'instance_name' (string): Name of the Compute Engine instance

    All named arguments, if not provided, default to whatever is defined in `prod.env` in the root dir with a
    'GCP_' prefix. Eg, to change the default of `--project`, modify GCP_PROJECT in `prod.env`.
    Named arguments:
        'project' (string): GCP Project ID
        'zone' (string): GCP Zone
    '''
    compute_resource = ComputeResource(instance_name, project, zone)

    log.info(f'Issuing delete command for instance `{instance_name}` in zone {zone} and project {project}...')
    gcp_compute_client = init_gcp_compute_client()

    delete_operation = compute_resource.delete(gcp_compute_client)

    # Block until operation completes.
    wait_for_operation(gcp_compute_client, project, zone, delete_operation['name'])

    log.info('Instance deleted successfully!')


def wait_for_operation(gcp_compute_client, project, zone, operation):
    '''
    Polls the API until operation status is DONE.
    '''
    while True:
        result = gcp_compute_client.zoneOperations().get(
            project=project,
            zone=zone,
            operation=operation).execute()

        if result['status'] == 'DONE':
            print("done.")
            if 'error' in result:
                raise Exception(result['error'])
            return result

        time.sleep(1)
