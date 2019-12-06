import { getCurrentUser } from '@girder/core/auth';
import GirderHeaderUserView from '@girder/core/views/layout/HeaderUserView';

import headerUserTemplate from '../../templates/layout/headerUser.pug';

var HeaderUserView = GirderHeaderUserView.extend({
    render() {
        this.$el.html(headerUserTemplate({
            user: getCurrentUser()
        }));
        return this;
    }
});

export default HeaderUserView;
