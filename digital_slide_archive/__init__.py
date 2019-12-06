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
import re

from bson import json_util
from girder import events
from girder import plugin
from girder.api import access
from girder.exceptions import ValidationException
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.setting import Setting
from girder.settings import SettingDefault, SettingKey
from girder.utility import config, setting_utilities
from girder.utility.model_importer import ModelImporter
from girder.utility.webroot import Webroot
from pkg_resources import DistributionNotFound, get_distribution

from . import rest
from .constants import PluginSettings
from .handlers import process_annotations
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


_template = os.path.join(
    os.path.dirname(__file__),
    'webroot.mako'
)


@setting_utilities.validator({
    PluginSettings.DSA_DEFAULT_DRAW_STYLES
})
def validateListOrJSON(doc):
    val = doc['value']
    try:
        if isinstance(val, list):
            doc['value'] = json.dumps(val)
        elif val is None or val.strip() == '':
            doc['value'] = None
        else:
            parsed = json.loads(val)
            if not isinstance(parsed, list):
                raise ValueError
            doc['value'] = val.strip()
    except (ValueError, AttributeError):
        raise ValidationException('%s must be a JSON list.' % doc['key'], 'value')


@setting_utilities.validator({
    PluginSettings.DSA_BANNER_COLOR,
    PluginSettings.DSA_BRAND_COLOR,
})
def validateDigitalSlideArchiveColor(doc):
    if not doc['value']:
        raise ValidationException('The banner color may not be empty', 'value')
    elif not re.match(r'^#[0-9A-Fa-f]{6}$', doc['value']):
        raise ValidationException('The banner color must be a hex color triplet', 'value')


@setting_utilities.validator(PluginSettings.DSA_BRAND_NAME)
def validateDigitalSlideArchiveBrandName(doc):
    if not doc['value']:
        raise ValidationException('The brand name may not be empty', 'value')


@setting_utilities.validator(PluginSettings.DSA_WEBROOT_PATH)
def validateDigitalSlideArchiveWebrootPath(doc):
    if not doc['value']:
        raise ValidationException('The webroot path may not be empty', 'value')
    if re.match(r'^girder$', doc['value']):
        raise ValidationException('The webroot path may not be "girder"', 'value')


@setting_utilities.validator(PluginSettings.DSA_QUARANTINE_FOLDER)
def validateDigitalSlideArchiveQuarantineFolder(doc):
    if not doc.get('value', None):
        doc['value'] = None
    else:
        Folder().load(doc['value'], force=True, exc=True)


# Defaults that have fixed values are added to the system defaults dictionary.
SettingDefault.defaults.update({
    PluginSettings.DSA_WEBROOT_PATH: 'dsa',
    PluginSettings.DSA_BRAND_NAME: 'Digital Slide Archive',
    PluginSettings.DSA_BANNER_COLOR: '#f8f8f8',
    PluginSettings.DSA_BRAND_COLOR: '#777777',
})


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


def _saveJob(event):
    """
    When a job is saved, if it is a docker run task, add the Dask Bokeh port to
    the list of exposed ports.
    """
    job = event.info
    try:
        jobkwargs = json_util.loads(job['kwargs'])
        if '--scheduler' in jobkwargs['container_args']:
            jobkwargs['ports'] = {'8787': None}
            job['kwargs'] = json_util.dumps(jobkwargs)
    except Exception:
        pass


class WebrootDigitalSlideArchive(Webroot):
    def _renderHTML(self):
        self.updateHtmlVars({
            'title': Setting().get(PluginSettings.DSA_BRAND_NAME),
            'dsaBrandName': Setting().get(PluginSettings.DSA_BRAND_NAME),
            'dsaBrandColor': Setting().get(PluginSettings.DSA_BRAND_COLOR),
            'dsaBannerColor': Setting().get(PluginSettings.DSA_BANNER_COLOR),
        })
        return super(WebrootDigitalSlideArchive, self)._renderHTML()


class GirderPlugin(plugin.GirderPlugin):
    DISPLAY_NAME = 'Digital Slide Archive'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        plugin.getPlugin('jobs').load(info)
        plugin.getPlugin('slicer_cli_web').load(info)
        plugin.getPlugin('large_image_annotation').load(info)

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

        girderRoot = info['serverRoot']
        dsaRoot = WebrootDigitalSlideArchive(_template)
        dsaRoot.updateHtmlVars(girderRoot.vars)

        # The interface is always available under dsa and also available
        # under the specified path.
        info['serverRoot'].dsa = dsaRoot
        webrootPath = Setting().get(PluginSettings.DSA_WEBROOT_PATH)
        setattr(info['serverRoot'], webrootPath, dsaRoot)
        info['serverRoot'].girder = girderRoot

        # auto-ingest annotations into database when a .anot file is uploaded
        events.bind('data.process', 'digital_slide_archive', process_annotations)

        events.bind('model.job.save', 'digital_slide_archive', _saveJob)

        def updateWebroot(event):
            """
            If the webroot path setting is changed, bind the new path to the
            dsa webroot resource.
            """
            if event.info.get('key') == PluginSettings.DSA_WEBROOT_PATH:
                setattr(info['serverRoot'], event.info['value'], dsaRoot)

        events.bind('model.setting.save.after', 'digital_slide_archive', updateWebroot)

        curConfig = config.getConfig().get('digital_slide_archive', {})
        if curConfig.get('restrict_downloads'):
            # Change some endpoints to require token access
            endpoints = [
                ('collection', 'GET', (':id', 'download')),
                ('file', 'GET', (':id', 'download')),
                ('file', 'GET', (':id', 'download', ':name')),
                ('folder', 'GET', (':id', 'download')),
                ('item', 'GET', (':id', 'download')),
                ('resource', 'GET', ('download', )),
                ('resource', 'POST', ('download', )),

                ('item', 'GET', (':itemId', 'tiles', 'images', ':image')),
            ]

            for resource, method, route in endpoints:
                cls = getattr(info['apiRoot'], resource)
                func = cls.getRouteHandler(method, route)
                if func.accessLevel == 'public':
                    func = access.token(func)
                    cls.removeRoute(method, route)
                    cls.route(method, route, func)
