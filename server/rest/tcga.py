import os

from girder.api import access
from girder.api.describe import Description
from girder.api.rest import Resource, RestException
from girder.constants import AccessType
from girder.utility.progress import ProgressContext
from girder.plugins.tcga_ingest import utils


class Tcga(Resource):
    def __init__(self):
        self.resourceName = 'tcga'

        self.route('POST', ('import',), self.importData)

    @access.admin
    def importData(self, params):
        for key in list(params):
            if params[key] == '':
                params.pop(key, None)
        self.requireParams(('path', 'destType', 'destId'), params)
        progress = self.boolParam('progress', params, default=True)
        model = params['destType']
        path = params['path']
        user = self.getCurrentUser()

        if model not in ('collection', 'folder', 'user'):
            raise RestException('The destination type must be collection, '
                                'user, or folder.')

        if params.get('assetstoreId'):
            assetstore = self.model('assetstore').load(
                params['assetstoreId'], force=True, exc=True)
        else:
            assetstore = None

        dest = self.model(model).load(
            params['destId'], user=user, level=AccessType.WRITE, exc=True)

        if not os.path.isdir(path):
            raise RestException('Directory "%s" not found.' % path)

        with ProgressContext(progress, title='Importing TCGA data',
                             user=user) as p:
            if not utils.ingest(path, user=user, dest=dest, destType=model,
                                progress=p, assetstore=assetstore):
                raise Exception('An error occurred during data import. Check '
                                'the error log file for details.')
    importData.description = (
        Description('Import TCGA data into Girder recursively.')
        .notes('Only administrators may use this route.')
        .param('path', 'The root import path on the filesystem.')
        .param('destId', 'Import destination ID.')
        .param('destType', 'Import destination type.',
               enum=('folder', 'collection', 'user'))
        .param('progress', 'Whether to record progress on the operation.',
               required=False, default=True, dataType='boolean')
        .param('assetstoreId', 'Pass this to explicitly bind the imported files'
               ' to a specific filesystem assetstore. If not passed, will use '
               'the normal target assetstore for the given destination.',
               required=False))
