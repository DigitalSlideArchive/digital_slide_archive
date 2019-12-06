# -*- coding: utf-8 -*-

"""Test digital_slide_archive endpoints"""

import json
import pytest

from girder.exceptions import ValidationException
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.group import Group
from girder.models.item import Item
from girder.models.setting import Setting
from girder.models.user import User
from girder.utility import config

from digital_slide_archive.constants import PluginSettings

from . import girder_utilities as utilities


# This probably should be moved into a fixture
config.getConfig()['digital_slide_archive'] = {'restrict_downloads': True}


@pytest.mark.plugin('digital_slide_archive')
class TestDSAResourceAndItem(object):
    def makeResources(self, admin):
        self.publicFolder = utilities.namedFolder(admin, 'Public')
        self.privateFolder = utilities.namedFolder(admin, 'Private')
        # Create some resources to use in the tests
        self.collection = Collection().createCollection(
            'collection A', admin)
        self.colFolderA = Folder().createFolder(
            self.collection, 'folder A', parentType='collection',
            creator=admin)
        self.colFolderB = Folder().createFolder(
            self.collection, 'folder B', parentType='collection',
            creator=admin)
        self.colFolderC = Folder().createFolder(
            self.colFolderA, 'folder C', creator=admin)
        self.colItemA1 = Item().createItem('item A1', admin, self.colFolderA)
        self.colItemB1 = Item().createItem('item B1', admin, self.colFolderB)
        self.colItemB2 = Item().createItem('item B2', admin, self.colFolderB)
        self.colItemC1 = Item().createItem('item C1', admin, self.colFolderC)
        self.colItemC2 = Item().createItem('item C2', admin, self.colFolderC)
        self.colItemC3 = Item().createItem('item C3', admin, self.colFolderC)
        self.itemPub1 = Item().createItem('item Public 1', admin, self.publicFolder)
        self.itemPriv1 = Item().createItem('item Private 1', admin, self.privateFolder)
        self.folderD = Folder().createFolder(self.publicFolder, 'folder D', creator=admin)
        self.itemD1 = Item().createItem('item D1', admin, self.folderD)
        self.itemD2 = Item().createItem('item D2', admin, self.folderD)

    def testResourceItems(self, server, admin):
        self.makeResources(admin)
        # Now test that we get the items we expect
        # From a user
        resp = server.request(
            path='/resource/%s/items' % admin['_id'], user=admin,
            params={'type': 'user'})
        assert utilities.respStatus(resp) == 200
        items = resp.json
        assert [item['name'] for item in items] == [
            'item Public 1', 'item D1', 'item D2', 'item Private 1']
        # From a collection
        resp = server.request(
            path='/resource/%s/items' % self.collection['_id'], user=admin,
            params={'type': 'collection'})
        assert utilities.respStatus(resp) == 200
        items = resp.json
        assert [item['name'] for item in items] == [
            'item A1', 'item C1', 'item C2', 'item C3', 'item B1', 'item B2']
        # With sort, limit, and offset
        resp = server.request(
            path='/resource/%s/items' % self.collection['_id'], user=admin,
            params={'type': 'collection', 'limit': 4, 'offset': 1,
                    'sort': 'name', 'sortdir': -1})
        assert utilities.respStatus(resp) == 200
        items = resp.json
        assert [item['name'] for item in items] == [
            'item B1', 'item A1', 'item C3', 'item C2']
        resp = server.request(
            path='/resource/%s/items' % self.collection['_id'], user=admin,
            params={'type': 'collection', 'limit': 1, 'offset': 0,
                    'sort': 'name', 'sortdir': -1})
        assert utilities.respStatus(resp) == 200
        items = resp.json
        assert [item['name'] for item in items] == ['item B2']
        # From a folder
        resp = server.request(
            path='/resource/%s/items' % self.colFolderA['_id'],
            user=admin, params={'type': 'folder'})
        assert utilities.respStatus(resp) == 200
        items = resp.json
        assert [item['name'] for item in items] == [
            'item A1', 'item C1', 'item C2', 'item C3']
        # From a lower folder
        resp = server.request(
            path='/resource/%s/items' % self.colFolderC['_id'],
            user=admin, params={'type': 'folder'})
        assert utilities.respStatus(resp) == 200
        items = resp.json
        assert [item['name'] for item in items] == ['item C1', 'item C2', 'item C3']

        # With a bad parameter
        resp = server.request(
            path='/resource/%s/items' % self.colFolderC['_id'],
            user=admin, params={'type': 'collection'})
        assert utilities.respStatus(resp) == 400
        assert 'Resource not found' in resp.json['message']

    def testItemQuery(self, server, admin, user):
        self.makeResources(admin)
        itemMeta = [
            {'key1': 'value1'},
            {'key1': 'value2'},
            {'key1': 'value1', 'key2': 'value2'},
        ]
        for idx, meta in enumerate(itemMeta):
            item = Item().createItem('item %d' % idx, admin, self.privateFolder)
            item['meta'] = meta
            item = Item().save(item)
        resp = server.request(
            path='/item/query', user=admin, params={'query': json.dumps({
                'meta.key1': {'$exists': True}
            })})
        assert utilities.respStatus(resp) == 200
        items = resp.json
        assert len(items) == 3
        resp = server.request(
            path='/item/query', user=user, params={'query': json.dumps({
                'meta.key1': {'$exists': True}
            })})
        assert utilities.respStatus(resp) == 200
        items = resp.json
        assert len(items) == 0
        resp = server.request(
            path='/item/query', user=admin, params={'query': json.dumps({
                'meta.key1': 'value1'
            })})
        assert utilities.respStatus(resp) == 200
        items = resp.json
        assert len(items) == 2
        resp = server.request(
            path='/item/query', user=admin, params={'query': json.dumps({
                'meta': {'key1': 'value1'}
            })})
        assert utilities.respStatus(resp) == 200
        items = resp.json
        assert len(items) == 1

    def testResourceMetadata(self, server, admin):
        self.makeResources(admin)
        resp = server.request(
            method='PUT', path='/resource/metadata', params={
                'resources': json.dumps({'item': [str(self.colItemA1['_id'])]}),
                'metadata': json.dumps({
                    'keya': 'valuea',
                    'keyb.keyc': 'valuec'
                })})
        assert utilities.respStatus(resp) == 401
        resp = server.request(
            method='PUT', path='/resource/metadata', user=admin, params={
                'resources': json.dumps({'item': [str(self.colItemA1['_id'])]}),
                'metadata': json.dumps({
                    'keya': 'valuea',
                    'keyb.keyc': 'valuec'
                })})
        assert utilities.respStatus(resp) == 200
        assert resp.json == 1
        meta = Item().load(self.colItemA1['_id'], user=admin)['meta']
        assert meta['keya'] == 'valuea'
        assert meta['keyb']['keyc'] == 'valuec'
        resp = server.request(
            method='PUT', path='/resource/metadata', user=admin, params={
                'resources': json.dumps({'item': [
                    str(self.colItemA1['_id']),
                    str(self.colItemB1['_id'])
                ], 'folder': [str(self.colFolderA['_id'])]}),
                'metadata': json.dumps({
                    'keya': 'valuea',
                    'keyb.keyc': None,
                    'keyb.keyd': 'valued',
                })})
        assert utilities.respStatus(resp) == 200
        assert resp.json == 3
        meta = Item().load(self.colItemA1['_id'], user=admin)['meta']
        assert meta['keya'] == 'valuea'
        assert 'keyc' not in meta['keyb']
        assert meta['keyb']['keyd'] == 'valued'
        resp = server.request(
            method='PUT', path='/resource/metadata', user=admin, params={
                'resources': json.dumps({'item': [
                    str(self.colItemA1['_id']),
                ], 'folder': [str(self.colFolderA['_id'])]}),
                'metadata': json.dumps({
                    'keya': 'valuea',
                    'keyb.keyc': None,
                    'keyb.keyd': 'valued',
                }),
                'allowNull': True})
        assert utilities.respStatus(resp) == 200
        assert resp.json == 2
        meta = Item().load(self.colItemA1['_id'], user=admin)['meta']
        assert meta['keya'] == 'valuea'
        assert meta['keyb']['keyc'] is None
        assert meta['keyb']['keyd'] == 'valued'


