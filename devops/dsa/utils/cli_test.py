#!/usr/bin/env python

import argparse
import getpass
import random
import sys
import tempfile
import time

import girder_client


def get_girder_client(opts):
    """
    Log in to Girder and return a reference to the client.

    :param opts: options that include the username, password, and girder api
        url.
    :returns: the girder client.
    """
    token = opts.get('token')
    username = opts.get('username')
    password = opts.get('password')
    if not username and not token:
        username = input('Admin login: ')
    if not password and not token:
        password = getpass.getpass('Password for %s: ' % (
            username if username else 'default admin user'))
    client = girder_client.GirderClient(apiUrl=opts['apiurl'])
    if token:
        client.setToken(token)
    else:
        client.authenticate(username, password)
    return client


def get_test_data(client, opts):  # noqa
    """
    Make sure we have a test collection with a folder with test data.

    :param client: girder client.
    :param opts: command line options.
    """
    collName = 'HistomicsTK Tests'
    try:
        collection = client.resourceLookup('/collection/' + collName)
    except Exception:
        collection = None
    if not collection:
        collection = client.createCollection(collName, public=True)
    folderName = 'Images'
    try:
        folder = client.resourceLookup('/collection/%s/%s' % (collName, folderName))
    except Exception:
        folder = None
    if not folder:
        folder = client.createFolder(collection['_id'], folderName, parentType='collection')
    remote = girder_client.GirderClient(apiUrl='https://data.kitware.com/api/v1')
    remoteFolder = remote.resourceLookup('/collection/HistomicsTK/Deployment test images')
    for item in remote.listItem(remoteFolder['_id']):
        localPath = '/collection/%s/%s/%s' % (collName, folderName, item['name'])
        try:
            localItem = client.resourceLookup(localPath)
        except Exception:
            localItem = None
        if localItem:
            if opts.get('test') == 'local':
                continue
            client.delete('item/%s' % localItem['_id'])
        localItem = client.createItem(folder['_id'], item['name'])
        for remoteFile in remote.listFile(item['_id']):
            with tempfile.NamedTemporaryFile() as tf:
                fileName = tf.name
                tf.close()
                sys.stdout.write('Downloading %s' % remoteFile['name'])
                sys.stdout.flush()
                remote.downloadFile(remoteFile['_id'], fileName)
                sys.stdout.write(' .')
                sys.stdout.flush()
                client.uploadFileToItem(
                    localItem['_id'], fileName, filename=remoteFile['name'],
                    mimeType=remoteFile['mimeType'])
                sys.stdout.write('.\n')
                sys.stdout.flush()
    for item in list(client.listItem(folder['_id'])):
        if '.anot' in item['name']:
            sys.stdout.write('Deleting %s\n' % item['name'])
            sys.stdout.flush()
            client.delete('item/%s' % item['_id'])
            continue
        if 'largeImage' not in item:
            sys.stdout.write('Making large_item %s ' % item['name'])
            sys.stdout.flush()
            job = client.post('item/%s/tiles' % item['_id'])
            if job is not None:
                job, peak_memory = wait_for_job(client, job)
            else:
                print('done')
    return folder


def install_cli(client, imageName):
    """
    Make sure the specified CLI is installed.

    :param client: girder client.
    :param imageName: name of the CLI docker image
    """
    client.put('slicer_cli_web/docker_image', data={'name': '["%s"]' % imageName})
    job = client.get('job/all', parameters={
        'sort': 'created', 'sortdir': -1,
        'types': '["slicer_cli_web_job"]',
        'limit': 1})[0]
    sys.stdout.write('Adding %s ' % imageName)
    wait_for_job(client, job)


def get_memory_use(client):
    """
    Get the memory use as reported by the system.

    :return: the system/check virtualMemory['used'] information.
    """
    info = client.get('system/check?mode=quick')
    return info['virtualMemory']['used']


def test_cli(client, folder, opts):
    """
    Run the CLI on an image and make sure we get an annotation out of it.

    :param client: girder client.
    :param folder: the parent folder of the test images.
    :param opts: command line options.
    """
    testItem = None
    if not opts.get('testid'):
        for item in client.listItem(folder['_id']):
            if item['name'].startswith('TCGA-02'):
                testItem = item
                break
    else:
        testItem = {'_id': opts.get('testid')}
    localFile = next(client.listFile(testItem['_id']))
    path = 'slicer_cli_web/%s/NucleiDetection/run' % (
        opts['cli'].replace('/', '_').replace(':', '_'), )
    sys.stdout.write('Running %s ' % opts['cli'])
    sys.stdout.flush()
    anList = client.get('annotation', parameters={
        'itemId': testItem['_id'], 'sort': '_id', 'sortdir': -1, 'limit': 1})
    lastOldAnnotId = None
    if len(anList):
        lastOldAnnotId = anList[0]['_id']
    memory_use = get_memory_use(client)
    starttime = time.time()
    region = '[15000,15000,1000,1000]'
    if opts.get('randomregion'):
        metadata = client.get('item/%s/tiles' % testItem['_id'])
        w = metadata['sizeX']
        h = metadata['sizeY']
        rw = random.randint(500, 5000)
        rh = random.randint(500, 5000)
        region = '[%d,%d,%d,%d]' % (random.randint(0, w - rw), random.randint(0, h - rh), rw, rh)
    if opts.get('noregion'):
        region = '[-1,-1,-1,-1]'
    data = {
        'inputImageFile': localFile['_id'],
        'outputNucleiAnnotationFile_folder': folder['_id'],
        'outputNucleiAnnotationFile': 'cli_test.anot',
        'analysis_roi': region,
        'foreground_threshold': '60',
        'min_fgnd_frac': '0.05',

        'analysis_tile_size': '4096',
        'nuclei_annotation_format': 'bbox',
        'max_radius': '30',
        'min_radius': '20',
    }
    if opts.get('testarg') and len(opts.get('testarg')):
        testarg = {val.split('=', 1)[0]: val.split('=', 1)[1] for val in opts['testarg']}
        data.update(testarg)
    if opts.get('verbose', 0) >= 1:
        sys.stdout.write('%r\n' % data)
    job = client.post(path, data=data)
    job, peak_memory = wait_for_job(client, job)
    runtime = time.time() - starttime
    # Wait for the annotation to be processed after the job finishes.
    maxWait = time.time() + 60
    annot = None
    while not annot and time.time() < maxWait:
        anList = client.get('annotation', parameters={
            'itemId': testItem['_id'], 'sort': '_id', 'sortdir': -1, 'limit': 1})
        if len(anList) and anList[0]['_id'] != lastOldAnnotId:
            annot = client.get('annotation/%s' % anList[0]['_id'])
            break
        time.sleep(1)
    sys.stdout.write('Total time: %5.3f, Max memory delta: %d bytes, Elements: %d\n' % (
        runtime, peak_memory - memory_use, len(annot['annotation']['elements'])))
    sys.stdout.flush()
    if len(annot['annotation']['elements']) < 100:
        raise Exception('Got less than 100 annotation elements (%d) from annotation %s' % (
            len(annot['annotation']['elements']), anList[0]['_id']))


