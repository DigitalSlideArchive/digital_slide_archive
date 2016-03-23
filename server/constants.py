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

from girder.models.model_base import ValidationException
from girder.constants import SettingDefault
import six


class PluginSettings(object):
    BRAND_NAME = 'digital_slide_archive.brand_name'


def validateSettings(event):
    key, val = event.info['key'], event.info['value']

    if key == PluginSettings.BRAND_NAME:
        if not isinstance(val, six.string_types):
            raise ValidationException(
                'Brand name must be provided as a string.', 'value')
        event.preventDefault().stopPropagation()


SettingDefault.defaults[PluginSettings.BRAND_NAME] = 'Digital Slide Archive'
