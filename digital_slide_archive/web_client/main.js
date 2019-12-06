import events from '@girder/core/events';
import router from '@girder/core/router';

import { registerPluginNamespace } from '@girder/core/pluginUtils';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

// expose symbols under girder.plugins
import * as digitalSlideArchive from '@girder/digital_slide_archive';

// import modules for side effects
import './views/itemList';
import './views/itemPage';

import ConfigView from './views/body/ConfigView';

const pluginName = 'digital_slide_archive';
const configRoute = `plugins/${pluginName}/config`;

registerPluginNamespace(pluginName, digitalSlideArchive);

exposePluginConfig(pluginName, configRoute);

router.route(configRoute, 'DigitalSlideArchiveConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
