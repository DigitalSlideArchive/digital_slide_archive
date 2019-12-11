girderTest.importPlugin('jobs', 'worker', 'large_image', 'large_image_annotation', 'slicer_cli_web', 'digital_slide_archive');

girderTest.startApp();

describe('itemList', function () {
    it('mock Webgl', function () {
        var GeojsViewer = window.girder.plugins.large_image.views.imageViewerWidget.geojs;
        window.girder.utilities.PluginUtils.wrap(GeojsViewer, 'initialize', function (initialize) {
            this.once('g:beforeFirstRender', function () {
                window.geo.util.mockWebglRenderer();
            });
            initialize.apply(this, _.rest(arguments));
        });
    });
    it('login', function () {
        girderTest.login('admin', 'Admin', 'Admin', 'password')();
    });
    it('go to first public user item', function () {
        runs(function () {
            $("a.g-nav-link[g-target='users']").click();
        });
        waitsFor(function () {
            return $('a.g-user-link').length > 0;
        });
        runs(function () {
            $('a.g-user-link').last().click();
        });
        waitsFor(function () {
            return $('a.g-folder-list-link').length > 0;
        });
        runs(function () {
            $('.g-folder-list-link:contains("Public")').click();
        });
        waitsFor(function () {
            return $('a.g-item-list-link:contains("image")').length > 0;
        });
        runs(function () {
            $('a.g-item-list-link:contains("image")').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-item-actions-button').length > 0;
        });
        runs(function () {
            $('.g-item-actions-button').parent().addClass('group');
        });
    });
    it('has a Open Digital Slide Archive button', function () {
        runs(function () {
            expect($('.g-dsa-open-item').length).toBe(1);
        });
    });
    it('has in Quarantine Item button', function () {
        runs(function () {
            expect($('.g-dsa-quarantine-item').length).toBe(1);
        });
    });
});
