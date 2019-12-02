# -*- coding: utf-8 -*-

import json
import pytest
import time

from girder.exceptions import ValidationException
from girder.models.collection import Collection
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.setting import Setting
from girder_jobs.constants import JobStatus

from digital_slide_archive.models.case import Case
from digital_slide_archive.models.cohort import Cohort
from digital_slide_archive.models.image import Image
from digital_slide_archive.models.meta import pruneNoneValues, updateDict
from digital_slide_archive.models.slide import Slide

from . import girder_utilities as utilities


def createFileItem(name, creator, parent):
    doc = Item().createItem(
        name, creator, parent
    )
    file = File().createFile(
        creator, doc, doc['name'],
        0, {'_id': ''}
    )
    Item().save(doc)
    return doc, file


def createImageItem(name, slide, admin):
    doc, file = createFileItem(name, admin, slide)
    doc['largeImage'] = {
        'fileId': file['_id'],
        'sourceName': 'svs'
    }
    Item().save(doc)
    return doc


def makeResources(self, admin, user):
    folders = Folder().childFolders(admin, 'user', user=admin)
    for folder in folders:
        if folder['name'] == 'Public':
            self.publicFolder = folder
        if folder['name'] == 'Private':
            self.privateFolder = folder
    self.tcgaCollection = Collection().createCollection('TCGA', admin)
    Setting().set('tcga.tcga_collection_id', self.tcgaCollection['_id'])

    # Used in rest tests
    self.cohort = Folder().createFolder(
        self.tcgaCollection, 'acc',
        parentType='collection', public=True, creator=admin)
    self.cohort2 = Folder().createFolder(
        self.tcgaCollection, 'other',
        parentType='collection', public=True, creator=admin)
    self.case1 = Folder().createFolder(
        self.cohort, 'TCGA-OR-A5J1', parentType='folder',
        public=True, creator=user)
    self.case2 = Folder().createFolder(
        self.cohort, 'TCGA-OR-A5J2', parentType='folder',
        public=True, creator=user)
    self.case3 = Folder().createFolder(
        self.cohort2, 'TCGA-OR-A5J3', parentType='folder',
        public=True, creator=user)
    self.case4 = Folder().createFolder(
        self.cohort, 'TCGA-OR-A5J4', parentType='folder',
        public=True, creator=user)
    self.slide1 = Folder().createFolder(
        self.case1, 'TCGA-OR-A5J1-01A-01-TS1', parentType='folder',
        public=True, creator=user)
    self.slide2 = Folder().createFolder(
        self.case1, 'TCGA-OR-A5J1-01Z-00-DX1', parentType='folder',
        public=True, creator=user)
    self.slide3 = Folder().createFolder(
        self.case2, 'TCGA-OR-A5J2-01A-01-TS1', parentType='folder',
        public=True, creator=user)
    self.slide4 = Folder().createFolder(
        self.case3, 'TCGA-OR-A5J3-01A-01-TS2', parentType='folder',
        public=True, creator=user)

    self.image1 = createImageItem(
        'TCGA-OR-A5J1-01A-01-TS1.CFE08710-54B8-45B0-86AE-500D6E36D8A5.svs',
        self.slide1, admin)
    self.image2 = createImageItem(
        'TCGA-OR-A5J1-01Z-00-DX1.600C7D8C-F04C-4125-AF14-B1E76DC01A1E.svs',
        self.slide2, admin)
    self.image3 = createImageItem(
        'TCGA-OR-A5J2-01A-01-TS1.F951E65D-4231-4880-83AB-D17520D1AC95.svs',
        self.slide3, admin)

    self.pathologyFolder = Folder().createFolder(
        self.publicFolder, 'pathologies',
        public=True, creator=user)
    self.pathology1, self.pathology_file1 = createFileItem(
        'TCGA-OR-A5J1.1130D2F4-FABF-4F97-B6A0-23390E196305.pdf',
        user, self.pathologyFolder)
    self.pathology2 = Item().createItem(
        'TCGA-OR-A5J2.33BC8197-BDEB-4EC4-83A4-B871A8C0A094.pdf',
        user, self.pathologyFolder)

    self.aperioFolder = Folder().createFolder(
        self.publicFolder, 'annotations', public=True, creator=user)
    self.aperio1, self.aperio_file1 = createFileItem(
        'TCGA-OR-A5J1-01Z-00-DX1.xml', user, self.aperioFolder)
    self.aperio2, self.aperio_file2 = createFileItem(
        'TCGA-OR-A5J2-01Z-00-DX1.xml', user, self.aperioFolder)
    self.aperio_invalid = Item().createItem(
        'TCGA-OR-A5J1-01Z-00-DX1.xml', user, self.aperioFolder)