@pytest.mark.plugin('digital_slide_archive')
class TestDSAEndpoints(object):
    def makeResources(self, admin):
        self.user2 = User().createUser(
            email='user2@email.com', login='user2', firstName='user2',
            lastName='user2', password='password', admin=False)
        self.group = self.group = Group().createGroup('test group', creator=self.user2)
        Group().addUser(self.group, self.user2)

    def testDSASettings(self, server):
        key = PluginSettings.DSA_DEFAULT_DRAW_STYLES

        resp = server.request(path='/digital_slide_archive/settings')
        assert utilities.respStatus(resp) == 200
        settings = resp.json
        assert settings[key] is None

        Setting().set(key, '')
        assert Setting().get(key) is None
        with pytest.raises(ValidationException, match='must be a JSON'):
            Setting().set(key, 'not valid')
        with pytest.raises(ValidationException, match='must be a JSON'):
            Setting().set(key, json.dumps({'not': 'a list'}))
        value = [{'lineWidth': 8, 'id': 'Group 8'}]
        Setting().set(key, json.dumps(value))
        assert json.loads(Setting().get(key)) == value
        Setting().set(key, value)
        assert json.loads(Setting().get(key)) == value

        resp = server.request(path='/digital_slide_archive/settings')
        assert utilities.respStatus(resp) == 200
        settings = resp.json
        assert json.loads(settings[key]) == value

    def testGeneralSettings(self, server, admin, user):
        self.makeResources(admin)
        settings = [{
            'key': PluginSettings.DSA_WEBROOT_PATH,
            'initial': 'dsa',
            'bad': {
                'girder': 'not be "girder"',
                '': 'not be empty'
            },
            'good': {'alternate1': 'alternate1'},
        }, {
            'key': PluginSettings.DSA_BRAND_NAME,
            'initial': 'Digital Slide Archive',
            'bad': {'': 'not be empty'},
            'good': {'Alternate': 'Alternate'},
        }, {
            'key': PluginSettings.DSA_BRAND_COLOR,
            'initial': '#777777',
            'bad': {
                '': 'not be empty',
                'white': 'be a hex color',
                '#777': 'be a hex color'
            },
            'good': {'#000000': '#000000'},
        }, {
            'key': PluginSettings.DSA_BANNER_COLOR,
            'initial': '#f8f8f8',
            'bad': {
                '': 'not be empty',
                'white': 'be a hex color',
                '#777': 'be a hex color'
            },
            'good': {'#000000': '#000000'},
        }]
        for setting in settings:
            key = setting['key']
            assert Setting().get(key) == setting['initial']
            for badval in setting.get('bad', {}):
                with pytest.raises(ValidationException, match=setting['bad'][badval]):
                    Setting().set(key, badval)
            for badval in setting.get('badjson', []):
                with pytest.raises(ValidationException, match=badval['return']):
                    Setting().set(key, badval['value'])
            for goodval in setting.get('good', {}):
                assert Setting().set(key, goodval)['value'] == setting['good'][goodval]
            for goodval in setting.get('goodjson', []):
                assert Setting().set(key, goodval['value'])['value'] == goodval['return']

    def testGetWebroot(self, server):
        resp = server.request(path='/dsa', method='GET', isJson=False, prefix='')
        assert utilities.respStatus(resp) == 200
        body = utilities.getBody(resp)
        assert '<title>Digital Slide Archive</title>' in body
        resp = server.request(path='/alternate2', method='GET', isJson=False, prefix='')
        assert utilities.respStatus(resp) == 404
        Setting().set(PluginSettings.DSA_WEBROOT_PATH, 'alternate2')
        Setting().set(PluginSettings.DSA_BRAND_NAME, 'Alternate')
        resp = server.request(path='/dsa', method='GET', isJson=False, prefix='')
        assert utilities.respStatus(resp) == 200
        body = utilities.getBody(resp)
        assert '<title>Alternate</title>' in body
        resp = server.request(path='/alternate2', method='GET', isJson=False, prefix='')
        assert utilities.respStatus(resp) == 200
        body = utilities.getBody(resp)
        assert '<title>Alternate</title>' in body

    def testRestrictDownloads(self, server, fsAssetstore, admin, user):
        self.makeResources(admin)
        file = utilities.uploadExternalFile(
            'data/Easy1.png.sha512', user, fsAssetstore)
        resp = server.request(
            path='/item/%s/download' % file['itemId'], user=self.user2, isJson=False)
        assert utilities.respStatus(resp) == 200
        resp = server.request(
            path='/item/%s/download' % file['itemId'], user=None)
        assert utilities.respStatus(resp) == 401
        resp = server.request(
            path='/item/%s/tiles/images/noimage' % file['itemId'], user=self.user2)
        assert utilities.respStatus(resp) == 400
        resp = server.request(
            path='/item/%s/tiles/images/noimage' % file['itemId'], user=None)
        assert utilities.respStatus(resp) == 401

    def testQuarantine(self, server, admin, user):
        publicFolder = Folder().childFolders(  # noqa: B305
            user, 'user', filters={'name': 'Public'}
        ).next()
        adminFolder = Folder().childFolders(  # noqa: B305
            admin, 'user', filters={'name': 'Public'}
        ).next()
        privateFolder = Folder().childFolders(  # noqa: B305
            admin, 'user', filters={'name': 'Private'}, user=admin
        ).next()
        items = [Item().createItem(name, creator, folder) for name, creator, folder in [
            ('userPublic1', user, publicFolder),
            ('userPublic2', user, publicFolder),
            ('adminPublic1', admin, adminFolder),
            ('adminPublic2', admin, adminFolder),
            ('adminPrivate1', admin, privateFolder),
            ('adminPrivate2', admin, privateFolder),
        ]]
        resp = server.request(
            method='PUT',
            path='/digital_slide_archive/quarantine/%s' % str(items[0]['_id']))
        assert utilities.respStatus(resp) == 401
        assert 'Write access denied' in resp.json['message']
        resp = server.request(
            method='PUT', user=user,
            path='/digital_slide_archive/quarantine/%s' % str(items[0]['_id']))
        assert utilities.respStatus(resp) == 400
        assert 'The quarantine folder is not configure' in resp.json['message']
        key = PluginSettings.DSA_QUARANTINE_FOLDER
        Setting().set(key, str(privateFolder['_id']))
        resp = server.request(
            method='PUT', user=user,
            path='/digital_slide_archive/quarantine/%s' % str(items[0]['_id']))
        assert utilities.respStatus(resp) == 200
        resp = server.request(
            method='PUT', user=user,
            path='/digital_slide_archive/quarantine/%s' % str(items[0]['_id']))
        assert utilities.respStatus(resp) == 403
        assert 'Write access denied' in resp.json['message']
        resp = server.request(
            method='PUT', user=user,
            path='/digital_slide_archive/quarantine/%s' % str(items[2]['_id']))
        assert utilities.respStatus(resp) == 403
        assert 'Write access denied' in resp.json['message']
        resp = server.request(
            method='PUT', user=admin,
            path='/digital_slide_archive/quarantine/%s' % str(items[2]['_id']))
        assert utilities.respStatus(resp) == 200
        resp = server.request(
            method='PUT', user=admin,
            path='/digital_slide_archive/quarantine/%s' % str(items[4]['_id']))
        assert utilities.respStatus(resp) == 400
        assert 'already in the quarantine' in resp.json['message']
        # Restore
        resp = server.request(
            method='PUT', user=admin,
            path='/digital_slide_archive/quarantine/%s/restore' % str(items[1]['_id']))
        assert utilities.respStatus(resp) == 400
        assert 'no quarantine record' in resp.json['message']
        resp = server.request(
            method='PUT',
            path='/digital_slide_archive/quarantine/%s/restore' % str(items[0]['_id']))
        assert utilities.respStatus(resp) == 401
        assert 'Write access denied' in resp.json['message']
        resp = server.request(
            method='PUT', user=user,
            path='/digital_slide_archive/quarantine/%s/restore' % str(items[0]['_id']))
        assert utilities.respStatus(resp) == 403
        assert 'Write access denied' in resp.json['message']
        resp = server.request(
            method='PUT', user=admin,
            path='/digital_slide_archive/quarantine/%s/restore' % str(items[0]['_id']))
        assert utilities.respStatus(resp) == 200
        resp = server.request(
            method='PUT', user=admin,
            path='/digital_slide_archive/quarantine/%s/restore' % str(items[0]['_id']))
        assert utilities.respStatus(resp) == 400
        assert 'no quarantine record' in resp.json['message']
        resp = server.request(
            method='PUT', user=user,
            path='/digital_slide_archive/quarantine/%s' % str(items[0]['_id']))
        assert utilities.respStatus(resp) == 200
