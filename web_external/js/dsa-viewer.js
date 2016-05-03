$(function () {
    'use strict';

    // set to a girder api address
    // (CORS must be enabled when not local)
    var api = 'https://girder.neuro.emory.edu/api/v1';

    // load all of a paged resource
    function load_all(path, params, select) {
        var limit = 50, offset = 0, all = [];

        function progress(data) {
            data.forEach(function (model) {
                $('<option/>')
                    .attr('value', model._id)
                    .text(model.name)
                    .appendTo(select);
            });
        }

        function fetch() {
            params.limit = limit;
            params.offset = offset;
            return $.ajax({
                url: api + path,
                data: params
            }).then(function (data) {
                progress(data);
                Array.prototype.push.apply(all, data);
                if (data.length === limit) {
                    offset += limit;
                    return fetch();
                }
                return all;
            }, function () {
                select.parent().addClass('has-error');
                select.find('option').text('Load failed!');
            });
        };

        select.attr('disabled', false);
        return fetch();
    }

    function load_collections() {
        var placeholder = $('<option disabled selected hidden/>')
            .text('Loading collections...');
        var select = $('#dsa-select-collection').empty().append(placeholder);

        return load_all('/collection', {}, select)
            .then(function () {
                placeholder.text('Select a collection...');
            });
    }

    function load_tumors(collection) {
        var placeholder = $('<option disabled selected hidden/>')
            .text('Loading tumors...');
        var select = $('#dsa-select-tumor').empty().append(placeholder);
        var params = {
            parentType: 'collection',
            parentId: collection
        };

        return load_all('/folder', params, select)
            .then(function () {
                placeholder.text('Select a tumor...');
            });
    }

    function load_patients(folder) {
        var placeholder = $('<option disabled selected hidden/>')
            .text('Loading tumors...');
        var select = $('#dsa-select-patient').empty().append(placeholder);
        var params = {
            parentType: 'folder',
            parentId: folder
        };

        return load_all('/folder', params, select)
            .then(function () {
                placeholder.text('Select a patient...');
            });
    }

    // populate a datatables instance with the slides in the
    // chosen folder
    function load_slides(folder, page) {
        page = page || 0;

        // number of slides to show on a page... could be configurable
        var limit = 5;

        var offset = limit * page;
        var node = $('.dsa-slide-list');

        node.find('.dsa-slide-page').remove();

        var $page = $('<div class="dsa-slide-page"/>');
        node.find('.pager').before($page);

        var previous = node.find('.pager > .previous').addClass('hidden').off('click');
        var next = node.find('.pager > .next').addClass('hidden').off('click');

        $('.dsa-slide-list').removeClass('hidden')
            .data('dsa-slide-page', page);

        // get a thumbnail image for the given item
        function thumbnail(item) {
            var el = document.createElement('img');
            el.src = api + '/item/' + item + '/tiles/thumbnail?width=250';
            return el;
        }

        return $.ajax({
            url: api + '/item',
            data: {
                folderId: folder,
                limit: limit,
                offset: offset
            }
        }).then(function (slides) {
            var $el = $('<div/>').addClass('list-group')
                .appendTo($page);

            // enable pagination buttons
            if (page > 0) {
                previous.removeClass('hidden');
                previous.click(function () {
                        load_slides(folder, page - 1);
                    });
            }

            if (slides.length === limit) {
                next.removeClass('hidden');
                next.click(function () {
                        load_slides(folder, page + 1);
                    });
            }

            // add elements for each slide returned
            slides.forEach(function (slide) {
                var link = $('<a/>').addClass('dsa-select-slide')
                    .addClass('list-group-item')
                    .attr('href', '#')
                    .data('dsa-slide-id', slide._id);

                var h4 = $('<h4/>').text(slide.name);
                link.append(thumbnail(slide._id)).append(h4).appendTo($page);
            });
        });
        
    }

    // add event handlers to select boxes
    $('#dsa-select-collection').change(function () {
        load_tumors($('#dsa-select-collection').val());
    });

    $('#dsa-select-tumor').change(function () {
        load_patients($('#dsa-select-tumor').val());
    });

    $('#dsa-select-patient').change(function () {
        load_slides($('#dsa-select-patient').val());
    });

    $('.dsa-slide-list').delegate('.dsa-select-slide', 'click', function (evt) {
        var $el = $(evt.currentTarget);
        if ($el.hasClass('selected')) {
            return;
        }
        $('.dsa-select-slide').removeClass('selected');
        $el.addClass('selected');
    });

    // finally load the collection list from the server
    load_collections();
});
