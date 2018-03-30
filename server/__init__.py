#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
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
###############################################################################

from girder import events
from girder.api import access
from girder.api.rest import boundHandler
from girder.constants import SettingKey
from girder.models.setting import Setting

from . import rest


@access.public
@boundHandler
def _virtualChildItems(self, event):
    params = event.info['params']

    if params['type'] != 'folder':
        return  # This can't be a virtual folder
    try:
        import girder.plugins.virtual_folders
    except ImportError:
        return  # If virtual folders aren't enabled, do nothing
    params['folderId'] = event.info['id']
    return girder.plugins.virtual_folders._virtualChildItems(event)


def load(info):
    rest.addEndpoints(info['apiRoot'])
    info['serverRoot'].updateHtmlVars({
        'brandName': Setting().get(SettingKey.BRAND_NAME)})
    events.bind('rest.get.resource/:id/items.before', info['name'], _virtualChildItems)
