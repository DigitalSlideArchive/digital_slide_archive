import Backbone from 'backbone';
import { LocalStorage } from 'backbone.localstorage';

import StyleModel from '../models/StyleModel';

const StyleCollection = Backbone.Collection.extend({
    model: StyleModel,
    localStorage: new LocalStorage('digital_slide_archive.draw.style')
});

export default StyleCollection;
