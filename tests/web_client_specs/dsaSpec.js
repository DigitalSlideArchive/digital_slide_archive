/* globals girder, girderTest, describe, it, expect, waitsFor, runs */

girderTest.importPlugin('jobs', 'worker', 'large_image', 'large_image_annotation', 'slicer_cli_web', 'digital_slide_archive');

girderTest.startApp();

describe('Test the Digital Slide Archive plugin', function () {
    it('change the Digital Slide Archive settings', function () {
        var styles = [{'lineWidth': 8, 'id': 'Sample Group'}];
        var styleJSON = JSON.stringify(styles);

        girderTest.login('admin', 'Admin', 'Admin', 'password')();
        waitsFor(function () {
            return $('a.g-nav-link[g-target="admin"]').length > 0;
        }, 'admin console link to load');
        runs(function () {
            $('a.g-nav-link[g-target="admin"]').click();
        });
        waitsFor(function () {
            return $('.g-plugins-config').length > 0;
        }, 'the admin console to load');
        runs(function () {
            $('.g-plugins-config').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-plugin-config-link').length > 0;
        }, 'the plugins page to load');
        runs(function () {
            expect($('.g-plugin-config-link[g-route="plugins/digital_slide_archive/config"]').length > 0);
            $('.g-plugin-config-link[g-route="plugins/digital_slide_archive/config"]').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('#g-dsa-form input').length > 0;
        }, 'settings to be shown');
        runs(function () {
            $('#g-dsa-default-draw-styles').val(styleJSON);
            $('.g-dsa-buttons .btn-primary').click();
        });
        waitsFor(function () {
            var resp = girder.rest.restRequest({
                url: 'system/setting',
                method: 'GET',
                data: {
                    list: JSON.stringify([
                        'digital_slide_archive.default_draw_styles'
                    ])
                },
                async: false
            });
            var settings = resp.responseJSON;
            var settingsStyles = settings && JSON.parse(settings['digital_slide_archive.default_draw_styles']);
            return (settingsStyles && settingsStyles.length === 1 &&
                    settingsStyles[0].lineWidth === styles[0].lineWidth);
        }, 'Digital Slide Archive settings to change');
        girderTest.waitForLoad();
        runs(function () {
            $('#g-dsa-default-draw-styles').val('not a json list');
            $('.g-dsa-buttons .btn-primary').click();
        });
        waitsFor(function () {
            return $('#g-dsa-error-message').text().substr('must be a JSON list') >= 0;
        });
        runs(function () {
            $('#g-dsa-brand-color').val('#ffffff');
            $('#g-dsa-brand-default-color').click();
            expect($('#g-dsa-brand-color').val() === '#777777');
            $('#g-dsa-banner-color').val('#ffffff');
            $('#g-dsa-banner-default-color').click();
            expect($('#g-dsa-banner-color').val() === '#f8f8f8');
        });
        /* test the quarantine folder */
        runs(function () {
            $('.g-open-browser').click();
        });
        girderTest.waitForDialog();
        runs(function () {
            $('#g-root-selector').val($('#g-root-selector')[0].options[1].value).trigger('change');
        });
        waitsFor(function () {
            return $('.g-folder-list-link').length >= 2;
        });
        runs(function () {
            $('.g-folder-list-link').click();
        });
        waitsFor(function () {
            return $('#g-selected-model').val() !== '';
        });
        runs(function () {
            $('.g-submit-button').click();
        });
        girderTest.waitForLoad();
        /* Cancel the changes */
        runs(function () {
            $('.g-dsa-buttons #g-dsa-cancel').click();
        });
        waitsFor(function () {
            return $('.g-plugin-config-link').length > 0;
        }, 'the plugins page to load');
        girderTest.waitForLoad();
    });
});
