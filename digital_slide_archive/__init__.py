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

from bson import json_util
from girder import plugin
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.setting import Setting
from girder.settings import SettingKey
from girder.utility.model_importer import ModelImporter
from pkg_resources import DistributionNotFound, get_distribution

from . import rest
from .models.aperio import Aperio
from .models.case import Case
from .models.cohort import Cohort
from .models.image import Image
from .models.pathology import Pathology
from .models.slide import Slide


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


def childItems(self, folder, limit=0, offset=0, sort=None, filters=None,
               includeVirtual=False, **kwargs):
    if not includeVirtual or not folder.get('isVirtual') or 'virtualItemsQuery' not in folder:
        return Folder._childItemsBeforeDSA(
            self, folder, limit=limit, offset=offset, sort=sort,
            filters=filters, **kwargs)
    q = json_util.loads(folder['virtualItemsQuery'])
    if 'virtualItemsSort' in folder and sort is None:
        sort = json.loads(folder['virtualItemsSort'])
    q.update(filters or {})
    return Item().find(q, limit=limit, offset=offset, sort=sort, **kwargs)


class GirderPlugin(plugin.GirderPlugin):
    DISPLAY_NAME = 'Digital Slide Archive'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        plugin.getPlugin('jobs').load(info)
        plugin.getPlugin('slicer_cli_web').load(info)

        ModelImporter.registerModel('aperio', Aperio, 'digital_slide_archive')
        ModelImporter.registerModel('case', Case, 'digital_slide_archive')
        ModelImporter.registerModel('cohort', Cohort, 'digital_slide_archive')
        ModelImporter.registerModel('image', Image, 'digital_slide_archive')
        ModelImporter.registerModel('pathology', Pathology, 'digital_slide_archive')
        ModelImporter.registerModel('slide', Slide, 'digital_slide_archive')

        rest.addEndpoints(info['apiRoot'])
        info['serverRoot'].updateHtmlVars({
            'brandName': Setting().get(SettingKey.BRAND_NAME)})
        global originalChildItems
        if not getattr(Folder, '_childItemsBeforeDSA', None):
            Folder._childItemsBeforeDSA = Folder.childItems
            Folder.childItems = childItems
