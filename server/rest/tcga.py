#!/usr/bin/env python
"""
Endpoints providing a simplified interface for handling TCGA datasets.
"""

from __future__ import print_function, division

import re

from girder import logger
from girder.api import access
from girder.api.describe import describeRoute, Description
from girder.api.rest import Resource, RestException, loadmodel
from girder.constants import TokenScope, AccessType
from girder.models.model_base import ValidationException
from girder.plugins.jobs.constants import JobStatus
from girder.utility import setting_utilities
from girder.utility.model_importer import ModelImporter

from ..constants import TCGACollectionSettingKey

invalid_key_re = re.compile(r'[.$]')


def import_recursive(job):
    try:
        root = job['kwargs']['root']
        token = job['kwargs']['token']

        jobModel = ModelImporter.model('job', 'jobs')
        userModel = ModelImporter.model('user')

        user = userModel.load(job['userId'], force=True)

        childModel = ModelImporter.model('cohort', 'digital_slide_archive')
        children = list(ModelImporter.model('folder').childFolders(
            root, 'collection', user=user
        ))
        count = len(children)
        progress = 0

        job = jobModel.updateJob(
            job, log='Started TCGA import\n',
            status=JobStatus.RUNNING,
            progressCurrent=progress,
            progressTotal=count
        )
        logger.info('Starting recursive TCGA import')

        for child in children:
            progress += 1
            try:
                msg = 'Importing "%s"' % child.get('name', '')
                job = jobModel.updateJob(
                    job, log=msg, progressMessage=msg + '\n',
                    progressCurrent=progress
                )
                logger.debug(msg)
                childModel.importDocument(
                    child, recurse=True, user=user, token=token, job=job
                )
                job = jobModel.load(id=job['_id'], force=True)

                # handle any request to stop execution
                if (not job or job['status'] in (
                        JobStatus.CANCELED, JobStatus.ERROR)):
                    logger.info('TCGA import job halted with')
                    return

            except ValidationException:
                logger.warning('Failed to import %s' % child.get('name', ''))

        logger.info('Starting recursive TCGA import')
        job = jobModel.updateJob(
            job, log='Finished TCGA import\n',
            status=JobStatus.SUCCESS,
            progressCurrent=count,
            progressMessage='Finished TCGA import'
        )
    except Exception as e:
        logger.exception('Importing TCGA failed with %s' % str(e))
        job = jobModel.updateJob(
            job, log='Import failed with %s\n' % str(e),
            status=JobStatus.ERROR
        )


def pagedResponse(cursor, limit, offset, sort):
    """Add paging headers to a paged query."""
    total = cursor.count()
    pages = (total - 1) // limit + 1
    index = offset // limit

    return {
        'total_count': total,
        'pos': offset,
        'limit': limit,
        'total_pages': pages,
        'current_page': index,
        'data': list(cursor)
    }


