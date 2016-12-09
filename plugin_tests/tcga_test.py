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
import os

from girder import config
from girder.models.model_base import ValidationException
from tests import base


# boiler plate to start and stop the server

os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')
config.loadConfig()  # Must reload config to pickup correct port


def setUpModule():
    base.enabledPlugins.append('digital_slide_archive')
    base.startServer(False)


def tearDownModule():
    base.stopServer()


# base class
class BaseTest(object):
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

        self.tcgaCollection = self.model('collection').createCollection(
            'TCGA', self.admin
        )
        self.model('setting').set(
            'tcga.tcga_collection_id', self.tcgaCollection['_id'])

        self.TCGAModel = self.model('cancer', 'digital_slide_archive')


# test tcga models
class TCGAModelTest(BaseTest, base.TestCase):
    def testPruneNoneValues(self):
        from girder.plugins.digital_slide_archive.models.meta \
            import pruneNoneValues

        doc = {
            'a': 0,
            'b': {
                'c': '',
                'd': {
                    'e': {},
                    'f': None
                },
                'g': None
            },
            'h': None
        }
        pruneNoneValues(doc)
        self.assertEqual(set(doc.keys()), {'a', 'b'})
        self.assertEqual(set(doc['b'].keys()), {'c', 'd'})
        self.assertEqual(set(doc['b']['d'].keys()), {'e'})

    def testUpdateDict(self):
        from girder.plugins.digital_slide_archive.models.meta \
            import updateDict

        doc = {
            'a': 0,
            'b': {
                'c': '',
                'd': {
                    'e': {},
                    'f': 'value'
                },
                'g': 1
            },
            'h': 2
        }
        update = {
            'a': 1,
            'b': {
                'y': False,
                'd': {
                    'z': 10
                }
            }
        }
        updateDict(doc, update)
        self.assertEqual(set(doc.keys()), {'a', 'b', 'h'})
        self.assertEqual(doc['a'], 1)
        self.assertEqual(set(doc['b'].keys()), {'c', 'd', 'g', 'y'})
        self.assertEqual(doc['b']['d'], {
            'e': {}, 'f': 'value', 'z': 10})

    def testSetTCGA(self):
        doc = {}
        self.TCGAModel.setTCGA(doc, name='value', other='new')
        self.assertEqual(doc.get('tcga'), {'name': 'value', 'other': 'new'})

    def testUpdateTCGAMeta(self):
        doc = {}
        self.TCGAModel.updateTCGAMeta(doc, {'name': 'value', 'other': 'old'})
        self.assertEqual(self.TCGAModel.getTCGAMeta(doc), {
            'name': 'value', 'other': 'old'})

        self.TCGAModel.updateTCGAMeta(doc, {'name': None, 'other': 'new'})
        self.assertEqual(self.TCGAModel.getTCGAMeta(doc), {
            'other': 'new'})

    def testLoadDocument(self):
        with self.assertRaises(ValidationException):
            self.TCGAModel.loadDocument('')

        self.assertEqual(
            self.TCGAModel.loadDocument(
                self.user['_id'],
                user=self.admin
            )['_id'],
            self.user['_id']
        )

        self.assertEqual(
            self.TCGAModel.loadDocument(
                self.tcgaCollection['_id'],
                user=self.admin
            )['_id'],
            self.tcgaCollection['_id']
        )

        self.assertEqual(
            self.TCGAModel.loadDocument(
                self.publicFolder['_id'],
                user=self.admin
            )['_id'],
            self.publicFolder['_id']
        )

    def testCancerModel(self):
        folderModel = self.model('folder')
        cancerModel = self.model('cancer', 'digital_slide_archive')
        doc = folderModel.createFolder(
            self.tcgaCollection, 'ucec', parentType='collection',
            public=True, creator=self.admin
        )
        cancerModel.importDocument(doc, user=self.admin)
        self.assertEqual(cancerModel.getTCGAType(doc), 'cancer')

        with self.assertRaises(ValidationException):
            cancerModel.importDocument(self.publicFolder, user=self.admin)

        cancerModel.removeTCGA(doc)
        self.assertEquals(cancerModel.findOne({}), None)

        folderModel.createFolder(
            doc, 'subfolder', public=True, creator=self.admin
        )
        cancerModel.importDocument(
            doc, user=self.admin, recurse=True
        )
        self.assertEquals(cancerModel.findOne({}).get('_id'), doc['_id'])

    def testCaseModel(self):
        folderModel = self.model('folder')
        cancerModel = self.model('cancer', 'digital_slide_archive')
        caseModel = self.model('case', 'digital_slide_archive')

        cancer = folderModel.createFolder(
            self.tcgaCollection, 'ucec', parentType='collection',
            public=True, creator=self.admin
        )
        invaliddoc = folderModel.createFolder(
            cancer, 'invalid name', parentType='folder',
            public=True, creator=self.admin
        )
        doc = folderModel.createFolder(
            cancer, 'TCGA-W5-AA2O', parentType='folder',
            public=True, creator=self.admin
        )
        folderModel.createFolder(
            doc, 'sub folder'
        )

        with self.assertRaises(ValidationException):
            caseModel.importDocument(self.tcgaCollection, user=self.admin)

        with self.assertRaises(ValidationException):
            caseModel.importDocument(doc, user=self.admin)

        cancerModel.importDocument(cancer, user=self.admin, recurse=True)
        self.assertEqual(
            caseModel.findOne({'_id': doc['_id']}).get('_id'),
            doc['_id']
        )

        with self.assertRaises(ValidationException):
            caseModel.importDocument(invaliddoc, user=self.admin)

    def testSlideModel(self):
        folderModel = self.model('folder')
        cancerModel = self.model('cancer', 'digital_slide_archive')
        slideModel = self.model('slide', 'digital_slide_archive')

        cancer = folderModel.createFolder(
            self.tcgaCollection, 'ucec', parentType='collection',
            public=True, creator=self.admin
        )
        case = folderModel.createFolder(
            cancer, 'TCGA-W5-AA2O', parentType='folder',
            public=True, creator=self.admin
        )
        doc = folderModel.createFolder(
            case, 'TCGA-W5-AA2O-01A-01-TSA', parentType='folder',
            public=True, creator=self.admin
        )

        with self.assertRaises(ValidationException):
            slideModel.importDocument(case, user=self.admin)

        with self.assertRaises(ValidationException):
            slideModel.importDocument(doc, user=self.admin)

        cancerModel.importDocument(cancer, user=self.admin, recurse=True)
        self.assertEqual(
            slideModel.findOne({'_id': doc['_id']}).get('_id'),
            doc['_id']
        )

    def testImageModel(self):
        folderModel = self.model('folder')
        itemModel = self.model('item')
        fileModel = self.model('file')
        cancerModel = self.model('cancer', 'digital_slide_archive')
        imageModel = self.model('image', 'digital_slide_archive')

        cancer = folderModel.createFolder(
            self.tcgaCollection, 'ucec', parentType='collection',
            public=True, creator=self.admin
        )
        case = folderModel.createFolder(
            cancer, 'TCGA-W5-AA2O', parentType='folder',
            public=True, creator=self.admin
        )
        slide = folderModel.createFolder(
            case, 'TCGA-W5-AA2O-01A-01-TSA', parentType='folder',
            public=True, creator=self.admin
        )
        invalid = itemModel.createItem(
            'invalid_name.svs',
            self.admin, slide
        )
        doc = itemModel.createItem(
            'TCGA-W5-AA2O-01A-01-TSA.90E7868E-0605-43FD-A4A5-A2C0A6AC3AEE.svs',
            self.admin, slide
        )
        file = fileModel.createFile(
            self.admin, doc, doc['name'],
            0, {'_id': ''}
        )
        doc['largeImage'] = {
            'fileId': file['_id'],
            'sourceName': 'svs'
        }
        itemModel.save(doc)

        with self.assertRaises(ValidationException):
            imageModel.importDocument(doc, user=self.admin)

        cancerModel.importDocument(cancer, user=self.admin, recurse=True)

        ifile = fileModel.createFile(
            self.admin, invalid, doc['name'],
            0, {'_id': ''}
        )
        invalid['largeImage'] = {
            'fileId': ifile['_id'],
            'sourceName': 'svs'
        }
        itemModel.save(invalid)
        with self.assertRaises(ValidationException):
            imageModel.importDocument(invalid, user=self.admin)

        self.assertEqual(
            imageModel.findOne({'_id': doc['_id']}).get('_id'),
            doc['_id']
        )