@pytest.mark.plugin('digital_slide_archive')
class TestTCGAModel(object):
    def testPruneNoneValues(self):
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
        assert set(doc.keys()) == {'a', 'b'}
        assert set(doc['b'].keys()) == {'c', 'd'}
        assert set(doc['b']['d'].keys()) == {'e'}

    def testUpdateDict(self):
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
        assert set(doc.keys()) == {'a', 'b', 'h'}
        assert doc['a'] == 1
        assert set(doc['b'].keys()) == {'c', 'd', 'g', 'y'}
        assert doc['b']['d'] == {'e': {}, 'f': 'value', 'z': 10}

    def testSetTCGA(self, db):
        doc = {}
        Cohort().setTCGA(doc, name='value', other='new')
        assert doc.get('tcga') == {'name': 'value', 'other': 'new'}

    def testUpdateTCGAMeta(self, db):
        doc = {}
        Cohort().updateTCGAMeta(doc, {'name': 'value', 'other': 'old'})
        assert Cohort().getTCGAMeta(doc) == {'name': 'value', 'other': 'old'}

        Cohort().updateTCGAMeta(doc, {'name': None, 'other': 'new'})
        assert Cohort().getTCGAMeta(doc) == {'other': 'new'}

    def testLoadDocument(self, server, admin, user):
        makeResources(self, admin, user)
        with pytest.raises(ValidationException):
            Cohort().loadDocument('')

        assert Cohort().loadDocument(user['_id'], user=admin)['_id'] == user['_id']

        assert Cohort().loadDocument(
            self.tcgaCollection['_id'], user=admin)['_id'] == self.tcgaCollection['_id']

        assert Cohort().loadDocument(
            self.publicFolder['_id'], user=admin)['_id'] == self.publicFolder['_id']

    def testCohortModel(self, server, admin, user):
        makeResources(self, admin, user)
        doc = Folder().createFolder(
            self.tcgaCollection, 'ucec', parentType='collection',
            public=True, creator=admin
        )
        Cohort().importDocument(doc, user=admin)
        assert Cohort().getTCGAType(doc) == 'cohort'

        with pytest.raises(ValidationException):
            Cohort().importDocument(self.publicFolder, user=admin)

        Cohort().removeTCGA(doc)
        assert Cohort().findOne({}) is None

        Folder().createFolder(doc, 'subfolder', public=True, creator=admin)
        Cohort().importDocument(doc, user=admin, recurse=True)
        assert Cohort().findOne({}).get('_id') == doc['_id']

    def testCaseModel(self, server, admin, user):
        makeResources(self, admin, user)
        cohort = Folder().createFolder(
            self.tcgaCollection, 'ucec', parentType='collection',
            public=True, creator=admin
        )
        invaliddoc = Folder().createFolder(
            cohort, 'invalid name', parentType='folder',
            public=True, creator=admin
        )
        doc = Folder().createFolder(
            cohort, 'TCGA-W5-AA2O', parentType='folder',
            public=True, creator=admin
        )
        Folder().createFolder(
            doc, 'sub folder'
        )

        with pytest.raises(ValidationException):
            Case().importDocument(self.tcgaCollection, user=admin)

        with pytest.raises(ValidationException):
            Case().importDocument(doc, user=admin)

        Cohort().importDocument(cohort, user=admin, recurse=True)
        assert Case().findOne({'_id': doc['_id']}).get('_id') == doc['_id']

        with pytest.raises(ValidationException):
            Case().importDocument(invaliddoc, user=admin)

    def testSlideModel(self, server, admin, user):
        makeResources(self, admin, user)

        cohort = Folder().createFolder(
            self.tcgaCollection, 'ucec', parentType='collection',
            public=True, creator=admin
        )
        case = Folder().createFolder(
            cohort, 'TCGA-W5-AA2O', parentType='folder',
            public=True, creator=admin
        )
        doc = Folder().createFolder(
            case, 'TCGA-W5-AA2O-01A-01-TSA', parentType='folder',
            public=True, creator=admin
        )

        with pytest.raises(ValidationException):
            Slide().importDocument(case, user=admin)

        with pytest.raises(ValidationException):
            Slide().importDocument(doc, user=admin)

        Cohort().importDocument(cohort, user=admin, recurse=True)
        assert Slide().findOne({'_id': doc['_id']}).get('_id') == doc['_id']

    def testImageModel(self, server, admin, user):
        makeResources(self, admin, user)

        cohort = Folder().createFolder(
            self.tcgaCollection, 'ucec', parentType='collection',
            public=True, creator=admin
        )
        case = Folder().createFolder(
            cohort, 'TCGA-W5-AA2O', parentType='folder',
            public=True, creator=admin
        )
        slide = Folder().createFolder(
            case, 'TCGA-W5-AA2O-01A-01-TSA', parentType='folder',
            public=True, creator=admin
        )
        invalid = Item().createItem(
            'invalid_name.svs',
            admin, slide
        )
        doc = Item().createItem(
            'TCGA-W5-AA2O-01A-01-TSA.90E7868E-0605-43FD-A4A5-A2C0A6AC3AEE.svs',
            admin, slide
        )
        file = File().createFile(
            admin, doc, doc['name'],
            0, {'_id': ''}
        )
        doc['largeImage'] = {
            'fileId': file['_id'],
            'sourceName': 'svs'
        }
        Item().save(doc)

        with pytest.raises(ValidationException):
            Image().importDocument(doc, user=admin)

        Cohort().importDocument(cohort, user=admin, recurse=True)

        ifile = File().createFile(
            admin, invalid, doc['name'],
            0, {'_id': ''}
        )
        invalid['largeImage'] = {
            'fileId': ifile['_id'],
            'sourceName': 'svs'
        }
        Item().save(invalid)
        with pytest.raises(ValidationException):
            Image().importDocument(invalid, user=admin)

        assert Image().findOne({'_id': doc['_id']}).get('_id') == doc['_id']


