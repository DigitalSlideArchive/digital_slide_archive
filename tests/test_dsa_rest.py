# -*- coding: utf-8 -*-

"""Test digital_slide_archive endpoints"""

import json
import pytest

from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.item import Item

from . import girder_utilities as utilities


@pytest.mark.plugin('digital_slide_archive')
class TestDigitalSlideArchiveRest(object):
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
