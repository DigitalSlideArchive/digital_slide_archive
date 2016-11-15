#!/usr/bin/env python
"""
Endpoints providing a simplified interface for handling TCGA datasets.
"""

from __future__ import print_function
from girder.api import access
from girder.api.describe import describeRoute, Description
from girder.api.rest import Resource  # , RestException


class TCGAResource(Resource):

    def __init__(self):
        super(TCGAResource, self).__init__()

        self.resourceName = 'tcga'
        self.route('GET', (), self.findCase)
        self.route('GET', (':case',), self.getCase)
        self.route('GET', (':case', 'slide'), self.findSlide)
        self.route('GET', (':case', 'slide', ':slide'), self.getSlide)

    @describeRoute(
        Description('List cases in the TCGA dataset')
    )
    @access.public
    def findCase(self, params):
        print(params)

    @describeRoute(
        Description('Get a case document from an id')
        .param('case', 'The id of the case', paramType='path')
    )
    @access.public
    def getCase(self, case, params):
        print(case)
        print(params)

    @describeRoute(
        Description('Find slide images for a case')
        .param('case', 'The id of the case', paramType='path')
    )
    @access.public
    def findSlide(self, case, params):
        print(case)
        print(params)

    @describeRoute(
        Description('Get a slide document for a case by id')
        .param('case', 'The id of the case', paramType='path')
        .param('slide', 'The id of the slide', paramType='path')
    )
    @access.public
    def getSlide(self, case, slide, params):
        print(case)
        print(slide)
        print(params)
