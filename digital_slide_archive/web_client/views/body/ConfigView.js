import $ from 'jquery';
import _ from 'underscore';
import View from '@girder/core/views/View';

import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import BrowserWidget from '@girder/core/views/widgets/BrowserWidget';
import { restRequest } from '@girder/core/rest';
import events from '@girder/core/events';
import router from '@girder/core/router';

import ConfigViewTemplate from '../../templates/body/configView.pug';
import '../../stylesheets/body/configView.styl';

/**
 * Show the default quota settings for users and collections.
 */
var ConfigView = View.extend({
    events: {
        'click #g-dsa-save': function (event) {
            this.$('#g-dsa-error-message').text('');
            var settings = _.map(this.settingsKeys, (key) => {
                const element = this.$('#g-' + key.replace('digital_slide_archive', 'dsa').replace(/[_.]/g, '-'));
                var result = {
                    key,
                    value: element.val() || null
                };
                if (key === 'digital_slide_archive.quarantine_folder') {
                    result.value = result.value ? result.value.split(' ')[0] : '';
                }
                return result;
            });
            this._saveSettings(settings);
        },
        'click #g-dsa-brand-default-color': function () {
            this.$('#g-dsa-brand-color').val(this.defaults['digital_slide_archive.brand_color']);
        },
        'click #g-dsa-banner-default-color': function () {
            this.$('#g-dsa-banner-color').val(this.defaults['digital_slide_archive.banner_color']);
        },
        'click #g-dsa-cancel': function (event) {
            router.navigate('plugins', {trigger: true});
        },
        'click .g-open-browser': '_openBrowser'
    },
    initialize: function () {
        this.breadcrumb = new PluginConfigBreadcrumbWidget({
            pluginName: 'Digital Slide Archive',
            parentView: this
        });

        this.settingsKeys = [
            'digital_slide_archive.webroot_path',
            'digital_slide_archive.brand_name',
            'digital_slide_archive.brand_color',
            'digital_slide_archive.banner_color',
            'digital_slide_archive.default_draw_styles',
            'digital_slide_archive.quarantine_folder'
        ];
        $.when(
            restRequest({
                method: 'GET',
                url: 'system/setting',
                data: {
                    list: JSON.stringify(this.settingsKeys),
                    default: 'none'
                }
            }).done((resp) => {
                this.settings = resp;
            }),
            restRequest({
                method: 'GET',
                url: 'system/setting',
                data: {
                    list: JSON.stringify(this.settingsKeys),
                    default: 'default'
                }
            }).done((resp) => {
                this.defaults = resp;
            })
        ).done(() => {
            this.render();
        });

        this._browserWidgetView = new BrowserWidget({
            parentView: this,
            titleText: 'Quarantine Destination',
            helpText: 'Browse to a location to select it as the destination.',
            submitText: 'Select Destination',
            validate: function (model) {
                let isValid = $.Deferred();
                if (!model || model.get('_modelType') !== 'folder') {
                    isValid.reject('Please select a folder.');
                } else {
                    isValid.resolve();
                }
                return isValid.promise();
            }
        });
        this.listenTo(this._browserWidgetView, 'g:saved', function (val) {
            this.$('#g-dsa-quarantine-folder').val(val.id);
            restRequest({
                url: `resource/${val.id}/path`,
                method: 'GET',
                data: {type: val.get('_modelType')}
            }).done((result) => {
                // Only add the resource path if the value wasn't altered
                if (this.$('#g-dsa-quarantine-folder').val() === val.id) {
                    this.$('#g-dsa-quarantine-folder').val(`${val.id} (${result})`);
                }
            });
        });
    },

    render: function () {
        this.$el.html(ConfigViewTemplate({
            settings: this.settings,
            defaults: this.defaults
        }));
        this.breadcrumb.setElement(this.$('.g-config-breadcrumb-container')).render();
        return this;
    },

    _saveSettings: function (settings) {
        return restRequest({
            method: 'PUT',
            url: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(() => {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }).fail((resp) => {
            this.$('#g-dsa-error-message').text(
                resp.responseJSON.message
            );
        });
    },

    _openBrowser: function () {
        this._browserWidgetView.setElement($('#g-dialog-container')).render();
    }
});

export default ConfigView;
