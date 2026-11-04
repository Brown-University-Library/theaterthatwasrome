import json
from unittest.mock import patch
from urllib.parse import parse_qs
from xml.etree import ElementTree

from bdrxml import mods
from django.test import SimpleTestCase, override_settings
from eulxml.xmlmap import load_xmlobject_from_string

from rome_app import app_settings
from rome_app.models import Annotation, Biography, Genre, Role
from unit_tests.http_mock import BdrMock

NAMESPACES = {'mods': 'http://www.loc.gov/mods/v3'}
XLINK_HREF = '{http://www.w3.org/1999/xlink}href'
EXISTING_XML = """<mods xmlns="http://www.loc.gov/mods/v3" xmlns:xlink="http://www.w3.org/1999/xlink">
    <titleInfo lang="fr"><title>Ancien titre</title></titleInfo>
    <titleInfo lang="en"><title>Old translation</title></titleInfo>
    <typeOfResource authority="local">still image</typeOfResource>
    <genre authority="local">old genre</genre>
    <abstract>Old abstract</abstract>
    <originInfo><dateOther type="impression">1600</dateOther><dateCreated>1599</dateCreated></originInfo>
    <name xlink:href="0009"><namePart>Old person</namePart><role><roleTerm>Old role</roleTerm></role></name>
    <note type="inscription" displayLabel="verso">Old inscription</note>
    <note type="resp">Earlier editor</note>
    <identifier type="local">catalogue-123</identifier>
</mods>"""


def annotation_form_data(**overrides: object) -> dict[str, object]:
    """
    Supplies cleaned form values with every optional annotation field populated.
    Called by: make_annotation(), TestAnnotationMods, TestAnnotationSubmission
    """
    data: dict[str, object] = {
        'title': 'Veduta di Roma',
        'title_language': 'it',
        'english_title': 'View of Rome',
        'genre': Genre(text='engraving'),
        'abstract': 'A view of the city.',
        'impression_date': '1650',
    }
    data.update(overrides)
    return data


def make_annotation(*, existing: bool = False, pid: str | None = None) -> Annotation:
    """
    Builds an annotation from synthetic values without saving local or remote records.
    Called by: TestAnnotationMods, TestAnnotationSubmission
    """
    mods_obj = load_xmlobject_from_string(EXISTING_XML, mods.Mods) if existing else None
    return Annotation(
        image_pid='testsuite:456',
        annotator='Current editor',
        pid=pid,
        mods_obj=mods_obj,
        form_data=annotation_form_data(),
        person_formset_data=[
            {'person': Biography(name='Example artist', trp_id='0001'), 'role': Role(text='artist')},
            {'person': Biography(name='Example printer', trp_id='0002'), 'role': Role(text='printer')},
        ],
        inscription_formset_data=[
            {'text': 'Roma, 1650', 'location': 'bottom'},
            {'text': 'Second inscription', 'location': 'verso'},
        ],
    )


