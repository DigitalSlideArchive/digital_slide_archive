# -*- coding: utf-8 -*-

from girder.settings import SettingDefault, SettingKey

TCGACollectionSettingKey = 'tcga.tcga_collection_id'

SettingDefault.defaults[SettingKey.BRAND_NAME] = 'Digital Slide Archive'


# Constants representing the setting keys for this plugin
class PluginSettings(object):
    DSA_DEFAULT_DRAW_STYLES = 'digital_slide_archive.default_draw_styles'
    DSA_WEBROOT_PATH = 'digital_slide_archive.webroot_path'
    DSA_BRAND_NAME = 'digital_slide_archive.brand_name'
    DSA_BRAND_COLOR = 'digital_slide_archive.brand_color'
    DSA_BANNER_COLOR = 'digital_slide_archive.banner_color'
    DSA_QUARANTINE_FOLDER = 'digital_slide_archive.quarantine_folder'
