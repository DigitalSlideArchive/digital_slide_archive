import pytest

from girder.plugin import loadedPlugins


@pytest.mark.plugin('digital_slide_archive')
def test_import(server):
    assert 'digital_slide_archive' in loadedPlugins()
