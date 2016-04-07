/* Wrap some views to show the brand name */

girder.wrap(girder.views.FrontPageView, 'render', function (render) {
    if (!girder.brandName) {
        girder.brandName = $('title').text();
    }
    this.$el.html(girder.templates.frontPage({
        apiRoot: girder.apiRoot,
        staticRoot: girder.staticRoot,
        currentUser: girder.currentUser,
        versionInfo: girder.versionInfo,
        brandName: girder.brandName
    }));
    return this;
});

girder.wrap(girder.views.LayoutHeaderView, 'render', function (render) {
    if (!girder.brandName) {
        girder.brandName = $('title').text();
    }
    this.$el.html(girder.templates.layoutHeader({
        brandName: girder.brandName
    }));
    this.userView.setElement(this.$('.g-current-user-wrapper')).render();
    this.searchWidget.setElement(this.$('.g-quick-search-container')).render();
    return this;
});