class TestAnnotationMods(SimpleTestCase):
    def test_new_annotation_writes_all_optional_fields(self) -> None:
        """
        Checks titles, dates, people, roles, inscriptions, and descriptive fields in the generated XML.
        """
        root = ElementTree.fromstring(make_annotation().get_mods_obj().serialize())
        self.assertEqual(root.tag, '{http://www.loc.gov/mods/v3}mods')
        titles = root.findall('mods:titleInfo', NAMESPACES)
        self.assertEqual(
            [(title.get('lang'), title.findtext('mods:title', namespaces=NAMESPACES)) for title in titles],
            [('it', 'Veduta di Roma'), ('en', 'View of Rome')],
        )
        self.assertEqual(
            [(node.text, node.get('authority')) for node in root.findall('mods:typeOfResource', NAMESPACES)],
            [('text_resources', 'primo')],
        )
        self.assertEqual(
            [(node.text, node.get('authority')) for node in root.findall('mods:genre', NAMESPACES)],
            [('engraving', 'aat')],
        )
        self.assertEqual(root.findtext('mods:abstract', namespaces=NAMESPACES), 'A view of the city.')
        self.assertEqual(
            [(node.text, node.get('type')) for node in root.findall('mods:originInfo/mods:dateOther', NAMESPACES)],
            [('1650', 'impression')],
        )
        people = root.findall('mods:name', NAMESPACES)
        self.assertEqual(
            [
                (
                    person.get(XLINK_HREF),
                    person.findtext('mods:namePart', namespaces=NAMESPACES),
                    person.findtext('mods:role/mods:roleTerm', namespaces=NAMESPACES),
                )
                for person in people
            ],
            [('0001', 'Example artist', 'artist'), ('0002', 'Example printer', 'printer')],
        )
        self.assertEqual(
            [(note.get('type'), note.get('displayLabel'), note.text) for note in root.findall('mods:note', NAMESPACES)],
            [
                ('inscription', 'bottom', 'Roma, 1650'),
                ('inscription', 'verso', 'Second inscription'),
                ('resp', None, 'Current editor'),
            ],
        )

    def test_update_replaces_edited_fields_and_preserves_other_metadata(self) -> None:
        """
        Checks edits replace old values while retaining the resource type, identifier, date, and editor history.
        """
        annotation = make_annotation(existing=True)
        root = ElementTree.fromstring(annotation.get_mods_obj(update=True).serialize())
        self.assertEqual(
            [node.text for node in root.findall('mods:titleInfo/mods:title', NAMESPACES)],
            ['Veduta di Roma', 'View of Rome'],
        )
        self.assertEqual([node.text for node in root.findall('mods:genre', NAMESPACES)], ['engraving'])
        self.assertEqual([node.text for node in root.findall('mods:abstract', NAMESPACES)], ['A view of the city.'])
        self.assertEqual([node.text for node in root.findall('mods:originInfo/mods:dateOther', NAMESPACES)], ['1650'])
        self.assertEqual([node.get(XLINK_HREF) for node in root.findall('mods:name', NAMESPACES)], ['0001', '0002'])
        self.assertEqual(
            [node.text for node in root.findall('mods:note[@type="inscription"]', NAMESPACES)],
            ['Roma, 1650', 'Second inscription'],
        )
        self.assertEqual(
            [node.text for node in root.findall('mods:note[@type="resp"]', NAMESPACES)],
            ['Earlier editor', 'Current editor'],
        )
        self.assertEqual(
            [(node.text, node.get('authority')) for node in root.findall('mods:typeOfResource', NAMESPACES)],
            [('still image', 'local')],
        )
        self.assertEqual(root.findtext('mods:identifier[@type="local"]', namespaces=NAMESPACES), 'catalogue-123')
        self.assertEqual(root.findtext('mods:originInfo/mods:dateCreated', namespaces=NAMESPACES), '1599')

    def test_empty_optional_fields_and_blank_formset_rows_are_omitted(self) -> None:
        """
        Checks a title-only annotation omits optional fields and ignores empty person and inscription rows.
        """
        annotation = make_annotation()
        annotation.add_form_data(
            'Current editor',
            annotation_form_data(title_language='', english_title='', genre=None, abstract='', impression_date=''),
            [{}, {'person': None, 'role': None}],
            [{}, {'text': '', 'location': 'bottom'}],
        )
        root = ElementTree.fromstring(annotation.get_mods_obj().serialize())
        titles = root.findall('mods:titleInfo', NAMESPACES)
        self.assertEqual(len(titles), 1)
        self.assertIsNone(titles[0].get('lang'))
        self.assertEqual(titles[0].findtext('mods:title', namespaces=NAMESPACES), 'Veduta di Roma')
        for path in ['mods:genre', 'mods:abstract', 'mods:originInfo', 'mods:name', 'mods:note[@type="inscription"]']:
            with self.subTest(path=path):
                self.assertEqual(root.findall(path, NAMESPACES), [])
        self.assertEqual(root.findtext('mods:typeOfResource', namespaces=NAMESPACES), 'text_resources')
        self.assertEqual([node.text for node in root.findall('mods:note', NAMESPACES)], ['Current editor'])

    def test_reading_existing_mods_does_not_apply_pending_form_changes(self) -> None:
        """
        Checks reading an existing XML object leaves its titles and editor history unchanged until an update.
        """
        annotation = make_annotation(existing=True)
        mods_obj = annotation.get_mods_obj()
        original_xml = mods_obj.serialize()
        self.assertIs(annotation.get_mods_obj(), mods_obj)
        self.assertEqual(mods_obj.serialize(), original_xml)
        root = ElementTree.fromstring(original_xml)
        self.assertEqual(root.findtext('mods:titleInfo/mods:title', namespaces=NAMESPACES), 'Ancien titre')
        self.assertEqual([node.text for node in root.findall('mods:note[@type="resp"]', NAMESPACES)], ['Earlier editor'])

    def test_update_requires_existing_mods(self) -> None:
        """
        Checks an update cannot silently create XML when the original annotation has not been loaded.
        """
        with self.assertRaisesMessage(ValueError, "no mods obj - can't update"):
            make_annotation().get_mods_obj(update=True)


