/* globals girder */

/**
 * Show the TCGA Ingest settings (which is really an ingest control).
 */
girder.views.tcgaIngest_ConfigView = girder.View.extend({
    events: {
        'submit #g-tcga-ingest-form': function (event) {
            event.preventDefault();

            var assetstoreId = this.$('#g-tcga-ingest-assetstore-id').val().trim(),
                srcPath = this.$('#g-tcga-ingest-path').val().trim(),
                destId = this.$('#g-tcga-ingest-dest-id').val().trim(),
                destType = this.$('#g-tcga-ingest-dest-type').val(),
                count = this.$('#g-tcga-ingest-amount').val();
            this.$('.g-validation-failed-message').empty();
            this._ingest({
                dataset: 'tcga',
                path: srcPath,
                progress: 'true',
                assetstoreId: assetstoreId,
                count: count
            });
        }
    },

    initialize: function () {
        this.render();
    },

    render: function () {
        this.$el.html(girder.templates.tcgaIngestConfig({}));
        if (!this.breadcrumb) {
            this.breadcrumb = new girder.views.PluginConfigBreadcrumbWidget({
                pluginName: 'TCGA Ingest',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            }).render();
        }

        return this;
    },

    _ingest: function (params) {
        girder.restRequest({
            type: 'POST',
            path: 'system/ingest',
            data: params,
            error: null
        }).done(_.bind(function () {
            girder.events.trigger('g:alert', {
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

girder.router.route(
    'plugins/digital_slide_archive/config', 'tcgaIngestConfig', function () {
        girder.events.trigger('g:navigateTo',
                              girder.views.tcgaIngest_ConfigView);
    });

girder.exposePluginConfig(
    'digital_slide_archive', 'plugins/digital_slide_archive/config');
