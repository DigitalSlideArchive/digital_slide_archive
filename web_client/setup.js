/* Wrap some views to show the brand name */
import { wrap } from 'girder/utilities/PluginUtils';
import LayoutHeaderView from 'girder/views/layout/HeaderView';

import layoutHeader from './templates/layoutHeader.pug';

wrap(LayoutHeaderView, 'render', function (render) {
    var brandName = $('title').text();
    this.$el.html(layoutHeader({
        brandName: brandName
    }));
    this.userView.setElement(this.$('.g-current-user-wrapper')).render();
    this.searchWidget.setElement(this.$('.g-quick-search-container')).render();
    return this;
});
