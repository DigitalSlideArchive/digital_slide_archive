# -*- coding: utf-8 -*-

import os
import pytest
import shutil
from pytest_girder.web_client import runWebClientTest

from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, setRawResponse, setResponseHeader
from girder.constants import STATIC_ROOT_DIR
from girder.models.folder import Folder
from girder.models.item import Item
from girder_large_image.models.image_item import ImageItem
from girder_large_image_annotation.models.annotation import Annotation

from . import girder_utilities as utilities
from .girder_utilities import girderWorker  # noqa


def copyDsaTest():
    src = os.path.join(os.path.dirname(__file__), 'web_client_specs', 'dsaTest.js')
    dest = os.path.join(STATIC_ROOT_DIR, 'built/plugins/digital_slide_archive', 'dsaTest.js')
    if not os.path.exists(dest) or os.path.getmtime(src) != os.path.getmtime(dest):
        shutil.copy2(src, dest)


def makeResources(server, fsAssetstore, admin, user):
    # Create an item in the admin Public folder
    adminPublicFolder = Folder().childFolders(  # noqa: B305
        admin, 'user', filters={'name': 'Public'}
    ).next()
    Item().createItem('Empty', admin, adminPublicFolder)
    # Upload a sample file
    file = utilities.uploadExternalFile(
        'data/sample_svs_image.TCGA-DU-6399-01A-01-TS1.e8eb65de-d63e-42db-'
        'af6f-14fefbbdf7bd.svs.sha512', user, fsAssetstore, name='image')
    item = Item().load(file['itemId'], force=True)
    # We have to ask to make this a large image item, because we renamed it
    # 'image' without an extension
    ImageItem().createImageItem(item, file, user=user, createJob=False)
    ImageItem().copyItem(item, user, name='copy')

    annotation = Annotation().createAnnotation(item, admin, {'name': 'admin annotation'})
    annotation = Annotation().setAccessList(annotation, {}, force=True, save=False)
    annotation = Annotation().setPublic(annotation, True, save=True)


class MockSlicerCLIWebResource(Resource):
    """
    This creates a mocked version of the ``/HistomicsTK/HistomicsTK/docker_image``
    endpoint so we can test generation of the analysis panel on the client without
    relying on girder_worker + docker.
    """

    def __init__(self):
        super(MockSlicerCLIWebResource, self).__init__()
        self.route('GET', ('docker_image',), self.dockerImage)
        self.route('GET', ('test_analysis_detection', 'xml'), self.testAnalysisXmlDetection)
        self.route('GET', ('test_analysis_features', 'xml'), self.testAnalysisXmlFeatures)
        self.route('POST', ('test_analysis_detection', 'run'), self.testAnalysisRun)
        self.route('POST', ('test_analysis_features', 'run'), self.testAnalysisRun)

    @access.public
    @describeRoute(
        Description('Mock the docker_image endpoint.')
    )
    def dockerImage(self, params):
        """
        Return a single CLI referencing mocked out /xmlspec and /run endpoints.
        """
        return {
            'dsarchive/histomicstk': {
                'latest': {
                    'ComputeNucleiFeatures': {
                        'run': 'mock_resource/test_analysis_features/run',
                        'type': 'python',
                        'xmlspec': 'mock_resource/test_analysis_features/xml'
                    },
                    'NucleiDetection': {
                        'run': 'mock_resource/test_analysis_detection/run',
                        'type': 'python',
                        'xmlspec': 'mock_resource/test_analysis_detection/xml'
                    }
                }
            }
        }

    @access.public
    @describeRoute(
        Description('Mock an analysis description route.')
    )
    def testAnalysisXmlDetection(self, params):
        """Return the nuclei detection XML spec as a test case."""
        xml_file = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 'test_analysis_detection.xml'))
        with open(xml_file) as f:
            xml = f.read()
        setResponseHeader('Content-Type', 'application/xml')
        setRawResponse()
        return xml

    @access.public
    @describeRoute(
        Description('Mock an analysis description route.')
    )
    def testAnalysisXmlFeatures(self, params):
        """Return the nuclei feature classification XML spec as a test case."""
        xml_file = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 'test_analysis_features.xml'))
        with open(xml_file) as f:
            xml = f.read()
        setResponseHeader('Content-Type', 'application/xml')
        setRawResponse()
        return xml

    @access.public
    @describeRoute(
        Description('Mock an analysis run route.')
    )
    def testAnalysisRun(self, params):
        """
        Mock out the CLI execution endpoint.

        For now, this is a no-op, but we should add some logic to generate an annotation
        output and job status events to simulate a real execution of the CLI.
        """
        return {'_id': 'jobid'}


@pytest.mark.usefixtures('girderWorker')  # noqa
@pytest.mark.plugin('digital_slide_archive')
@pytest.mark.parametrize('spec', (
    # add spec.js files here
))
def testWebClientWithWorker(boundServer, fsAssetstore, db, admin, user, spec, girderWorker):  # noqa
    copyDsaTest()
    boundServer.root.api.v1.mock_resource = MockSlicerCLIWebResource()
    makeResources(boundServer, fsAssetstore, admin, user)
    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', spec)
    runWebClientTest(boundServer, spec, 15000)


@pytest.mark.plugin('digital_slide_archive')
@pytest.mark.parametrize('spec', (
    'analysisSpec.js',
    'annotationSpec.js',
    'dsaSpec.js',
    'girderUISpec.js',
))
def testWebClient(boundServer, fsAssetstore, db, admin, user, spec):
    copyDsaTest()
    boundServer.root.api.v1.mock_resource = MockSlicerCLIWebResource()
    makeResources(boundServer, fsAssetstore, admin, user)
    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', spec)
    runWebClientTest(boundServer, spec, 15000)
