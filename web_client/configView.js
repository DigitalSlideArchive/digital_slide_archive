import _ from 'underscore';

import View from 'girder/views/View';
import events from 'girder/events';
import router from 'girder/router';
import { confirm } from 'girder/dialog';
import { restRequest } from 'girder/rest';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';
import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';

import dsaConfigTemplate from './templates/digitalSlideArchiveConfig.pug';

/**
 * Show the Digital Slide Archive config settings.  This includes the TCGA
 * Ingest settings (which is really an ingest control).
 */
var ConfigView = View.extend({
    events: {
        'submit #g-tcga-ingest-form': function (event) {
            event.preventDefault();

            var dataset = this.$('#g-tcga-ingest-datasource').val(),
                assetstoreId = this.$('#g-tcga-ingest-assetstore-id').val().trim(),
                limit = this.$('#g-tcga-ingest-amount').val();
            this.$('#g-tcga-ingest-error-message').empty();
            var callback = _.bind(function () {
                this._ingest({
                    dataset: dataset,
                    assetstoreId: assetstoreId,
                    limit: limit
                });
            }, this);
            if (limit === 'all') {
                confirm({
                    text: 'Ingesting all data will use a massive amount of space.  Are you sure you want to do this?',
                    confirmCallback: callback
                });
            } else {
                callback();
            }
        }
    },

    initialize: function () {
        this.render();
    },

    render: function () {
        this.$el.html(dsaConfigTemplate({}));
        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'Digital Slide Archive',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            }).render();
        }

        return this;
    },

    _ingest: function (params) {
        restRequest({
            type: 'POST',
            path: 'system/ingest',
            data: params,
            error: null
        }).done(_.bind(function () {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Ingest started.',
                type: 'success',
                timeout: 4000
            });
        }, this)).error(_.bind(function (resp) {
            this.$('#g-tcga-ingest-error-message').text(
                resp.responseJSON.message
            );
        }, this));
    }
});

router.route(
    'plugins/digital_slide_archive/config', 'digitalSlideArchiveConfig',
    function () {
        events.trigger('g:navigateTo', ConfigView);
    });

exposePluginConfig(
    'digital_slide_archive', 'plugins/digital_slide_archive/config');

export default ConfigView;
