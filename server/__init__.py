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

from bson import json_util
import json

from girder.constants import SettingKey
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.setting import Setting

from . import rest


originalChildItems = None


def childItems(self, folder, limit=0, offset=0, sort=None, filters=None,
               includeVirtual=False, **kwargs):
    if not includeVirtual or not folder.get('isVirtual') or 'virtualItemsQuery' not in folder:
        return originalChildItems(self, folder, limit=limit, offset=offset,
                                  sort=sort, filters=filters, **kwargs)
    q = json_util.loads(folder['virtualItemsQuery'])
    if 'virtualItemsSort' in folder and sort is None:
        sort = json.loads(folder['virtualItemsSort'])
    q.update(filters or {})
    return Item().find(q, limit=limit, offset=offset, sort=sort, **kwargs)


def load(info):
    rest.addEndpoints(info['apiRoot'])
    info['serverRoot'].updateHtmlVars({
        'brandName': Setting().get(SettingKey.BRAND_NAME)})
    global originalChildItems
    if Folder.childItems != childItems:
        originalChildItems = Folder.childItems
        Folder.childItems = childItems
