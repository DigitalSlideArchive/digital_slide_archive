#!/usr/bin/env python
"""
Endpoints providing a simplified interface for handling TCGA datasets.
"""

from __future__ import print_function
from girder.api import access
from girder.api.describe import describeRoute, Description
from girder.api.rest import Resource, RestException, loadmodel
from girder.constants import TokenScope, AccessType
from girder.utility import setting_utilities
from girder.models.model_base import ValidationException
from ..constants import TCGACollectionSettingKey


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
        self.route('GET', ('cancer',), self.findCancer)
        self.route('GET', ('cancer', ':id'), self.getCancer)

        self.route('GET', ('case',), self.findCase)
        self.route('GET', ('case', ':id',), self.getCase)

        self.route('GET', ('slide',), self.findSlide)
        self.route('GET', ('slide', ':id'), self.getSlide)
        self.route('GET', ('slide', ':id', 'image'), self.getImage)

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
            tcga, level=AccessType.READ, user=self.getCurrentUser()
        )

    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('Get the TCGA collection')
    )
    def getCollection(self, params):
        return self.getTCGACollection()

    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('List cancers in the TCGA dataset')
        .pagingParams(defaultSort='name')
    )
    def findCancer(self, params):
        user = self.getCurrentUser()
        tcga = self.getTCGACollection()
        limit, offset, sort = self.getPagingParameters(params, 'name')

        return list(self.model('cancer', 'digital_slide_archive').childFolders(
            parentType='collection', parent=tcga,
            user=user, offset=offset, limit=limit, sort=sort
        ))

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='cancer', plugin='digital_slide_archive',
               level=AccessType.READ)
    @describeRoute(
        Description('Get a cancer document from an id')
        .param('id', 'The id of the cancer', paramType='path')
    )
    def getCancer(self, cancer, params):
        return cancer

    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('List cases in the TCGA dataset')
        .param('cancer', 'The id of the cancer document', required=True)
        .pagingParams(defaultSort='name')
    )
    def findCase(self, params):
        user = self.getCurrentUser()
        limit, offset, sort = self.getPagingParameters(params, 'name')
        case = self.model('cancer', 'digital_slide_archive').load(
            id=params['cancer'], user=user, level=AccessType.READ,
            exc=True
        )

        return list(self.model('case', 'digital_slide_archive').childFolders(
            parentType='folder', parent=tcga,
            user=user, offset=offset, limit=limit, sort=sort
        ))

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
        Description('Find slide images for a case')
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
        return list(self.model('slide', 'digital_slide_archive').childFolders(
            parentType='folder', parent=case, user=user,
            offset=offset, limit=limit, sort=sort
        ))

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='slide', plugin='digital_slide_archive',
               level=AccessType.READ)
    @describeRoute(
        Description('Get a slide document for a case by id')
        .param('id', 'The id of the slide', paramType='path')
    )
    def getSlide(self, slide, params):
        return slide

    @access.public(scope=TokenScope.DATA_READ)
    @loadmodel(model='slide', plugin='digital_slide_archive',
               level=AccessType.READ)
    @describeRoute(
        Description('Get the image item from a slide')
        .param('id', 'The id of the slide', paramType='path')
    )
    def getImage(self, slide, params):
        slideModel = self.model('slide', 'digital_slide_archive')
        return slideModel.getImage(slide)

    @access.user(scope=TokenScope.DATA_WRITE)
    @describeRoute(
        Description('Import an image into the TCGA collection')
        .param('itemId', 'The ID of the source item')
    )
    def importImage(self, params):
        self.getTCGACollection(AccessType.WRITE)
        user = self.getCurrentUser()
        self.requireParams(('itemId',), params)

        item = self.model('item').load(
            id=params['itemId'], user=user,
            level=AccessType.WRITE, exc=True
        )

        self.model('image', 'digital_slide_archive').importImage(
            item, user
        )
        return item

    @access.user(scope=TokenScope.DATA_WRITE)
    @describeRoute(
        Description('Import a pathology report into the TCGA collection')
        .param('itemId', 'The ID of the source item')
    )
    def importPathology(self, params):
        self.getTCGACollection(AccessType.WRITE)
        user = self.getCurrentUser()
        self.requireParams(('itemId',), params)

        item = self.model('item').load(
            id=params['itemId'], user=user,
            level=AccessType.WRITE, exc=True
        )

        self.model('pathology', 'digital_slide_archive').importPathology(
            item, user
        )
        return item