def test_tiles(client, folder, opts):
    """
    Make sure we have a test collection with a folder with test data.

    :param client: girder client.
    :param folder: the parent folder of the test images.
    :param opts: command line options.
    """
    for item in client.listItem(folder['_id']):
        if 'largeImage' not in item:
            raise Exception('No large image in item')
        result = client.get('item/%s/tiles/region' % item['_id'], parameters={
            'left': 100, 'top': 150, 'right': 400, 'bottom': 450,
            'encoding': 'PNG',
        }, jsonResp=False)
        region = result.content
        if region[1:4] != b'PNG' or len(region) < 6000:
            raise Exception('Region did not give expected results')


def wait_for_job(client, job):
    """
    Wait for a job to complete.

    :param client: the girder client.
    :param job: a girder job.
    :return: the updated girder job.
    """
    peak_memory_use = get_memory_use(client)
    lastdot = 0
    jobId = job['_id']
    while job['status'] not in (3, 4, 5):
        if time.time() - lastdot >= 3:
            sys.stdout.write('.')
            sys.stdout.flush()
            lastdot = time.time()
        time.sleep(0.25)
        peak_memory_use = max(peak_memory_use, get_memory_use(client))
        job = client.get('job/%s' % jobId)
    if job['status'] == 3:
        print(' ready')
    else:
        print(' failed')
    return job, peak_memory_use


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Download test data for HistomicsTK, and test that basic functions work.')
    parser.add_argument(
        'cli',
        help='A cli docker image name.  This is pulled and used in tests.')
    parser.add_argument(
        '--apiurl', '--api', '--url', '-a',
        default='http://127.0.0.1:8080/api/v1', help='The Girder api url.')
    parser.add_argument(
        '--password', '--pass', '--passwd', '--pw',
        help='The Girder admin password.  If not specified, a prompt is given.')
    parser.add_argument(
        '--username', '--user',
        help='The Girder admin username.  If not specified, a prompt is given.')
    parser.add_argument(
        '--token',
        help='A Girder admin authentication token.  If specified, username '
        'and password are ignored')
    parser.add_argument(
        '--no-cli', '--nocli', action='store_true', dest='nocli',
        help='Do not pull and upload the cli; assume it is already present.')
    parser.add_argument(
        '--no-region', '--noregion', '--whole', action='store_true',
        dest='noregion',
        help='Run the cli against the whole image (this is slow).')
    parser.add_argument(
        '--random-region', '--randomregion', '--random', action='store_true',
        dest='randomregion',
        help='Run the cli against a random region on the image (this may be slow).')
    parser.add_argument(
        '--test', action='store_true', default=False,
        help='Download test data and check that basic functions work.')
    parser.add_argument(
        '--test-local', '--local-test', '--local', action='store_const',
        dest='test', const='local',
        help='Use local test data and check that basic functions work.  If '
        'local data is not present, it is downloaded.')
    parser.add_argument(
        '--no-test', action='store_false', dest='test',
        help='Do not download test data and do not run checks.')
    parser.add_argument(
        '--test-id', dest='testid', help='The ID of the item to test.')
    parser.add_argument(
        '--test-arg', '--arg', '--testarg', dest='testarg', action='append',
        help='Test arguments.  These should be of the form <key>=<value>.')
    parser.add_argument(
        '--only-data', '--data', action='store_const', dest='test',
        const='data',
        help='Download test data, but do not run CLI.')
    parser.add_argument('--verbose', '-v', action='count', default=0)

    args = parser.parse_args()
    if args.verbose >= 2:
        print('Parsed arguments: %r' % args)
    client = get_girder_client(vars(args))
    if not args.nocli:
        install_cli(client, args.cli)
    if args.test:
        folder = get_test_data(client, vars(args))
        test_tiles(client, folder, vars(args))
        if args.test != 'data':
            test_cli(client, folder, vars(args))