@pytest.mark.plugin('digital_slide_archive')
class TestTCGARest(object):
    def runRecursiveImport(self, server, admin):
        # generate the async import task
        resp = server.request(
            path='/tcga/import',
            method='POST',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        job = resp.json

        # loop until it is done
        for i in range(100):
            time.sleep(0.1)

            resp = server.request(
                path='/job/' + job['_id'],
                user=admin
            )
            assert utilities.respStatus(resp) == 200

            status = resp.json['status']
            if status == JobStatus.SUCCESS:
                return
            elif status in (JobStatus.ERROR, JobStatus.CANCELED):
                raise Exception('TCGA import failed')

        raise Exception('TCGA import did not finish in time')

    def testTCGACollection(self, server, admin, user):
        makeResources(self, admin, user)
        resp = server.request(
            path='/tcga'
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json['_id'] == str(self.tcgaCollection['_id'])

        resp = server.request(
            path='/tcga',
            method='DELETE',
            user=user
        )
        assert utilities.respStatus(resp) == 403

        resp = server.request(
            path='/tcga',
            method='DELETE',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga'
        )
        assert utilities.respStatus(resp) == 404

        resp = server.request(
            path='/tcga',
            params={'collectionId': self.tcgaCollection['_id']},
            method='POST'
        )
        assert utilities.respStatus(resp) == 401

        resp = server.request(
            path='/tcga',
            params={'collectionId': self.tcgaCollection['_id']},
            method='POST',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga'
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json['_id'] == str(self.tcgaCollection['_id'])

    def testRecursiveImport(self, server, admin, user):
        makeResources(self, admin, user)
        self.runRecursiveImport(server, admin)
        images = list(Image().find({}))
        assert len(images) == 3

    def testCohortEndpoints(self, server, admin, user):
        makeResources(self, admin, user)
        resp = server.request(
            path='/tcga/cohort'
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json['data'] == []

        resp = server.request(
            path='/tcga/cohort',
            params={'folderId': self.cohort['_id']},
            method='POST'
        )
        assert utilities.respStatus(resp) == 401

        resp = server.request(
            path='/tcga/cohort',
            params={'folderId': self.cohort['_id']},
            method='POST',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga/cohort/' + str(self.cohort['_id'])
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json['name'] == self.cohort['name']

        resp = server.request(
            path='/tcga/cohort/' + str(self.cohort['_id']),
            method='DELETE',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga/cohort'
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json['data'] == []

        # import recursively and test searching for slides
        self.runRecursiveImport(server, admin)
        resp = server.request(
            path='/tcga/cohort/' + str(self.cohort['_id']) + '/slides'
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['data']) == 3

        resp = server.request(
            path='/tcga/cohort/' + str(self.cohort2['_id']) + '/slides'
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['data']) == 1

        resp = server.request(
            path='/tcga/cohort/' + str(self.cohort['_id']) + '/images'
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['data']) == 3
        assert resp.json['data'][0]['tcga']['type'] == 'image'

    def testCaseEndpoints(self, server, admin, user):
        makeResources(self, admin, user)
        self.runRecursiveImport(server, admin)

        resp = server.request(
            path='/tcga/case',
            params={'cohort': str(self.cohort['_id'])}
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['data']) == 3

        resp = server.request(
            path='/tcga/case/' + str(self.case1['_id']),
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json['name'] == self.case1['name']

        # search for images under a case 1
        resp = server.request(
            path='/tcga/case/' + str(self.case1['_id']) + '/images'
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['data']) == 2

        # search for images under a case 2
        resp = server.request(
            path='/tcga/case/' + str(self.case2['_id']) + '/images'
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['data']) == 1

        resp = server.request(
            path='/tcga/case/' + str(self.case1['_id']),
            method='DELETE',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga/case',
            params={'cohort': str(self.cohort['_id'])}
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['data']) == 2

        resp = server.request(
            path='/tcga/case',
            params={'folderId': self.case1['_id']},
            method='POST',
            user=admin
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json['name'] == self.case1['name']

        resp = server.request(
            path='/tcga/case/label/' + self.case2['name']
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json['_id'] == str(self.case2['_id'])

        resp = server.request(
            path='/tcga/case/label/' + 'notalabel'
        )
        assert utilities.respStatus(resp) == 400

    def testCaseMetadata(self, server, admin, user):
        makeResources(self, admin, user)
        id1 = str(self.case1['_id'])
        id2 = str(self.case2['_id'])
        self.runRecursiveImport(server, admin)

        resp = server.request(
            path='/tcga/case/' + id1 + '/metadata/tables'
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json == []

        resp = server.request(
            path='/tcga/case/' + id1 + '/metadata/table1',
            method='POST',
            body=json.dumps({
                'key1': 'value1',
                'key2': 'value2'
            })
        )
        assert utilities.respStatus(resp) == 401

        resp = server.request(
            path='/tcga/case/' + id1 + '/metadata/table1',
            method='POST',
            body=json.dumps({
                'key1': 'value1',
                'key2': 'value2'
            }),
            user=user,
            type='application/json'
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga/case/' + id1 + '/metadata/tables'
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json == ['table1']

        resp = server.request(
            path='/tcga/case/' + id1 + '/metadata/table1',
        )
        assert utilities.respStatus(resp) == 200
        assert set(resp.json.keys()) == {'key1', 'key2'}

        resp = server.request(
            path='/tcga/case/' + id1 + '/metadata/table1',
            method='PUT',
            body=json.dumps({
                'key1': None,
                'key3': 'value3'
            }),
            user=user,
            type='application/json'
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga/case/' + id1 + '/metadata/table1',
        )
        assert utilities.respStatus(resp) == 200
        assert set(resp.json.keys()) == {'key2', 'key3'}

        resp = server.request(
            path='/tcga/case/' + id2 + '/metadata/table1',
            method='POST',
            body=json.dumps({
                'key1': 'value1'
            }),
            user=user,
            type='application/json'
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga/case/search',
            params={'table': 'table1'}
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['data']) == 2

        resp = server.request(
            path='/tcga/case/search',
            params={'table': 'table1', 'key': 'key1'}
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['_id'] == id2

        resp = server.request(
            path='/tcga/case/search',
            params={'table': 'table1', 'key': 'key1', 'value': 'value2'}
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['data']) == 0

        resp = server.request(
            path='/tcga/case/search',
            params={'table': 'table1', 'key': 'key1', 'substring': 'alue'}
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['data']) == 1

        # special characters should be escaped
        resp = server.request(
            path='/tcga/case/search',
            params={'table': 'table1', 'key': 'key1', 'substring': '.*'}
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['data']) == 0

        # querying by substring and value should fail
        resp = server.request(
            path='/tcga/case/search',
            params={
                'table': 'table1',
                'key': 'key1',
                'substring': 'value1',
                'value': 'value1'
            }
        )
        assert utilities.respStatus(resp) == 400

        resp = server.request(
            path='/tcga/case/' + id2 + '/metadata/table1',
            method='DELETE',
            user=user
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga/case/' + id2 + '/metadata/tables'
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json == []

    def testSlideEndpoints(self, server, admin, user):
        makeResources(self, admin, user)
        case1 = str(self.case1['_id'])
        slide1 = str(self.slide1['_id'])
        self.runRecursiveImport(server, admin)

        resp = server.request(
            path='/tcga/slide',
            params={'case': case1}
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['data']) == 2

        resp = server.request(
            path='/tcga/slide/' + slide1
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json['name'] == self.slide1['name']

        resp = server.request(
            path='/tcga/slide/' + slide1,
            method='DELETE',
            user=user
        )
        assert utilities.respStatus(resp) == 403

        resp = server.request(
            path='/tcga/slide/' + slide1,
            method='DELETE',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga/slide/' + slide1
        )
        assert utilities.respStatus(resp) == 400

        resp = server.request(
            path='/tcga/slide',
            params={'folderId': slide1},
            method='POST',
            user=user
        )
        assert utilities.respStatus(resp) == 403

        resp = server.request(
            path='/tcga/slide',
            params={'folderId': slide1},
            method='POST',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga/slide/' + slide1
        )
        assert utilities.respStatus(resp) == 200

    def testImageEndpoints(self, server, admin, user):
        makeResources(self, admin, user)
        slide1 = str(self.slide1['_id'])
        image1 = str(self.image1['_id'])
        self.runRecursiveImport(server, admin)

        resp = server.request(
            path='/tcga/image',
            params={'slide': slide1}
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['data']) == 1
        assert resp.json['data'][0]['tcga'].get('caseId') == str(self.case1['_id'])

        resp = server.request(
            path='/tcga/image',
            params={'caseName': self.case1['name']}
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['data']) == 2

        resp = server.request(
            path='/tcga/image/' + image1
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json['name'] == self.image1['name']

        resp = server.request(
            path='/tcga/image/' + image1,
            method='DELETE',
            user=user
        )
        assert utilities.respStatus(resp) == 403

        resp = server.request(
            path='/tcga/image/' + image1,
            method='DELETE',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga/image/' + image1
        )
        assert utilities.respStatus(resp) == 400

        resp = server.request(
            path='/tcga/image',
            params={'itemId': image1},
            method='POST',
            user=user
        )
        assert utilities.respStatus(resp) == 403

        resp = server.request(
            path='/tcga/image',
            params={'itemId': image1},
            method='POST',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga/image/' + image1
        )
        assert utilities.respStatus(resp) == 200

    def testPathologyEndpoints(self, server, admin, user):
        makeResources(self, admin, user)
        case1 = str(self.case1['_id'])
        pathology1 = str(self.pathology1['_id'])
        self.runRecursiveImport(server, admin)

        resp = server.request(
            path='/tcga/pathology',
            params={'id': pathology1},
            method='POST',
            user=user
        )
        assert utilities.respStatus(resp) == 403

        resp = server.request(
            path='/tcga/pathology',
            params={'id': pathology1},
            method='POST',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga/pathology',
            params={'case': case1}
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['data']) == 1
        assert str(resp.json['data'][0]['file']['_id']) == str(self.pathology_file1['_id'])
        assert str(resp.json['data'][0]['file']['mimeType']) == 'application/pdf'

        resp = server.request(
            path='/tcga/pathology/' + pathology1
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json['name'] == self.pathology1['name']
        assert str(resp.json['file']['_id']) == str(self.pathology_file1['_id'])

        resp = server.request(
            path='/tcga/pathology/' + pathology1,
            method='DELETE',
            user=user
        )
        assert utilities.respStatus(resp) == 403

        resp = server.request(
            path='/tcga/pathology/' + pathology1,
            method='DELETE',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga/pathology/' + pathology1
        )
        assert utilities.respStatus(resp) == 400

        resp = server.request(
            path='/tcga/pathology',
            params={'itemId': pathology1},
            method='POST',
            user=user
        )
        assert utilities.respStatus(resp) == 403

        resp = server.request(
            path='/tcga/pathology',
            params={'id': pathology1},
            method='POST',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga/pathology/' + pathology1
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga/pathology',
            params={'id': str(self.pathologyFolder['_id']), 'recursive': True},
            method='POST',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/tcga/pathology/' + str(self.pathology2['_id'])
        )
        assert utilities.respStatus(resp) == 200

    def testAperioEndpoints(self, server, admin, user):
        makeResources(self, admin, user)
        aperio1 = str(self.aperio1['_id'])
        aperio2 = str(self.aperio2['_id'])
        image = str(self.image2['_id'])
        self.runRecursiveImport(server, admin)

        # test access control
        resp = server.request(
            path='/tcga/aperio',
            params={'id': aperio1},
            method='POST',
            user=user
        )
        assert utilities.respStatus(resp) == 403

        # test automatic import of tcga items
        resp = server.request(
            path='/tcga/aperio',
            params={'id': aperio1},
            method='POST',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/item/' + image + '/aperio'
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json) == 1
        assert str(resp.json[0]['_id']) == str(self.aperio1['_id'])
        assert str(resp.json[0]['file']['_id']) == str(self.aperio_file1['_id'])
        assert str(resp.json[0]['file']['mimeType']) == 'application/xml'

        # test filtering by tag
        resp = server.request(
            path='/item/' + image + '/aperio',
            params={'tag': 'foo'}
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json) == 0

        # test writing a new tag
        resp = server.request(
            path='/item/' + aperio1 + '/aperio',
            params={'tag': 'foo'},
            method='PUT',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/item/' + image + '/aperio',
            params={'tag': 'foo'}
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json) == 1

        # test importing an annotation manually
        resp = server.request(
            path='/item/' + aperio2 + '/aperio',
            params={'tag': 'bar', 'imageId': image},
            method='POST',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/item/' + image + '/aperio',
            params={'tag': 'bar'}
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json) == 1
        assert resp.json[0]['_id'] == aperio2

        # test deleting an annotation
        resp = server.request(
            path='/item/' + aperio2 + '/aperio',
            method='DELETE',
            user=admin
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request(
            path='/item/' + image + '/aperio',
            params={'tag': 'bar'}
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json) == 0

    def testPagingParams(self, server, admin, user):
        makeResources(self, admin, user)
        cohort1 = str(self.cohort['_id'])
        self.runRecursiveImport(server, admin)

        resp = server.request(
            path='/tcga/case',
            params={'cohort': cohort1, 'limit': 2, 'offset': 0}
        )
        assert utilities.respStatus(resp) == 200
        data = resp.json

        assert data['pos'] == 0
        assert data['limit'] == 2
        assert data['total_count'] == 3
        assert data['current_page'] == 0
        assert data['total_pages'] == 2

        resp = server.request(
            path='/tcga/case',
            params={'cohort': cohort1, 'limit': 2, 'offset': 2}
        )
        assert utilities.respStatus(resp) == 200
        data = resp.json

        assert data['pos'] == 2
        assert data['limit'] == 2
        assert data['total_count'] == 3
        assert data['current_page'] == 1
        assert data['total_pages'] == 2

        resp = server.request(
            path='/tcga/case',
            params={'cohort': cohort1, 'limit': 2, 'offset': 1}
        )
        assert utilities.respStatus(resp) == 200
        data = resp.json

        assert data['pos'] == 1
        assert data['limit'] == 2
        assert data['total_count'] == 3
        assert data['current_page'] == 0
        assert data['total_pages'] == 2
