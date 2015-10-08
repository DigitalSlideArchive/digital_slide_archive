import os

from girder import events, logger
from girder.constants import AssetstoreType
from girder.models.model_base import ValidationException
from girder.utility import assetstore_utilities
from girder.utility.model_importer import ModelImporter
from girder.utility.progress import noProgress


class MetadataParseException(Exception):
    pass


def extractMetadataFromPath(path):
    """
    Given a full path to an SVS file, we extract all relevant metadata that is
    represented in the filename and its absolute path.
    """
    basename = os.path.basename(path)
    barcode, uuid, _ = basename.split('.')
    barcodeParts = barcode.split('-')

    if barcodeParts[0] != 'TCGA':
        raise MetadataParseException(
            'First barcode token should be "TCGA" (%s).' % path)

    metadata = {
        'OriginalPath': path,
        'FullBarcode': barcode,
        'TSS': barcodeParts[1],
        'Participant': barcodeParts[2],
        'Sample': barcodeParts[3][:2],
        'Vial': barcodeParts[3][2:],
        'Portion': barcodeParts[4][:2],
        'Analyte': barcodeParts[4][2:],
        'Slide': barcodeParts[5][:2],
        'SlideOrder': barcodeParts[5][2:]
    }

    metadata['SlideType'] = {
        'DX': 'Diagnostic',
        'TS': 'Frozen',
        'BS': 'Frozen',
        'MS': 'Frozen'
    }.get(metadata['Slide'], 'Unknown')

    return {
        'basename': basename,
        'folderName': '-'.join(barcodeParts[1:3]),
        'itemName': uuid,
        'itemMetadata': metadata
    }


def ingest(path, user, dest, destType, progress=noProgress, followLinks=True,
           assetstore=None):
    """
    Recursively ingest local files into the appropriate hierarchical structure
    within girder. Looks for .svs files only for now. This does not stop when
    an exception occurs; instead it logs each exception and at the end of the
    operation, returns a boolean flag of whether or not any exceptions were
    encountered. The logs will contain detailed information about exactly which
    files failed and why.

    :param path: The root path to search for .svs files.
    :type path: str
    :param user: The user performing the operation.
    :type user: user document
    :param dest: The destination object under which to create the data.
    :type dest: folder, user, or collection
    :param destType: The type of the destination (folder, user, collection).
    :type destType: str
    :param progress: Progress object. Only indeterminate progress is recorded,
        but the message is updated with each .svs file found.
    :type progress: :py:class:`girder.utility.progress.ProgressContext`
    :param followLinks: Whether symlinks should be followed when searching.
    :type followLinks: bool
    :param assetstore: If you wish to explicitly specify which assetstore these
        files belong to, pass this. Otherwise it will detect the assetstore
        automatically based on the destination or the global current assetstore.
    :type assetstore: assetstore
    :returns: Whether the operation succeeded without errors.
    :rtype: bool
    """
    assetstore = assetstore or \
        ModelImporter.model('upload').getTargetAssetstore(destType, dest)

    if assetstore['type'] != AssetstoreType.FILESYSTEM:
        raise ValidationException(
            'Assetstore "%s" is not a filesystem assetstore.' %
            assetstore['name'])
    adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)

    ok = True
    for root, _, files in os.walk(path, followlinks=followLinks):
        for name in files:
            if os.path.splitext(name)[1] == '.svs':
                progress.update(message=name)
                try:
                    ingestFile(
                        os.path.join(root, name), user, dest, destType, adapter)
                except Exception:
                    ok = False
                    logger.exception('Exception during TCGA ingest:')
    return ok


def ingestFile(path, user, dest, destType, adapter):
    """
    Ingests a single .svs file into the girder data hierarchy.

    :param path: The path to the .svs file.
    :type path: str
    :param user: The user performing the operation.
    :type user: user document
    :param dest: The destination object under which to create the data.
    :type dest: folder, user, or collection
    :param destType: The type of the destination (folder, user, collection).
    :type destType: str
    :param adapter: The assetstore adapter to import into.
    :type adapter: FilesystemAssetstoreAdapter
    """
    info = extractMetadataFromPath(path)
    itemModel = ModelImporter.model('item')

    folder = ModelImporter.model('folder').createFolder(
        parent=dest, name=info['folderName'], parentType=destType, creator=user,
        reuseExisting=True)
    item = itemModel.createItem(
        name=info['itemName'], creator=user, folder=folder, reuseExisting=True)
    item = itemModel.setMetadata(item, info['itemMetadata'])

    adapter.importFile(item=item, path=path, user=user)
