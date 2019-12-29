# compute_manager: CLI, manages GCP Compute instances

Playing around with GCP, this tool issues management commands for instances using the information provided in `configs/`.

## getting started

For auth: uses credentials configured in [gcloud init, so setup gcloud first](https://cloud.google.com/sdk/docs/initializing).

```
virtualenv <name_a_virtualenv_for_this_tool>
. <virtualenv_name>/bin/activate
pip install --editable .
compute_manager --help
```

## usage

For a new instance, create a new yaml file at `configs/<new_instance_name>/config.yml`. Define these properties:
* `instance_project`
* `instance_family`
* `machine_type`

Then issue `compute_manager create <new_instance_name> --project <YOUR_GCP_PROJECT_ID> --zone <YOUR_GCP_ZONE>`. You should have a shiny new instance booting in GCP Compute.

(If you don't want to provide `--project` and `--zone`, put them in `/prod.env`. The tool picks up from this envfile as defaults. Following commands will assume this was done.)

You can start with a yaml file already provided with `compute_manager create ubuntu-instance-1`.

When you're done, you can delete your instance with `compute_manager delete <instance_name>`s

## supports

### GCP Compute Engine: Instances
* `create`
* `delete`

### GCP Compute Engine: Instance groups

`<WIP>`
