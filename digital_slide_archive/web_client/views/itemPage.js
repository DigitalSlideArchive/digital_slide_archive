import { wrap } from '@girder/core/utilities/PluginUtils';
import { restRequest } from '@girder/core/rest';
import events from '@girder/core/events';
import ItemView from '@girder/core/views/body/ItemView';

import '../stylesheets/views/itemList.styl';

wrap(ItemView, 'render', function (render) {
    function quarantine(event) {
        const item = this.model;
        restRequest({
            type: 'PUT',
            url: 'digital_slide_archive/quarantine/' + item.id,
            error: null
        }).done((resp) => {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Item quarantined.',
                type: 'success',
                timeout: 4000
            });
            this.render();
        }).fail((resp) => {
            events.trigger('g:alert', {
                icon: 'cancel',
                text: 'Failed to quarantine item.',
                type: 'danger',
                timeout: 4000
            });
        });
    }

    this.once('g:rendered', function () {
        if (this.$el.find('.g-edit-item[role="menuitem"]').length && !this.$el.find('.g-dsa-quarantine-item[role="menuitem"]').length) {
            this.$el.find('.g-edit-item[role="menuitem"]').parent('li').after(
                '<li role="presentation"><a class="g-dsa-quarantine-item" role="menuitem"><span>Q</span>Quarantine item</a></li>'
            );
        }
        if (this.$el.find('.g-item-actions-menu').length && !this.$el.find('.g-dsa-open-item[role="menuitem"]').length &&
            this.model.attributes.largeImage) {
            this.$el.find('.g-item-actions-menu').prepend(
                `<li role="presentation">
                <a class="g-dsa-open-item" role="menuitem" href="/dsa#?image=${this.model.id}" target="_blank">
                    <i class="icon-link-ext"></i>Open in Digital SlideArchive
                </a>
            </li>`
            );
        }
        this.events['click .g-dsa-quarantine-item'] = quarantine;
        this.delegateEvents();
    });
    render.call(this);
});
