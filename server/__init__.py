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
from girder.utility.model_importer import ModelImporter
from girder.utility import webroot

from . import constants
from . import rest


def setBranding(info):
    brandName = ModelImporter.model('setting').get(
        constants.PluginSettings.BRAND_NAME)
    if brandName is None or brandName.strip() == '':
        brandName = ModelImporter.model('setting').getDefault(
            constants.PluginSettings.BRAND_NAME)

    info['serverRoot'].updateHtmlVars({'title': brandName})

    oldinit = webroot.Webroot.__init__

    def newinit(self, templatePath=None):
        oldinit(self, templatePath)
        self.vars['title'] = brandName

    webroot.Webroot.__init__ = newinit


def load(info):
    events.bind('model.setting.validate',
                'digital_slide_archive', constants.validateSettings)

    setBranding(info)

    rest.addEndpoints(info['apiRoot'])
