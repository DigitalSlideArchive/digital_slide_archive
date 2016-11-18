import re

from girder.constants import AccessType
from girder.models.model_base import ValidationException

from ..constants import TCGACollectionSettingKey

_case_re = re.compile('tcga-[a-z0-9]{2}-[a-z0-9]{4}', flags=re.I)
_uuid_re = re.compile(
    '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
    flags=re.I
)
_image_re = re.compile(
    '^(?P<barcode>(?P<case>' +
    _case_re.pattern + ')[0-9a-z-]*)\.' +
    '(?P<uuid>' + _uuid_re.pattern + ')\.svs$',
    flags=re.I
)
_pathology_re = re.compile(
    '^(?P<case>' + _case_re.pattern +
    ')\.(?P<uuid>' + _uuid_re.pattern +
    ')\.pdf$',
    flags=re.I
)


class TCGAModel(object):

    def initialize(self, **kwargs):
        self.exposeFields(AccessType.READ, fields='tcga')
        super(TCGAModel, self).initialize(**kwargs)

    def save(self, doc, **kwargs):
        self.setTCGA(doc, type=self.TCGAType)
        print('_id' in doc)
        return super(TCGAModel, self).save(doc, **kwargs)

    def find(self, query=None, **kwargs):
        query = query or {}
        self.setTCGA(query, type=self.TCGAType)
        return super(TCGAModel, self).find(query, **kwargs)

    def findOne(self, query=None, **kwargs):
        query = query or {}
        self.setTCGA(query, type=self.TCGAType)
        return super(TCGAModel, self).findOne(query, **kwargs)

    def setTCGA(self, doc, **tcga):
        doc['tcga'] = doc.get('tcga', {})
        doc['tcga'].update(tcga)

    def getTCGAType(self, doc):
        return doc.get('tcga', {}).get('type')

    def getTCGACollection(self):
        tcga = self.model('setting').get(
            TCGACollectionSettingKey
        )
        if tcga is None:
            raise Exception(
                'TCGA collection id not initialized in settings'
            )
        return self.model('collection').load(
            tcga, force=True
        )

    def _parse(self, name, regex):
        m = regex.match(name)
        if m is None:
            raise ValidationException('Invalid name')
        return m.groupdict()

    def parseImage(self, name):
        return self._parse(name, _image_re)

    def parsePathology(self, name):
        return self._parse(name, _pathology_re)
