/* global dsaTest */

/* global dsaTest */

girderTest.importPlugin('jobs', 'worker', 'large_image', 'large_image_annotation', 'slicer_cli_web', 'digital_slide_archive');
girderTest.addScript('/static/built/plugins/digital_slide_archive/dsaTest.js');

girderTest.promise.done(function () {
    dsaTest.startApp();

    var restRequest;
    beforeEach(function () {
        // Replace girder's rest request method with one that calls
        // our mocked docker_image endpoint in place of the real one.
        restRequest = girder.rest.restRequest;
        girder.rest.restRequest = function (opts) {
            if (opts.url === 'slicer_cli_web/docker_image') {
                opts.url = 'mock_resource/docker_image';
            }
            return restRequest.call(this, opts);
        };
    });
    afterEach(function () {
        girder.rest.restRequest = restRequest;
    });
    describe('setup', function () {
        it('login', function () {
            dsaTest.login();
        });

        it('open image', function () {
            dsaTest.openImage('image');
            waitsFor(function () {
                return $('.h-analysis-item').length > 0;
            }, 'analyses dropdown to load');
        });
    });

    describe('open analysis', function () {
        var regionValue;

        it('get dropdown values', function () {
            var $el = $('.h-analyses-dropdown');
            expect($el.find('a:contains("dsarchive/histomicstk")').length).toBe(1);

            $el = $el.find('.dropdown-submenu:first');
            expect($el.find('a:contains("latest")').length).toBe(1);

            $el = $el.find('.dropdown-menu:first');
            var link = $el.find('a:contains("NucleiDetection")');
            expect(link.length).toBe(1);

            link.click();
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('.h-control-panel-container .s-panel').length;
            }, 'panels to load');

            runs(function () {
                var $panel = $('.h-control-panel-container .s-panel:first');
                expect($panel.find('.s-panel-title-container').text()).toBe('Detects Nuclei');
            });
        });
        it('check autofilled forms', function () {
            waitsFor(function () {
                return !!$('#inputImageFile').val();
            }, 'Input image to auto fill');
            runs(function () {
                expect($('#inputImageFile').val()).toBe('image');
            });

            waitsFor(function () {
                return !!$('#outputNucleiAnnotationFile').val();
            }, 'Output annotation file to auto fill');

            runs(function () {
                expect($('#outputNucleiAnnotationFile').val()).toBe(
                    'Detects Nuclei-outputNucleiAnnotationFile.anot'
                );
            });
        });
        it('draw a region of interest', function () {
            var regionButton = $('.s-select-region-button');
            var interactor = dsaTest.geojsMap().interactor();

            expect(regionButton.length).toBe(1);
            regionButton.click();

            interactor.simulateEvent('mousedown', {
                map: {x: 100, y: 100},
                button: 'left'
            });
            interactor.simulateEvent('mousemove', {
                map: {x: 200, y: 200},
                button: 'left'
            });
            interactor.simulateEvent('mouseup', {
                map: {x: 200, y: 200},
                button: 'left'
            });

            waitsFor(function () {
                return $('#analysis_roi').val() !== '-1,-1,-1,-1';
            }, 'roi widget to update');
            runs(function () {
                regionValue = $('#analysis_roi').val();
            });
        });
        it('submit the job', function () {
            var options;

            girder.events.once('g:alert', function (_options) {
                options = _options;
            });
            var $el = $('.s-info-panel-submit');
            expect($el.length).toBe(1);
            $el.click();

            waitsFor(function () {
                return options !== undefined;
            }, 'job submission to return');
            runs(function () {
                expect(options.text).toBe('Analysis job submitted.');
                expect($('.s-jobs-panel .s-panel-controls .icon-up-open').length).toBe(1);
            });
        });
        it('open a new analysis', function () {
            var $el = $('.h-analyses-dropdown');
            expect($el.find('a:contains("dsarchive/histomicstk")').length).toBe(1);

            $el = $el.find('.dropdown-submenu:first');
            expect($el.find('a:contains("latest")').length).toBe(1);

            var link = $el.find('a:contains("ComputeNucleiFeatures")');
            expect(link.length).toBe(1);

            link.click();
            girderTest.waitForLoad();

            waitsFor(function () {
                var $panel = $('.h-control-panel-container .s-panel:first');
                return $panel.find('.s-panel-title-container').text() === 'Computes Nuclei Features';
            }, 'new analysis to load');
        });
        it('assert roi is preserved', function () {
            expect($('#analysis_roi').val()).toEqual(regionValue);
        });
        it('assert roi resets on analysis change', function () {
            var resetCalled;
            dsaTest.app.bodyView.viewerWidget.on('g:mouseResetAnnotation', function (annotation) {
                if (annotation.id === 'region-selection') {
                    resetCalled = true;
                }
            });
            dsaTest.app.bodyView.controlPanel.reset();
            girder.plugins.digital_slide_archive.events.trigger('h:analysis', null);
            waitsFor(function () {
                return resetCalled;
            }, 'region annotation to be removed');
        });
    });
    describe('close analysis', function () {
        it('open analysis', function () {
            var $el = $('.h-analyses-dropdown');
            var link = $el.find('a:contains("NucleiDetection")');
            link.click();
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('.h-control-panel-container .s-panel').length;
            }, 'panels to load');
        });
        it('click close', function () {
            expect($('.s-close-panel-group:visible').length).toBe(1);
            $('.s-close-panel-group:visible').click();
            expect($('.s-close-panel-group:visible').length).toBe(0);
        });
    });
});