@override_settings(TTWR_COLLECTION_PID='testsuite:collection')
@patch.multiple(
    app_settings,
    BDR_POST_URL='https://localhost/api/items/v1/',
    BDR_IDENTITY='test-identity',
    BDR_AUTH_CODE='test-authorization',
)
class TestAnnotationSubmission(SimpleTestCase):
    def test_serialization_preserves_unicode_and_escapes_xml_text(self) -> None:
        """
        Checks XML text survives UTF-8 serialization and parsing without becoming markup or accumulating notes.
        """
        annotation = make_annotation()
        text = 'Città & veduta <Roma> "1650"'
        annotation.add_form_data(
            'Éditeur & reviewer',
            annotation_form_data(title=text, abstract=text),
            [],
            [{'text': text, 'location': 'verso & margin'}],
        )
        xml = annotation.to_mods_xml()
        self.assertIsInstance(xml, str)
        self.assertEqual(annotation.to_mods_xml(), xml)
        root = ElementTree.fromstring(xml.encode('utf-8'))
        for path in ['mods:titleInfo/mods:title', 'mods:abstract', 'mods:note[@type="inscription"]']:
            with self.subTest(path=path):
                self.assertEqual(root.findtext(path, namespaces=NAMESPACES), text)
        self.assertEqual(root.findall('.//Roma'), [])
        self.assertEqual(
            [node.get('displayLabel') for node in root.findall('mods:note[@type="inscription"]', NAMESPACES)],
            ['verso & margin'],
        )
        self.assertEqual([node.text for node in root.findall('mods:note[@type="resp"]', NAMESPACES)], ['Éditeur & reviewer'])

    def test_create_posts_xml_relationships_and_rights(self) -> None:
        """
        Checks a create sends one POST with XML, collection and image links, rights, and the annotation content model.
        """
        with BdrMock() as remote:
            remote.add('POST', 'https://localhost/api/items/v1/', body='{"pid": "testsuite:789"}')
            result = make_annotation().save_to_bdr()
        self.assertEqual(result, {'pid': 'testsuite:789'})
        self.assertEqual([call.method for call in remote.calls], ['POST'])
        fields = parse_qs(remote.calls[0].content.decode('utf-8'), strict_parsing=True)
        self.assertEqual(set(fields), {'identity', 'authorization_code', 'mods', 'rels', 'rights', 'content_model'})
        self.assertEqual(fields['identity'], ['test-identity'])
        self.assertEqual(fields['authorization_code'], ['test-authorization'])
        self.assertEqual(fields['content_model'], ['Annotation'])
        self.assertEqual(
            json.loads(fields['rels'][0]),
            {'isMemberOfCollection': 'testsuite:collection', 'isAnnotationOf': 'testsuite:456'},
        )
        self.assertEqual(
            json.loads(fields['rights'][0]),
            {'parameters': {'owner_id': 'test-identity', 'additional_rights': 'BDR_PUBLIC#display'}},
        )
        root = ElementTree.fromstring(json.loads(fields['mods'][0])['xml_data'])
        self.assertEqual(root.findtext('mods:titleInfo/mods:title', namespaces=NAMESPACES), 'Veduta di Roma')
        self.assertEqual([node.get(XLINK_HREF) for node in root.findall('mods:name', NAMESPACES)], ['0001', '0002'])
        self.assertEqual(
            [node.text for node in root.findall('mods:note[@type="inscription"]', NAMESPACES)],
            ['Roma, 1650', 'Second inscription'],
        )

    def test_update_puts_changed_xml_and_preserves_existing_metadata(self) -> None:
        """
        Checks a successful PUT targets the annotation PID and sends edited XML with its original metadata retained.
        """
        with BdrMock() as remote:
            remote.add('PUT', 'https://localhost/api/items/v1/', status=204)
            result = make_annotation(existing=True, pid='testsuite:789').update_in_bdr()
        self.assertEqual(result, {'status': 'success'})
        self.assertEqual([call.method for call in remote.calls], ['PUT'])
        fields = parse_qs(remote.calls[0].content.decode('utf-8'), strict_parsing=True)
        self.assertEqual(set(fields), {'identity', 'authorization_code', 'mods', 'pid'})
        self.assertEqual(fields['identity'], ['test-identity'])
        self.assertEqual(fields['authorization_code'], ['test-authorization'])
        self.assertEqual(fields['pid'], ['testsuite:789'])
        root = ElementTree.fromstring(json.loads(fields['mods'][0])['xml_data'])
        self.assertEqual(
            [node.text for node in root.findall('mods:titleInfo/mods:title', NAMESPACES)],
            ['Veduta di Roma', 'View of Rome'],
        )
        self.assertEqual(root.findtext('mods:identifier', namespaces=NAMESPACES), 'catalogue-123')
        self.assertEqual(root.findtext('mods:originInfo/mods:dateCreated', namespaces=NAMESPACES), '1599')
        self.assertEqual(root.findtext('mods:typeOfResource', namespaces=NAMESPACES), 'still image')
        self.assertEqual(
            [node.text for node in root.findall('mods:note[@type="resp"]', NAMESPACES)],
            ['Earlier editor', 'Current editor'],
        )

    def test_missing_annotation_pid_prevents_update_request(self) -> None:
        """
        Checks an update without an annotation identifier fails before contacting BDR.
        """
        with BdrMock() as remote, self.assertRaisesMessage(ValueError, 'no pid for annotation update'):
            make_annotation(existing=True).update_in_bdr()
        self.assertEqual(remote.calls, [])

    def test_missing_person_identifier_prevents_create_and_update_requests(self) -> None:
        """
        Checks invalid person metadata stops both create and update submissions before contacting BDR.
        """
        for existing in [False, True]:
            with self.subTest(existing=existing), BdrMock() as remote:
                annotation = make_annotation(existing=existing, pid='testsuite:789' if existing else None)
                annotation.add_form_data(
                    'Current editor',
                    annotation_form_data(),
                    [{'person': Biography(name='Person without identifier', trp_id=''), 'role': Role(text='artist')}],
                    [],
                )
                with self.assertRaisesMessage(ValueError, 'no trp_id'):
                    if existing:
                        annotation.update_in_bdr()
                    else:
                        annotation.save_to_bdr()
                self.assertEqual(remote.calls, [])
