import { cancelRestRequests, apiRoot, staticRoot } from '@girder/core/rest';
import { getCurrentUser } from '@girder/core/auth';
import * as version from '@girder/core/version';
import GirderFrontPageView from '@girder/core/views/body/FrontPageView';

import frontPageTemplate from '../../templates/body/frontPage.pug';
import '../../stylesheets/body/frontPage.styl';

var FrontPageView = GirderFrontPageView.extend({
    events: {},

    initialize: function () {
        cancelRestRequests('fetch');
        this.render();
    },

    render: function () {
        this.$el.html(frontPageTemplate({
            apiRoot,
            staticRoot,
            version,
            currentUser: getCurrentUser()
        }));
    }
});

export default FrontPageView;
