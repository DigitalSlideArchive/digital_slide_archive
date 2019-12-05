# -*- coding: utf-8 -*-

import pytest

from girder.models.folder import Folder
from girder.models.item import Item

from . import girder_utilities as utilities


@pytest.mark.plugin('digital_slide_archive')
class TestImageBrowseEndpoints(object):
    def makeResources(self, admin):
        self.folder = list(Folder().childFolders(admin, 'user', user=admin))[0]
        self.items = [
            Item().createItem('item_%i' % i, creator=admin, folder=self.folder)
            for i in range(10)
        ]
        for item in self.items:
            # make the item look like an image
            item['largeImage'] = {
                'fileId': 'deadbeef'
            }
            Item().save(item)
        self.nonimage = Item().createItem('non-image', creator=admin, folder=self.folder)
        self.extraFolder = Folder().createFolder(self.folder, 'extra', creator=admin)

    def testGetNextImage(self, server, admin):
        self.makeResources(admin)
        resp = server.request(
            path='/item/%s/next_image' % str(self.items[0]['_id']), user=admin)
        assert utilities.respStatus(resp) == 200
        assert resp.json['_id'] == str(self.items[1]['_id'])

        resp = server.request(
            path='/item/%s/next_image' % str(self.items[-1]['_id']), user=admin)
        assert utilities.respStatus(resp) == 200
        assert resp.json['_id'] == str(self.items[0]['_id'])

    def testGetPreviousImage(self, server, admin):
        self.makeResources(admin)
        resp = server.request(
            path='/item/%s/previous_image' % str(self.items[0]['_id']), user=admin)
        assert utilities.respStatus(resp) == 200
        assert resp.json['_id'] == str(self.items[-1]['_id'])

        resp = server.request(
            path='/item/%s/previous_image' % str(self.items[-1]['_id']), user=admin)
        assert utilities.respStatus(resp) == 200
        assert resp.json['_id'] == str(self.items[-2]['_id'])

    def testGetNextImageException(self, server, admin):
        self.makeResources(admin)
        resp = server.request(
            path='/item/%s/next_image' % str(self.nonimage['_id']), user=admin)
        assert utilities.respStatus(resp) == 404

    def testGetNextImageFolder(self, server, admin):
        self.makeResources(admin)
        folderId = str(self.folder['_id'])
        resp = server.request(
            path='/item/%s/next_image' % str(self.items[0]['_id']),
            user=admin, params=dict(folderId=folderId))
        assert utilities.respStatus(resp) == 200
        assert resp.json['_id'] == str(self.items[1]['_id'])

        resp = server.request(
            path='/item/%s/next_image' % str(self.items[-1]['_id']),
            user=admin, params=dict(folderId=folderId))
        assert utilities.respStatus(resp) == 200
        assert resp.json['_id'] == str(self.items[0]['_id'])

    def testGetPreviousImageFolder(self, server, admin):
        self.makeResources(admin)
        folderId = str(self.folder['_id'])
        resp = server.request(
            path='/item/%s/previous_image' % str(self.items[0]['_id']),
            user=admin, params=dict(folderId=folderId))
        assert utilities.respStatus(resp) == 200
        assert resp.json['_id'] == str(self.items[-1]['_id'])

        resp = server.request(
            path='/item/%s/previous_image' % str(self.items[-1]['_id']),
            user=admin, params=dict(folderId=folderId))
        assert utilities.respStatus(resp) == 200
        assert resp.json['_id'] == str(self.items[-2]['_id'])

    def testGetNextImageExceptionFolder(self, server, admin):
        self.makeResources(admin)
        resp = server.request(
            path='/item/%s/next_image' % str(self.items[0]['_id']),
            user=admin, params=dict(folderId=self.extraFolder['_id']))
        assert utilities.respStatus(resp) == 404
