Run the following singularity commands::

    singularity run --bind ./db:/data/db docker://mongo:latest &

    singularity run --bind ./assetstore:/assetstore --bind ./girder.cfg:/etc/girder.cfg docker://dsarchive/dsa_common bash -c 'python /opt/digital_slide_archive/devops/minimal/provision.py --sample-data && girder serve' &

Note these have both been set to run in the background, which might not be desired.

This has only been minimally tested, and should be used with caution.
