#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#############################################################################

import json
import os

from girder import config
from girder.models.item import Item
from tests import base


# boiler plate to start and stop the server

os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')
config.loadConfig()  # Must reload config to pickup correct port


def setUpModule():
    base.enabledPlugins.append('digital_slide_archive')
    base.startServer(False)


def tearDownModule():
    base.stopServer()


# Test digital_slide_archive endpoints
class DigitalSlideArchiveRestTest(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)
        admin = {
            'email': 'admin@email.com',
            'login': 'adminlogin',
            'firstName': 'Admin',
            'lastName': 'Last',
            'password': 'adminpassword',
            'admin': True
        }
        self.admin = self.model('user').createUser(**admin)
        user = {
            'email': 'user@email.com',
            'login': 'userlogin',
            'firstName': 'Common',
            'lastName': 'User',
            'password': 'userpassword'
        }
        self.user = self.model('user').createUser(**user)
        folders = self.model('folder').childFolders(
            self.admin, 'user', user=self.admin)
        for folder in folders:
            if folder['name'] == 'Public':
                self.publicFolder = folder
            if folder['name'] == 'Private':
                self.privateFolder = folder

    def testResourceItems(self):
        # Create some resources to use in the tests
        self.collection = self.model('collection').createCollection(
            'collection A', self.admin)
        self.colFolderA = self.model('folder').createFolder(
            self.collection, 'folder A', parentType='collection',
            creator=self.admin)
        self.colFolderB = self.model('folder').createFolder(
            self.collection, 'folder B', parentType='collection',
            creator=self.admin)
        self.colFolderC = self.model('folder').createFolder(
            self.colFolderA, 'folder C', creator=self.admin)
        self.colItemA1 = self.model('item').createItem(
            'item A1', self.admin, self.colFolderA)
        self.colItemB1 = self.model('item').createItem(
            'item B1', self.admin, self.colFolderB)
        self.colItemB2 = self.model('item').createItem(
            'item B2', self.admin, self.colFolderB)
        self.colItemC1 = self.model('item').createItem(
            'item C1', self.admin, self.colFolderC)
        self.colItemC2 = self.model('item').createItem(
            'item C2', self.admin, self.colFolderC)
        self.colItemC3 = self.model('item').createItem(
            'item C3', self.admin, self.colFolderC)
        self.itemPub1 = self.model('item').createItem(
            'item Public 1', self.admin, self.publicFolder)
        self.itemPriv1 = self.model('item').createItem(
            'item Private 1', self.admin, self.privateFolder)
        self.folderD = self.model('folder').createFolder(
            self.publicFolder, 'folder D', creator=self.admin)
        self.itemD1 = self.model('item').createItem(
            'item D1', self.admin, self.folderD)
        self.itemD2 = self.model('item').createItem(
            'item D2', self.admin, self.folderD)
        # Now test that we get the items we expect
        # From a user
        resp = self.request(
            path='/resource/%s/items' % self.admin['_id'], user=self.admin,
            params={'type': 'user'})
        self.assertStatusOk(resp)
        items = resp.json
        self.assertEqual([item['name'] for item in items],
                         ['item Public 1', 'item D1', 'item D2',
                          'item Private 1'])
        # From a collection
        resp = self.request(
            path='/resource/%s/items' % self.collection['_id'], user=self.admin,
            params={'type': 'collection'})
        self.assertStatusOk(resp)
        items = resp.json
        self.assertEqual([item['name'] for item in items],
                         ['item A1', 'item C1', 'item C2', 'item C3',
                          'item B1', 'item B2'])
        # With sort, limit, and offset
        resp = self.request(
            path='/resource/%s/items' % self.collection['_id'], user=self.admin,
            params={'type': 'collection', 'limit': 4, 'offset': 1,
                    'sort': 'name', 'sortdir': -1})
        self.assertStatusOk(resp)
        items = resp.json
        self.assertEqual([item['name'] for item in items],
                         ['item B1', 'item A1', 'item C3', 'item C2'])
        resp = self.request(
            path='/resource/%s/items' % self.collection['_id'], user=self.admin,
            params={'type': 'collection', 'limit': 1, 'offset': 0,
                    'sort': 'name', 'sortdir': -1})
        self.assertStatusOk(resp)
        items = resp.json
        self.assertEqual([item['name'] for item in items], ['item B2'])
        # From a folder
        resp = self.request(
            path='/resource/%s/items' % self.colFolderA['_id'],
            user=self.admin, params={'type': 'folder'})
        self.assertStatusOk(resp)
        items = resp.json
        self.assertEqual([item['name'] for item in items],
                         ['item A1', 'item C1', 'item C2', 'item C3'])
        # From a lower folder
        resp = self.request(
            path='/resource/%s/items' % self.colFolderC['_id'],
            user=self.admin, params={'type': 'folder'})
        self.assertStatusOk(resp)
        items = resp.json
        self.assertEqual([item['name'] for item in items],
                         ['item C1', 'item C2', 'item C3'])

        # With a bad parameter
        resp = self.request(
            path='/resource/%s/items' % self.colFolderC['_id'],
            user=self.admin, params={'type': 'collection'})
        self.assertStatus(resp, 400)
        self.assertIn('Resource not found', resp.json['message'])

    def testItemQuery(self):
        itemMeta = [
            {'key1': 'value1'},
            {'key1': 'value2'},
            {'key1': 'value1', 'key2': 'value2'},
        ]
        for idx, meta in enumerate(itemMeta):
            item = self.model('item').createItem('item %d' % idx, self.admin, self.privateFolder)
            item['meta'] = meta
            item = Item().save(item)
        resp = self.request(
            path='/item/query', user=self.admin, params={'query': json.dumps({
                'meta.key1': {'$exists': True}
            })})
        self.assertStatusOk(resp)
        items = resp.json
        self.assertEqual(len(items), 3)
        resp = self.request(
            path='/item/query', user=self.user, params={'query': json.dumps({
                'meta.key1': {'$exists': True}
            })})
        self.assertStatusOk(resp)
        items = resp.json
        self.assertEqual(len(items), 0)
        resp = self.request(
            path='/item/query', user=self.admin, params={'query': json.dumps({
                'meta.key1': 'value1'
            })})
        self.assertStatusOk(resp)
        items = resp.json
        self.assertEqual(len(items), 2)
        resp = self.request(
            path='/item/query', user=self.admin, params={'query': json.dumps({
                'meta': {'key1': 'value1'}
            })})
        self.assertStatusOk(resp)
        items = resp.json
        self.assertEqual(len(items), 1)