# Test tcga endpoints
class TCGARestTest(BaseTest, base.TestCase):
    def setUp(self):
        super(TCGARestTest, self).setUp()
        self.cancer = self.model('folder').createFolder(
            self.tcgaCollection, 'acc',
            parentType='collection', public=True, creator=self.admin
        )

        self.case1 = self.model('folder').createFolder(
            self.cancer, 'TCGA-OR-A5J1', parentType='folder',
            public=True, creator=self.admin
        )
        self.case2 = self.model('folder').createFolder(
            self.cancer, 'TCGA-OR-A5J2', parentType='folder',
            public=True, creator=self.admin
        )

        self.slide1 = self.model('folder').createFolder(
            self.case1, 'TCGA-OR-A5J1-01A-01-TS1', parentType='folder',
            public=True, creator=self.admin
        )
        self.slide2 = self.model('folder').createFolder(
            self.case1, 'TCGA-OR-A5J1-01Z-00-DX1', parentType='folder',
            public=True, creator=self.admin
        )
        self.slide3 = self.model('folder').createFolder(
            self.case2, 'TCGA-OR-A5J2-01A-01-TS1', parentType='folder',
            public=True, creator=self.admin
        )

        self.image1 = self.createImageItem(
            'TCGA-OR-A5J1-01A-01-TS1.CFE08710-54B8-45B0-86AE-500D6E36D8A5.svs',
            self.slide1
        )
        self.image2 = self.createImageItem(
            'TCGA-OR-A5J1-01Z-00-DX1.600C7D8C-F04C-4125-AF14-B1E76DC01A1E.svs',
            self.slide2
        )
        self.image3 = self.createImageItem(
            'TCGA-OR-A5J2-01A-01-TS1.F951E65D-4231-4880-83AB-D17520D1AC95.svs',
            self.slide3
        )

    def createImageItem(self, name, slide):
        doc = self.model('item').createItem(
            name, self.admin, slide
        )
        file = self.model('file').createFile(
            self.admin, doc, doc['name'],
            0, {'_id': ''}
        )
        doc['largeImage'] = {
            'fileId': file['_id'],
            'sourceName': 'svs'
        }
        self.model('item').save(doc)
        return doc

    def testTCGACollection(self):
        resp = self.request(
            path='/tcga'
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['_id'], str(self.tcgaCollection['_id']))

        resp = self.request(
            path='/tcga',
            method='DELETE',
            user=self.user
        )
        self.assertStatus(resp, 403)

        resp = self.request(
            path='/tcga',
            method='DELETE',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga'
        )
        self.assertStatus(resp, 404)

        resp = self.request(
            path='/tcga',
            params={'collectionId': self.tcgaCollection['_id']},
            method='POST'
        )
        self.assertStatus(resp, 401)

        resp = self.request(
            path='/tcga',
            params={'collectionId': self.tcgaCollection['_id']},
            method='POST',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga'
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['_id'], str(self.tcgaCollection['_id']))

    def testRecursiveImport(self):
        resp = self.request(
            path='/tcga/import',
            method='POST',
            user=self.admin,
        )
        self.assertStatusOk(resp)
        images = list(self.model('image', 'digital_slide_archive').find({}))
        self.assertEqual(len(images), 3)
