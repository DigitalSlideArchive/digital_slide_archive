---
layout: page
permalink: /system-overview/

# Banner Content
# =================================
title: System Overview
subtitle:
hero_image: assets/img/system-diagrams/system-diagram.svg
---

<div class="system-overview-page" markdown="1">

The Digital Slide Archive is typically either installed on a single computer or on one main computer with on or more worker machines to run image algorithms. There are additional options, such as having the database hosted in an external location, but these are uncommon.

## Single Computer Setup

![Single Computer Diagram](/digital_slide_archive/assets/img/system-diagrams/system-diagram-single-computer-setup.svg "Single Computer Diagram"){:width="75%"}

The default installation of the Digital Slide Archive is on a single computer. This is the simplest was to deploy the DSA, though image analysis tasks are limited to the available processing power a single computer.

Image and other data files, the database, and log files are all stored on the local file system. Data files can also be stored or imported from external assetstores, such as Amazon S3.

When the deploy_docker.py script is used for installation, a set of five docker containers are started to provide all of the services needed by the DSA. When an image analysis task is performed, e.g., detecting nuclei on a whole slide image using the HistomicsTK toolkit, an additional docker container is created to run the task. This container only exists as long as is necessary for the image analysis. The results are stored back to the database and file assetstore.

---

## Distributed Workers Setup

![Distributed Workers Setup](/digital_slide_archive/assets/img/system-diagrams/system-diagram-distributed-workers-setup.svg "Distributed Workers Setup Diagram"){:width="75%"}

To allow running a larger number of image analysis tasks, the Digital Slide Archive can be installed on one main computer and any number of worker machines.

Image and other data files, the database, and log files are all stored on the local file system of the main computer, just like in the single computer configuration. Of course data files can also be stored or imported from external assetstores, such as Amazon S3.

To start in this mode, some additional parameters are passed to the deploy_docker.py script. For instance, a minimal command is <mark><em>deploy_docker.py start --only girder,rabbitmq,mongodb,memcached --worker-api-url=&lt;hostname or IP of this computer as seen from second computer>/api/v1</em></mark>. One or more workers can be started on other machines with a command like <mark><em>deploy_docker.py start --only worker --rmq=&lt;hostname or IP of first computer></em></mark>. Workers can be started or stopped at any time. For instance, more workers can be added when running many tasks and then stopped when they are no longer needed. If a shared network file system is used, appropriate mount commands can be added as additional options to both the main computer and the worker commands; this can substantially reduce network traffic.

On the main computer, four docker containers are started to provide most of the services needed by the DSA. On each worker, one docker container is started initially. When an image analysis task is performed an additional docker container is created on the worker to run the task. This container only exists as long as is necessary for the image analysis. The results are stored back to the database and file assetstore.

When there are multiple workers, each worker is given tasks in turn until they are all busy. As workers finish a task, they are assigned new tasks. If a worker is stopped or loses network connectivity with a partially completed task, that task is reassigned to another available worker. The worker computers do not need to be identical; faster workers will end up processing more tasks than slower workers.
