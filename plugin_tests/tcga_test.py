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
import json

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

        self.TCGAModel = self.model('cohort', 'digital_slide_archive')


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

    def testCohortModel(self):
        folderModel = self.model('folder')
        cohortModel = self.model('cohort', 'digital_slide_archive')
        doc = folderModel.createFolder(
            self.tcgaCollection, 'ucec', parentType='collection',
            public=True, creator=self.admin
        )
        cohortModel.importDocument(doc, user=self.admin)
        self.assertEqual(cohortModel.getTCGAType(doc), 'cohort')

        with self.assertRaises(ValidationException):
            cohortModel.importDocument(self.publicFolder, user=self.admin)

        cohortModel.removeTCGA(doc)
        self.assertEquals(cohortModel.findOne({}), None)

        folderModel.createFolder(
            doc, 'subfolder', public=True, creator=self.admin
        )
        cohortModel.importDocument(
            doc, user=self.admin, recurse=True
        )
        self.assertEquals(cohortModel.findOne({}).get('_id'), doc['_id'])

    def testCaseModel(self):
        folderModel = self.model('folder')
        cohortModel = self.model('cohort', 'digital_slide_archive')
        caseModel = self.model('case', 'digital_slide_archive')

        cohort = folderModel.createFolder(
            self.tcgaCollection, 'ucec', parentType='collection',
            public=True, creator=self.admin
        )
        invaliddoc = folderModel.createFolder(
            cohort, 'invalid name', parentType='folder',
            public=True, creator=self.admin
        )
        doc = folderModel.createFolder(
            cohort, 'TCGA-W5-AA2O', parentType='folder',
            public=True, creator=self.admin
        )
        folderModel.createFolder(
            doc, 'sub folder'
        )

        with self.assertRaises(ValidationException):
            caseModel.importDocument(self.tcgaCollection, user=self.admin)

        with self.assertRaises(ValidationException):
            caseModel.importDocument(doc, user=self.admin)

        cohortModel.importDocument(cohort, user=self.admin, recurse=True)
        self.assertEqual(
            caseModel.findOne({'_id': doc['_id']}).get('_id'),
            doc['_id']
        )

        with self.assertRaises(ValidationException):
            caseModel.importDocument(invaliddoc, user=self.admin)

    def testSlideModel(self):
        folderModel = self.model('folder')
        cohortModel = self.model('cohort', 'digital_slide_archive')
        slideModel = self.model('slide', 'digital_slide_archive')

        cohort = folderModel.createFolder(
            self.tcgaCollection, 'ucec', parentType='collection',
            public=True, creator=self.admin
        )
        case = folderModel.createFolder(
            cohort, 'TCGA-W5-AA2O', parentType='folder',
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

        cohortModel.importDocument(cohort, user=self.admin, recurse=True)
        self.assertEqual(
            slideModel.findOne({'_id': doc['_id']}).get('_id'),
            doc['_id']
        )

    def testImageModel(self):
        folderModel = self.model('folder')
        itemModel = self.model('item')
        fileModel = self.model('file')
        cohortModel = self.model('cohort', 'digital_slide_archive')
        imageModel = self.model('image', 'digital_slide_archive')

        cohort = folderModel.createFolder(
            self.tcgaCollection, 'ucec', parentType='collection',
            public=True, creator=self.admin
        )
        case = folderModel.createFolder(
            cohort, 'TCGA-W5-AA2O', parentType='folder',
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

        cohortModel.importDocument(cohort, user=self.admin, recurse=True)

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
        self.cohort = self.model('folder').createFolder(
            self.tcgaCollection, 'acc',
            parentType='collection', public=True, creator=self.admin
        )

        self.cohort2 = self.model('folder').createFolder(
            self.tcgaCollection, 'other',
            parentType='collection', public=True, creator=self.admin
        )

        self.case1 = self.model('folder').createFolder(
            self.cohort, 'TCGA-OR-A5J1', parentType='folder',
            public=True, creator=self.user
        )
        self.case2 = self.model('folder').createFolder(
            self.cohort, 'TCGA-OR-A5J2', parentType='folder',
            public=True, creator=self.user
        )
        self.case3 = self.model('folder').createFolder(
            self.cohort2, 'TCGA-OR-A5J3', parentType='folder',
            public=True, creator=self.user
        )
        self.case4 = self.model('folder').createFolder(
            self.cohort, 'TCGA-OR-A5J4', parentType='folder',
            public=True, creator=self.user
        )

        self.slide1 = self.model('folder').createFolder(
            self.case1, 'TCGA-OR-A5J1-01A-01-TS1', parentType='folder',
            public=True, creator=self.user
        )
        self.slide2 = self.model('folder').createFolder(
            self.case1, 'TCGA-OR-A5J1-01Z-00-DX1', parentType='folder',
            public=True, creator=self.user
        )
        self.slide3 = self.model('folder').createFolder(
            self.case2, 'TCGA-OR-A5J2-01A-01-TS1', parentType='folder',
            public=True, creator=self.user
        )
        self.slide4 = self.model('folder').createFolder(
            self.case3, 'TCGA-OR-A5J3-01A-01-TS2', parentType='folder',
            public=True, creator=self.user
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

        self.pathologyFolder = self.model('folder').createFolder(
            self.publicFolder, 'pathologies',
            public=True, creator=self.user
        )
        self.pathology1, self.pathology_file1 = self.createFileItem(
            'TCGA-OR-A5J1.1130D2F4-FABF-4F97-B6A0-23390E196305.pdf',
            self.user,
            self.pathologyFolder
        )
        self.pathology2 = self.model('item').createItem(
            'TCGA-OR-A5J2.33BC8197-BDEB-4EC4-83A4-B871A8C0A094.pdf',
            self.user,
            self.pathologyFolder
        )

        self.aperioFolder = self.model('folder').createFolder(
            self.publicFolder, 'annotations',
            public=True, creator=self.user
        )
        self.aperio1, self.aperio_file1 = self.createFileItem(
            'TCGA-OR-A5J1-01Z-00-DX1.xml',
            self.user,
            self.aperioFolder
        )
        self.aperio2, self.aperio_file2 = self.createFileItem(
            'TCGA-OR-A5J2-01Z-00-DX1.xml',
            self.user,
            self.aperioFolder
        )
        self.aperio_invalid = self.model('item').createItem(
            'TCGA-OR-A5J1-01Z-00-DX1.xml',
            self.user,
            self.aperioFolder
        )

    def createFileItem(self, name, creator, parent):
        doc = self.model('item').createItem(
            name, creator, parent
        )
        file = self.model('file').createFile(
            creator, doc, doc['name'],
            0, {'_id': ''}
        )
        self.model('item').save(doc)
        return doc, file

    def createImageItem(self, name, slide):
        doc, file = self.createFileItem(name, self.admin, slide)
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

    def testCohortEndpoints(self):
        resp = self.request(
            path='/tcga/cohort'
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['data'], [])

        resp = self.request(
            path='/tcga/cohort',
            params={'folderId': self.cohort['_id']},
            method='POST'
        )
        self.assertStatus(resp, 401)

        resp = self.request(
            path='/tcga/cohort',
            params={'folderId': self.cohort['_id']},
            method='POST',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/cohort/' + str(self.cohort['_id'])
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], self.cohort['name'])

        resp = self.request(
            path='/tcga/cohort/' + str(self.cohort['_id']),
            method='DELETE',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/cohort'
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['data'], [])

        # import recursively and test searching for slides
        resp = self.request(
            path='/tcga/import',
            method='POST',
            user=self.admin,
        )
        self.assertStatusOk(resp)
        resp = self.request(
            path='/tcga/cohort/' + str(self.cohort['_id']) + '/slides'
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['data']), 3)

        resp = self.request(
            path='/tcga/cohort/' + str(self.cohort2['_id']) + '/slides'
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['data']), 1)

        resp = self.request(
            path='/tcga/cohort/' + str(self.cohort['_id']) + '/images'
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['data']), 3)
        self.assertEqual(resp.json['data'][0]['tcga']['type'], 'image')

    def testCaseEndpoints(self):
        resp = self.request(
            path='/tcga/import',
            method='POST',
            user=self.admin,
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/case',
            params={'cohort': str(self.cohort['_id'])}
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['data']), 3)

        resp = self.request(
            path='/tcga/case/' + str(self.case1['_id']),
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], self.case1['name'])

        # search for images under a case 1
        resp = self.request(
            path='/tcga/case/' + str(self.case1['_id']) + '/images'
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['data']), 2)

        # search for images under a case 2
        resp = self.request(
            path='/tcga/case/' + str(self.case2['_id']) + '/images'
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['data']), 1)

        resp = self.request(
            path='/tcga/case/' + str(self.case1['_id']),
            method='DELETE',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/case',
            params={'cohort': str(self.cohort['_id'])}
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['data']), 2)

        resp = self.request(
            path='/tcga/case',
            params={'folderId': self.case1['_id']},
            method='POST',
            user=self.admin
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], self.case1['name'])

        resp = self.request(
            path='/tcga/case/label/' + self.case2['name']
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['_id'], str(self.case2['_id']))

        resp = self.request(
            path='/tcga/case/label/' + 'notalabel'
        )
        self.assertStatus(resp, 400)

    def testCaseMetadata(self):
        id1 = str(self.case1['_id'])
        id2 = str(self.case2['_id'])
        resp = self.request(
            path='/tcga/import',
            method='POST',
            user=self.admin,
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/case/' + id1 + '/metadata/tables'
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

        resp = self.request(
            path='/tcga/case/' + id1 + '/metadata/table1',
            method='POST',
            body=json.dumps({
                'key1': 'value1',
                'key2': 'value2'
            })
        )
        self.assertStatus(resp, 401)

        resp = self.request(
            path='/tcga/case/' + id1 + '/metadata/table1',
            method='POST',
            body=json.dumps({
                'key1': 'value1',
                'key2': 'value2'
            }),
            user=self.user,
            type='application/json'
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/case/' + id1 + '/metadata/tables'
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, ['table1'])

        resp = self.request(
            path='/tcga/case/' + id1 + '/metadata/table1',
        )
        self.assertStatusOk(resp)
        self.assertEqual(set(resp.json.keys()), {'key1', 'key2'})

        resp = self.request(
            path='/tcga/case/' + id1 + '/metadata/table1',
            method='PUT',
            body=json.dumps({
                'key1': None,
                'key3': 'value3'
            }),
            user=self.user,
            type='application/json'
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/case/' + id1 + '/metadata/table1',
        )
        self.assertStatusOk(resp)
        self.assertEqual(set(resp.json.keys()), {'key2', 'key3'})

        resp = self.request(
            path='/tcga/case/' + id2 + '/metadata/table1',
            method='POST',
            body=json.dumps({
                'key1': 'value1'
            }),
            user=self.user,
            type='application/json'
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/case/search',
            params={'table': 'table1'}
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['data']), 2)

        resp = self.request(
            path='/tcga/case/search',
            params={'table': 'table1', 'key': 'key1'}
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['data']), 1)
        self.assertEqual(resp.json['data'][0]['_id'], id2)

        resp = self.request(
            path='/tcga/case/search',
            params={'table': 'table1', 'key': 'key1', 'value': 'value2'}
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['data']), 0)

        resp = self.request(
            path='/tcga/case/' + id2 + '/metadata/table1',
            method='DELETE',
            user=self.user
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/case/' + id2 + '/metadata/tables'
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])

    def testSlideEndpoints(self):
        case1 = str(self.case1['_id'])
        slide1 = str(self.slide1['_id'])
        resp = self.request(
            path='/tcga/import',
            method='POST',
            user=self.admin,
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/slide',
            params={'case': case1}
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['data']), 2)

        resp = self.request(
            path='/tcga/slide/' + slide1
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], self.slide1['name'])

        resp = self.request(
            path='/tcga/slide/' + slide1,
            method='DELETE',
            user=self.user
        )
        self.assertStatus(resp, 403)

        resp = self.request(
            path='/tcga/slide/' + slide1,
            method='DELETE',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/slide/' + slide1
        )
        self.assertStatus(resp, 400)

        resp = self.request(
            path='/tcga/slide',
            params={'folderId': slide1},
            method='POST',
            user=self.user
        )
        self.assertStatus(resp, 403)

        resp = self.request(
            path='/tcga/slide',
            params={'folderId': slide1},
            method='POST',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/slide/' + slide1
        )
        self.assertStatusOk(resp)

    def testImageEndpoints(self):
        slide1 = str(self.slide1['_id'])
        image1 = str(self.image1['_id'])
        resp = self.request(
            path='/tcga/import',
            method='POST',
            user=self.admin,
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/image',
            params={'slide': slide1}
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['data']), 1)
        self.assertEqual(
            resp.json['data'][0]['tcga'].get('caseId'),
            str(self.case1['_id'])
        )

        resp = self.request(
            path='/tcga/image/' + image1
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], self.image1['name'])

        resp = self.request(
            path='/tcga/image/' + image1,
            method='DELETE',
            user=self.user
        )
        self.assertStatus(resp, 403)

        resp = self.request(
            path='/tcga/image/' + image1,
            method='DELETE',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/image/' + image1
        )
        self.assertStatus(resp, 400)

        resp = self.request(
            path='/tcga/image',
            params={'itemId': image1},
            method='POST',
            user=self.user
        )
        self.assertStatus(resp, 403)

        resp = self.request(
            path='/tcga/image',
            params={'itemId': image1},
            method='POST',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/image/' + image1
        )
        self.assertStatusOk(resp)

    def testPathologyEndpoints(self):
        case1 = str(self.case1['_id'])
        pathology1 = str(self.pathology1['_id'])
        resp = self.request(
            path='/tcga/import',
            method='POST',
            user=self.admin,
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/pathology',
            params={'id': pathology1},
            method='POST',
            user=self.user
        )
        self.assertStatus(resp, 403)

        resp = self.request(
            path='/tcga/pathology',
            params={'id': pathology1},
            method='POST',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/pathology',
            params={'case': case1}
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['data']), 1)

        resp = self.request(
            path='/tcga/pathology/' + pathology1
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['name'], self.pathology1['name'])
        self.assertEqual(
            str(resp.json['file']['_id']),
            str(self.pathology_file1['_id'])
        )

        resp = self.request(
            path='/tcga/pathology/' + pathology1,
            method='DELETE',
            user=self.user
        )
        self.assertStatus(resp, 403)

        resp = self.request(
            path='/tcga/pathology/' + pathology1,
            method='DELETE',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/pathology/' + pathology1
        )
        self.assertStatus(resp, 400)

        resp = self.request(
            path='/tcga/pathology',
            params={'itemId': pathology1},
            method='POST',
            user=self.user
        )
        self.assertStatus(resp, 403)

        resp = self.request(
            path='/tcga/pathology',
            params={'id': pathology1},
            method='POST',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/pathology/' + pathology1
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/pathology',
            params={'id': str(self.pathologyFolder['_id']), 'recursive': True},
            method='POST',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/pathology/' + str(self.pathology2['_id'])
        )
        self.assertStatusOk(resp)

    def testAperioEndpoints(self):
        aperio1 = str(self.aperio1['_id'])
        aperio2 = str(self.aperio2['_id'])
        image = str(self.image2['_id'])
        resp = self.request(
            path='/tcga/import',
            method='POST',
            user=self.admin,
        )
        self.assertStatusOk(resp)

        # test access control
        resp = self.request(
            path='/tcga/aperio',
            params={'id': aperio1},
            method='POST',
            user=self.user
        )
        self.assertStatus(resp, 403)

        # test automatic import of tcga items
        resp = self.request(
            path='/tcga/aperio',
            params={'id': aperio1},
            method='POST',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/item/' + image + '/aperio'
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(
            str(resp.json[0]['_id']),
            str(self.aperio1['_id'])
        )
        self.assertEqual(
            str(resp.json[0]['file']['_id']),
            str(self.aperio_file1['_id'])
        )

        # test filtering by tag
        resp = self.request(
            path='/item/' + image + '/aperio',
            params={'tag': 'foo'}
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 0)

        # test writing a new tag
        resp = self.request(
            path='/item/' + aperio1 + '/aperio',
            params={'tag': 'foo'},
            method='PUT',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/item/' + image + '/aperio',
            params={'tag': 'foo'}
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)

        # test importing an annotation manually
        resp = self.request(
            path='/item/' + aperio2 + '/aperio',
            params={'tag': 'bar', 'imageId': image},
            method='POST',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/item/' + image + '/aperio',
            params={'tag': 'bar'}
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['_id'], aperio2)

        # test deleting an annotation
        resp = self.request(
            path='/item/' + aperio2 + '/aperio',
            method='DELETE',
            user=self.admin
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/item/' + image + '/aperio',
            params={'tag': 'bar'}
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 0)

    def testPagingParams(self):
        cohort1 = str(self.cohort['_id'])
        resp = self.request(
            path='/tcga/import',
            method='POST',
            user=self.admin,
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/tcga/case',
            params={'cohort': cohort1, 'limit': 2, 'offset': 0}
        )
        self.assertStatusOk(resp)
        data = resp.json

        self.assertEqual(data['pos'], 0)
        self.assertEqual(data['limit'], 2)
        self.assertEqual(data['total_count'], 3)
        self.assertEqual(data['current_page'], 0)
        self.assertEqual(data['total_pages'], 2)

        resp = self.request(
            path='/tcga/case',
            params={'cohort': cohort1, 'limit': 2, 'offset': 2}
        )
        self.assertStatusOk(resp)
        data = resp.json

        self.assertEqual(data['pos'], 2)
        self.assertEqual(data['limit'], 2)
        self.assertEqual(data['total_count'], 3)
        self.assertEqual(data['current_page'], 1)
        self.assertEqual(data['total_pages'], 2)

        resp = self.request(
            path='/tcga/case',
            params={'cohort': cohort1, 'limit': 2, 'offset': 1}
        )
        self.assertStatusOk(resp)
        data = resp.json

        self.assertEqual(data['pos'], 1)
        self.assertEqual(data['limit'], 2)
        self.assertEqual(data['total_count'], 3)
        self.assertEqual(data['current_page'], 0)
        self.assertEqual(data['total_pages'], 2)
