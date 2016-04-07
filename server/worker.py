#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

from girder.api.rest import RestException
from girder.utility.progress import ProgressContext

from girder.plugins.jobs.constants import JobStatus
from girder.utility.model_importer import ModelImporter

from .datasets import TCGAIngest, IngestException


def ingestRunner(job):
    Job = ModelImporter.model('job', 'jobs')\

    assetstore = \
        ModelImporter.model('assetstore').load(
            job['kwargs']['assetstoreId'], force=True, exc=True) \
        if job['kwargs']['assetstoreId'] \
        else None
    notify = job['kwargs']['progressEnabled']
    ingester = TCGAIngest(
        limit=job['kwargs']['limit'],
        assetstore=assetstore,
        job=job,
        notify=notify,
        localImportPath=job['kwargs']['localImportPath']
    )

    Job.updateJob(
        job,
        log='TCGA ingest started\n',
        status=JobStatus.RUNNING,
        notify=notify,
        progressMessage='TCGA ingest started',
    )
    try:
        ingester.ingest()
    except IngestException as e:
        Job.updateJob(
            job,
            log='TCGA ingest failed: %s\n' % str(e),
            status=JobStatus.ERROR,
            notify=notify,
            progressMessage='TCGA ingest failed'
        )
    else:
        Job.updateJob(
            job,
            log='TCGA ingest completed\n',
            status=JobStatus.SUCCESS,
            notify=notify,
            progressMessage='TCGA ingest completed'
        )