class TCGAResource(Resource):

    def __init__(self):
        super(TCGAResource, self).__init__()

        @setting_utilities.validator({
            TCGACollectionSettingKey
        })
        def validateTCGACollection(doc):
            model = self.model('collection').load(
                doc['value'], force=True
            )
            if model is None:
                raise ValidationException(
                    'Invalid collection id', 'value'
                )

        self.resourceName = 'tcga'
        self.route('GET', (), self.getCollection)
        self.route('POST', (), self.setCollection)
        self.route('POST', ('import',), self.importCollection)
        self.route('DELETE', (), self.deleteCollection)

        self.route('GET', ('cohort',), self.findCohort)
        self.route('GET', ('cohort', ':id'), self.getCohort)
        self.route('POST', ('cohort',), self.importCohort)
        self.route('DELETE', ('cohort', ':id'), self.deleteCohort)
        self.route('GET', ('cohort', ':id', 'slides'), self.cohortListSlides)
        self.route('GET', ('cohort', ':id', 'images'), self.cohortListImages)

        self.route('GET', ('case',), self.findCase)
        self.route('GET', ('case', ':id'), self.getCase)
        self.route('GET', ('case', 'label', ':label'), self.getCaseByLabel)
        self.route('POST', ('case',), self.importCase)
        self.route('DELETE', ('case', ':id'), self.deleteCase)
        self.route('GET', ('case', 'search'), self.searchCase)
        self.route('GET', ('case', ':id', 'metadata', 'tables'), self.listCaseTables)
        self.route('GET', ('case', ':id', 'metadata', ':table'), self.getCaseMetadata)
        self.route('POST', ('case', ':id', 'metadata', ':table'), self.setCaseMetadata)
        self.route('PUT', ('case', ':id', 'metadata', ':table'), self.updateCaseMetadata)
        self.route('DELETE', ('case', ':id', 'metadata', ':table'), self.deleteCaseMetadata)
        self.route('GET', ('case', ':id', 'images'), self.listCaseImages)

        self.route('GET', ('slide',), self.findSlide)
        self.route('GET', ('slide', ':id'), self.getSlide)
        self.route('POST', ('slide',), self.importSlide)
        self.route('DELETE', ('slide', ':id'), self.deleteSlide)

        self.route('GET', ('image',), self.findImage)
        self.route('GET', ('image', ':id'), self.getImage)
        self.route('POST', ('image',), self.importImage)
        self.route('DELETE', ('image', ':id'), self.deleteImage)

        self.route('GET', ('pathology',), self.findPathology)
        self.route('GET', ('pathology', ':id'), self.getPathology)
        self.route('POST', ('pathology',), self.importPathology)
        self.route('DELETE', ('pathology', ':id'), self.deletePathology)

    def getTCGACollection(self, level=AccessType.READ):
        tcga = self.model('setting').get(
            TCGACollectionSettingKey
        )
        if tcga is None:
            raise RestException(
                'TCGA collection id not initialized in settings',
                code=404
            )
        return self.model('collection').load(
            tcga, level=level, user=self.getCurrentUser()
        )

    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('Get the TCGA collection')
    )
    def getCollection(self, params):
        return self.getTCGACollection()

    @access.admin
    @describeRoute(
        Description('Set the TCGA collection')
        .param('collectionId', 'The id of the collection')
    )
    def setCollection(self, params):
        user = self.getCurrentUser()
        self.requireParams('collectionId', params)

        # this is to ensure the collection exists
        collection = self.model('collection').load(
            id=params['collectionId'], user=user,
            level=AccessType.WRITE, exc=True
        )
        return self.model('setting').set(
            TCGACollectionSettingKey,
            collection['_id']
        )

    @access.admin
    @describeRoute(
        Description('Recursively import the TCGA collection')
        .notes('This will run as a local job that will execute '
               'asynchronously.')
    )
    def importCollection(self, params):
        user = self.getCurrentUser()
        token = self.getCurrentToken()
        tcga = self.getTCGACollection(level=AccessType.WRITE)

        jobModel = self.model('job', 'jobs')
        job = jobModel.createLocalJob(
            module='girder.plugins.digital_slide_archive.rest.tcga',
            function='import_recursive',
            kwargs={'root': tcga, 'token': token},
            title='Import TCGA items',
            user=user,
            type='tcga_import_recursive',
            public=False,
            async=True
        )
        jobModel.scheduleJob(job)
        return job

    @access.admin
    @describeRoute(
        Description('Remove the TCGA collection')
    )
    def deleteCollection(self, params):
        return self.model('setting').unset(TCGACollectionSettingKey)

    # cohort endpoints
    #####################
    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('List cohorts in the TCGA dataset')
        .pagingParams(defaultSort='name')
    )
    def findCohort(self, params):
        user = self.getCurrentUser()
        tcga = self.getTCGACollection()
        limit, offset, sort = self.getPagingParameters(params, 'name')

        cursor = self.model('cohort', 'digital_slide_archive').childFolders(
            parentType='collection', parent=tcga, cursor=True,
            user=user, offset=offset, limit=limit, sort=sort
        )
        return pagedResponse(cursor, limit, offset, sort)

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='cohort', plugin='digital_slide_archive',
               level=AccessType.READ)
    @describeRoute(
        Description('Get a cohort document from an id')
        .param('id', 'The id of the cohort', paramType='path')
    )
    def getCohort(self, cohort, params):
        return cohort

    @access.admin
    @describeRoute(
        Description('Import a folder as a TCGA cohort type')
        .param('folderId', 'The id of the folder to import')
    )
    def importCohort(self, params):
        user = self.getCurrentUser()
        token = self.getCurrentToken()
        self.requireParams('folderId', params)

        folder = self.model('folder').load(
            id=params['folderId'], user=user,
            level=AccessType.WRITE, exc=True
        )

        cohort = self.model('cohort', 'digital_slide_archive').importDocument(
            folder, user=user, token=token
        )
        return cohort

    @access.admin
    @loadmodel(model='cohort', plugin='digital_slide_archive',
               level=AccessType.WRITE)
    @describeRoute(
        Description('Remove a cohort type')
        .param('id', 'The id of the cohort', paramType='path')
    )
    def deleteCohort(self, cohort, params):
        return self.model('cohort', 'digital_slide_archive').removeTCGA(
            cohort)

    @access.public
    @loadmodel(model='cohort', plugin='digital_slide_archive',
               level=AccessType.READ)
    @describeRoute(
        Description('List slides in a cohort')
        .param('id', 'The id of the cohort', paramType='path')
        .pagingParams(defaultSort='name')
    )
    def cohortListSlides(self, cohort, params):
        limit, offset, sort = self.getPagingParameters(params, 'name')
        cursor = self.model('slide', 'digital_slide_archive').find({
            'tcga.cohort': cohort['name']
        }, cursor=True, limit=limit, offset=offset, sort=sort)
        return pagedResponse(cursor, limit, offset, sort)

    @access.public
    @loadmodel(model='cohort', plugin='digital_slide_archive',
               level=AccessType.READ)
    @describeRoute(
        Description('List slide images in a cohort')
        .param('id', 'The id of the cohort', paramType='path')
        .pagingParams(defaultSort='name')
    )
    def cohortListImages(self, cohort, params):
        limit, offset, sort = self.getPagingParameters(params, 'name')
        cursor = self.model('image', 'digital_slide_archive').find({
            'tcga.cohort': cohort['name']
        }, cursor=True, limit=limit, offset=offset, sort=sort)
        return pagedResponse(cursor, limit, offset, sort)

    # Case endpoints
    #####################
    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('List cases in the TCGA dataset')
        .param('cohort', 'The id of the cohort document', required=True)
        .pagingParams(defaultSort='name')
    )
    def findCase(self, params):
        user = self.getCurrentUser()
        limit, offset, sort = self.getPagingParameters(params, 'name')
        cohort = self.model('cohort', 'digital_slide_archive').load(
            id=params['cohort'], user=user, level=AccessType.READ,
            exc=True
        )

        cursor = self.model('case', 'digital_slide_archive').childFolders(
            parentType='folder', parent=cohort, cursor=True,
            user=user, offset=offset, limit=limit, sort=sort
        )
        return pagedResponse(cursor, limit, offset, sort)

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='case', plugin='digital_slide_archive',
               level=AccessType.READ)
    @describeRoute(
        Description('Get a case document from an id')
        .param('id', 'The id of the case', paramType='path')
    )
    def getCase(self, case, params):
        return case

    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('Get a case document from a label')
        .param('label', 'The label of the case', paramType='path')
        .errorResponse('Label was invalid')
    )
    def getCaseByLabel(self, label, params):
        user = self.getCurrentUser()
        case = self.model('case', 'digital_slide_archive').findOne(
            {'tcga.label': label}, user=user
        )
        if not case:
            raise RestException(
                'TCGA case label not found'
            )
        return case

    @access.admin
    @describeRoute(
        Description('Import a folder as a TCGA case')
        .param('folderId', 'The id of the folder to import')
    )
    def importCase(self, params):
        user = self.getCurrentUser()
        token = self.getCurrentToken()
        self.requireParams('folderId', params)

        folder = self.model('folder').load(
            id=params['folderId'], user=user,
            level=AccessType.WRITE, exc=True
        )

        case = self.model('case', 'digital_slide_archive').importDocument(
            folder, user=user, token=token
        )
        return case

    @access.admin
    @loadmodel(model='case', plugin='digital_slide_archive',
               level=AccessType.WRITE)
    @describeRoute(
        Description('Remove a case document')
        .param('id', 'The id of the case', paramType='path')
    )
    def deleteCase(self, case, params):
        return self.model('case', 'digital_slide_archive').removeTCGA(case)

    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('Search for cases by clinical data')
        .param('table', 'A table to search',
               required=True)
        .param('key', 'A key that should be present',
               required=False)
        .param('value', 'The value associated with the given key',
               required=False)
        .param('substring', 'Find values containing this substring',
               required=False)
        .notes('Only one of "value" or "substring" may be provided.')
        .pagingParams(defaultSort='name')
    )
    def searchCase(self, params):
        user = self.getCurrentUser()
        limit, offset, sort = self.getPagingParameters(params, 'name')
        self.requireParams('table', params)

        table = params.get('table')
        key = params.get('key')
        value = params.get('value')
        substring = params.get('substring')

        if value and substring:
            raise RestException(
                'Cannot search by both value and substring'
            )

        if (value or substring) and not key:
            raise RestException(
                'A key must be provided to search by value'
            )

        if key and invalid_key_re.search(key):
            raise RestException(
                'Invalid key parameter'
            )

        query = {}
        if not key:
            query = {
                'tcga.meta.' + table: {
                    '$exists': True
                }
            }
        elif not value and not substring:
            query = {
                'tcga.meta.' + table + '.' + key: {
                    '$exists': True
                }
            }
        elif value:
            query = {
                'tcga.meta.' + table + '.' + key: value
            }
        else:
            query = {
                'tcga.meta.' + table + '.' + key: re.compile(re.escape(substring))
            }

        cursor = self.model('case', 'digital_slide_archive').find(
            query, user=user, offset=offset, limit=limit, sort=sort
        )
        return pagedResponse(cursor, limit, offset, sort)

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='case', plugin='digital_slide_archive',
               level=AccessType.READ)
    @describeRoute(
        Description('List tables present inside case metadata')
        .param('id', 'The id of the case', paramType='path')
    )
    def listCaseTables(self, case, params):
        return list(self.model('case', 'digital_slide_archive').getTCGAMeta(
            case).keys())

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='case', plugin='digital_slide_archive',
               level=AccessType.READ)
    @describeRoute(
        Description('Get case metadata')
        .param('id', 'The id of the case', paramType='path')
        .param('table', 'The table name to get', paramType='path')
    )
    def getCaseMetadata(self, case, table, params):
        return self.model('case', 'digital_slide_archive').getTCGAMeta(
            case).get(table)

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='case', plugin='digital_slide_archive',
               level=AccessType.WRITE)
    @describeRoute(
        Description('Create or replace case metadata')
        .param('id', 'The id of the case', paramType='path')
        .param('table', 'The table to update', paramType='path')
        .param('body', 'A JSON object containing the metadata to create',
               paramType='body')
    )
    def setCaseMetadata(self, case, table, params):
        metadata = self.getBodyJson()
        caseModel = self.model('case', 'digital_slide_archive')
        for k in metadata:
            if not len(k) or '.' in k or k[0] == '$':
                raise RestException(
                    'Invalid key name'
                )
        meta = caseModel.getTCGAMeta(case)
        meta[table] = metadata
        caseModel.save(case)
        return metadata

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='case', plugin='digital_slide_archive',
               level=AccessType.WRITE)
    @describeRoute(
        Description('Update case metadata')
        .notes('Set metadata fields to null to delete them.')
        .param('id', 'The id of the case', paramType='path')
        .param('table', 'The table to update', paramType='path')
        .param('body', 'A JSON object containing the metadata to update',
               paramType='body')
    )
    def updateCaseMetadata(self, case, table, params):
        metadata = self.getBodyJson()
        caseModel = self.model('case', 'digital_slide_archive')
        for k in metadata:
            if not len(k) or '.' in k or k[0] == '$':
                raise RestException(
                    'Invalid key name'
                )
        meta = {
            table: metadata
        }

        caseModel.updateTCGAMeta(case, meta).save(case)
        return caseModel.getTCGAMeta(case).get(table)

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='case', plugin='digital_slide_archive',
               level=AccessType.WRITE)
    @describeRoute(
        Description('Delete case metadata')
        .param('id', 'The id of the case', paramType='path')
        .param('table', 'The table to remove', paramType='path')
    )
    def deleteCaseMetadata(self, case, table, params):
        caseModel = self.model('case', 'digital_slide_archive')
        meta = caseModel.getTCGAMeta(case)
        del meta[table]
        caseModel.save(case)

    @access.public
    @loadmodel(model='case', plugin='digital_slide_archive',
               level=AccessType.READ)
    @describeRoute(
        Description('List images under a case')
        .param('id', 'The id of the case', paramType='path')
        .pagingParams(defaultSort='name')
    )
    @access.public(scope=TokenScope.DATA_READ)
    def listCaseImages(self, case, params):
        limit, offset, sort = self.getPagingParameters(params, 'name')
        cursor = self.model('image', 'digital_slide_archive').find({
            'tcga.label': case['name']
        }, cursor=True, limit=limit, offset=offset, sort=sort)
        return pagedResponse(cursor, limit, offset, sort)

    # Slide endpoints
    #####################
    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('Find slides for a case')
        .param('case', 'The id of case document', required=True)
        .pagingParams(defaultSort='name')
    )
    def findSlide(self, params):
        limit, offset, sort = self.getPagingParameters(params, 'name')
        user = self.getCurrentUser()
        case = self.model('case', 'digital_slide_archive').load(
            id=params['case'], user=user, level=AccessType.READ,
            exc=True
        )
        cursor = self.model('slide', 'digital_slide_archive').childFolders(
            parentType='folder', parent=case, user=user, cursor=True,
            offset=offset, limit=limit, sort=sort
        )
        return pagedResponse(cursor, limit, offset, sort)

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='slide', plugin='digital_slide_archive',
               level=AccessType.READ)
    @describeRoute(
        Description('Get a slide document by id')
        .param('id', 'The id of the slide', paramType='path')
    )
    def getSlide(self, slide, params):
        return slide

    @access.admin
    @describeRoute(
        Description('Import a folder as a TCGA slide')
        .param('folderId', 'The id of the folder to import')
    )
    def importSlide(self, params):
        user = self.getCurrentUser()
        token = self.getCurrentToken()
        self.requireParams('folderId', params)

        folder = self.model('folder').load(
            id=params['folderId'], user=user,
            level=AccessType.WRITE, exc=True
        )

        slide = self.model('slide', 'digital_slide_archive').importDocument(
            folder, user=user, token=token
        )
        return slide

    @access.admin
    @loadmodel(model='slide', plugin='digital_slide_archive',
               level=AccessType.WRITE)
    @describeRoute(
        Description('Remove a slide')
        .param('id', 'The id of the slide', paramType='path')
    )
    def deleteSlide(self, slide, params):
        return self.model('slide', 'digital_slide_archive').removeTCGA(slide)

    # Image endpoints
    #####################
    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('Find images')
        .param('slide', 'The id of slide document', required=False)
        .param('caseName', 'The name of the case', required=False)
        .pagingParams(defaultSort='name')
    )
    def findImage(self, params):
        limit, offset, sort = self.getPagingParameters(params, 'name')
        user = self.getCurrentUser()
        if params.get('slide'):
            slide = self.model('slide', 'digital_slide_archive').load(
                id=params['slide'], user=user, level=AccessType.READ,
                exc=True
            )
            cursor = self.model('image', 'digital_slide_archive').find(
                {'folderId': slide['_id']},
                offset=offset, limit=limit, sort=sort
            )

        elif params.get('caseName'):
            cursor = self.model('image', 'digital_slide_archive').find({
                'tcga.label': params['caseName']
            }, cursor=True, limit=limit, offset=offset, sort=sort)

        else:
            raise RestException('You must provide a slide id or case name')
        return pagedResponse(cursor, limit, offset, sort)

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='image', plugin='digital_slide_archive',
               level=AccessType.READ)
    @describeRoute(
        Description('Get an image document by id')
        .param('id', 'The id of the image', paramType='path')
    )
    def getImage(self, image, params):
        return image

    @access.admin
    @describeRoute(
        Description('Import an item as a TCGA slide image')
        .param('itemId', 'The id of the item to import')
    )
    def importImage(self, params):
        user = self.getCurrentUser()
        token = self.getCurrentToken()
        self.requireParams('itemId', params)

        item = self.model('item').load(
            id=params['itemId'], user=user,
            level=AccessType.WRITE, exc=True
        )

        image = self.model('image', 'digital_slide_archive').importDocument(
            item, user=user, token=token
        )
        return image

    @access.admin
    @loadmodel(model='image', plugin='digital_slide_archive',
               level=AccessType.WRITE)
    @describeRoute(
        Description('Remove an image')
        .param('id', 'The id of the image', paramType='path')
    )
    def deleteImage(self, image, params):
        return self.model('image', 'digital_slide_archive').removeTCGA(image)

    # Pathology endpoints
    #####################
    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('Find pathologies for a case')
        .param('case', 'The id of a case document', required=True)
        .pagingParams(defaultSort='name')
    )
    def findPathology(self, params):
        limit, offset, sort = self.getPagingParameters(params, 'name')
        user = self.getCurrentUser()
        case = self.model('case', 'digital_slide_archive').load(
            id=params['case'], user=user, level=AccessType.READ,
            exc=True
        )
        model = self.model('pathology', 'digital_slide_archive')
        cursor = model.find(
            {'tcga.case': case['tcga']['label']},
            offset=offset, limit=limit, sort=sort
        )

        # Inject file information into the returned documents
        response = pagedResponse(cursor, limit, offset, sort)
        for doc in response.get('data', []):
            files = model.childFiles(doc, limit=1)
            if files.count():
                doc['file'] = files[0]
        return response

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='pathology', plugin='digital_slide_archive',
               level=AccessType.READ)
    @describeRoute(
        Description('Get a pathology document by id')
        .param('id', 'The id of the pathology', paramType='path')
    )
    def getPathology(self, pathology, params):
        files = self.model('pathology', 'digital_slide_archive').childFiles(
            pathology, limit=1
        )
        if files.count():
            pathology['file'] = files[0]
        return pathology

    @access.admin
    @describeRoute(
        Description('Import an item as a TCGA pathology')
        .param('id', 'The id of the item to import')
        .param('recursive', 'Perform a recursive search for pathologies',
               required=False, dataType='boolean')
    )
    def importPathology(self, params):
        user = self.getCurrentUser()
        token = self.getCurrentToken()
        self.requireParams('id', params)

        item = self.model('pathology', 'digital_slide_archive').loadDocument(
            id=params['id'], user=user,
            level=AccessType.WRITE, exc=True
        )

        pathology = self.model('pathology', 'digital_slide_archive').importDocument(
            item, user=user, token=token, recurse=params.get('recursive')
        )
        return pathology

    @access.admin
    @loadmodel(model='pathology', plugin='digital_slide_archive',
               level=AccessType.WRITE)
    @describeRoute(
        Description('Remove a pathology')
        .param('id', 'The id of the pathology', paramType='path')
    )
    def deletePathology(self, pathology, params):
        return self.model('pathology', 'digital_slide_archive').removeTCGA(pathology)

    # Aperio endpoints
    #####################
    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('Find Aperio annotations for a case')
        .param('case', 'The id of a case document', required=True)
        .pagingParams(defaultSort='name')
    )
    def findAperio(self, params):
        limit, offset, sort = self.getPagingParameters(params, 'name')
        user = self.getCurrentUser()
        case = self.model('case', 'digital_slide_archive').load(
            id=params['case'], user=user, level=AccessType.READ,
            exc=True
        )
        cursor = self.model('aperio', 'digital_slide_archive').find(
            {'tcga.case': case['tcga']['label']},
            offset=offset, limit=limit, sort=sort
        )
        return pagedResponse(cursor, limit, offset, sort)

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='aperio', plugin='digital_slide_archive',
               level=AccessType.READ)
    @describeRoute(
        Description('Get an Aperio document by id')
        .param('id', 'The id of the Aperio item', paramType='path')
    )
    def getAperio(self, aperio, params):
        return aperio

    @access.admin
    @describeRoute(
        Description('Import an item as a TCGA Aperio XML item')
        .param('id', 'The id of the item or root to import')
        .param('recursive', 'Perform a recursive search for annotations',
               required=False, dataType='boolean')
    )
    def importAperio(self, params):
        user = self.getCurrentUser()
        token = self.getCurrentToken()
        self.requireParams('id', params)

        item = self.model('aperio', 'digital_slide_archive').loadDocument(
            id=params['id'], user=user,
            level=AccessType.WRITE, exc=True
        )

        aperio = self.model('aperio', 'digital_slide_archive').importDocument(
            item, user=user, token=token, recurse=params.get('recursive')
        )
        return aperio

    @access.admin
    @loadmodel(model='aperio', plugin='digital_slide_archive',
               level=AccessType.WRITE)
    @describeRoute(
        Description('Remove an Aperio XML item')
        .param('id', 'The id of the Aperio item', paramType='path')
    )
    def deleteAperio(self, aperio, params):
        return self.model('aperio', 'digital_slide_archive').removeTCGA(aperio)
