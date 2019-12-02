# -*- coding: utf-8 -*-

import hashlib
import os
import pytest
import requests
import six
import subprocess

from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.upload import Upload

from girder_worker.girder_plugin.constants import PluginSettings as WorkerSettings


_checkedPaths = {}


def deleteIfWrongHash(destpath, hashvalue):
    """
    Check if a file at a path has a particular sha512 hash.  If not, delete it.
    If the file has been checked once, don't check it again.

    :param destpath: the file path.
    :param hashvalue: the sha512 hash hexdigest.
    """
    if os.path.exists(destpath) and destpath not in _checkedPaths and hashvalue:
        sha512 = hashlib.sha512()
        with open(destpath, 'rb') as f:
            while True:
                data = f.read(1024 * 1024)
                if not data:
                    break
                sha512.update(data)
        if sha512.hexdigest() != hashvalue:
            os.unlink(destpath)
        else:
            _checkedPaths[destpath] = True


def externaldata(
        hashpath=None, hashvalue=None, destdir='externaldata', destname=None,
        sources='https://data.kitware.com/api/v1/file/hashsum/sha512/{hashvalue}/download'):
    """
    Get a file from an external data source.  If the file has already been
    downloaded, check that it has the correct hash.

    :param hashpath: an optional path to a file that contains the hash value.
        There may be white space before or after the hashvalue.
    :param hashvalue: if no hashpath is specified, use this as a hash value.
    :param destdir: the location to store downloaded files.
    :param destname: if specified, the name of the file.  If hashpath is used
        and this is None, the basename of the hashpath is used for the
        destination name.
    :param sources: a string or list of strings that are url templates.
        `{hashvalue}` is replaced with the hashvalue.
    :returns: the path to the downloaded file.
    """
    if isinstance(sources, six.string_types):
        sources = [sources]
    curDir = os.path.dirname(os.path.realpath(__file__))
    if hashpath:
        hashvalue = open(os.path.join(curDir, hashpath)).read().strip()
        if destname is None:
            destname = os.path.splitext(os.path.basename(hashpath))[0]
    realdestdir = os.path.join(os.environ.get('TOX_WORK_DIR', curDir), destdir)
    destpath = os.path.join(realdestdir, destname)
    deleteIfWrongHash(destpath, hashvalue)
    if not os.path.exists(destpath):
        for source in sources:
            try:
                request = requests.get(source.format(hashvalue=hashvalue), stream=True)
                request.raise_for_status()
                if not os.path.exists(realdestdir):
                    os.makedirs(realdestdir)
                sha512 = hashlib.sha512()
                with open(destpath, 'wb') as out:
                    for buf in request.iter_content(65536):
                        out.write(buf)
                        sha512.update(buf)
                if os.path.getsize(destpath) == int(request.headers['content-length']):
                    if hashvalue and sha512.hexdigest() != hashvalue:
                        raise Exception('Download has wrong hash value - %s' % destpath)
                    break
                raise Exception('Incomplete download (got %d of %d) of %s' % (
                    os.path.getsize(destpath), int(request.headers['content-length'], destpath)))
            except Exception:
                pass
            if os.path.exists(destpath):
                os.unlink(destpath)
    if not os.path.exists(destpath):
        raise Exception('Failed to get external data %s' % destpath)
    return destpath


def namedFolder(user, folderName='Public'):
    return Folder().find({
        'parentId': user['_id'],
        'name': folderName,
    })[0]


def uploadFile(filePath, user, assetstore, folderName='Public', name=None):
    if name is None:
        name = os.path.basename(filePath)
    folder = namedFolder(user, folderName)
    file = Upload().uploadFromFile(
        open(filePath, 'rb'), os.path.getsize(filePath), name,
        parentType='folder', parent=folder, user=user, assetstore=assetstore)
    return file


def uploadExternalFile(hashPath, user, assetstore, folderName='Public', name=None):
    imagePath = externaldata(hashPath)
    return uploadFile(imagePath, user=user, assetstore=assetstore, folderName=folderName, name=name)


def uploadTestFile(fileName, user, assetstore, folderName='Public', name=None):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, '..', '..', 'test', 'test_files', fileName)
    return uploadFile(imagePath, user=user, assetstore=assetstore, folderName=folderName, name=None)


def respStatus(resp):
    return int(resp.output_status.split()[0])


def getBody(response, text=True):
    """
    Returns the response body as a text type or binary string.

    :param response: The response object from the server.
    :param text: If true, treat the data as a text string, otherwise, treat
                 as binary.
    """
    data = '' if text else b''

    for chunk in response.body:
        if text and isinstance(chunk, six.binary_type):
            chunk = chunk.decode('utf8')
        elif not text and not isinstance(chunk, six.binary_type):
            chunk = chunk.encode('utf8')
        data += chunk

    return data


@pytest.fixture
def girderWorker(db):
    """
    Run an instance of Girder worker, connected to rabbitmq.  The rabbitmq
    service must be running.
    """
    broker = 'amqp://guest@127.0.0.1'
    Setting().set(WorkerSettings.BROKER, broker)
    Setting().set(WorkerSettings.BACKEND, broker)
    env = os.environ.copy()
    env['C_FORCE_ROOT'] = 'true'
    proc = subprocess.Popen([
        'celery', '-A', 'girder_worker.app', 'worker', '--broker', broker, '--concurrency=1'],
        close_fds=True, env=env)
    yield True
    proc.terminate()
    proc.wait()
    Setting().unset(WorkerSettings.BROKER)
    Setting().unset(WorkerSettings.BACKEND)
