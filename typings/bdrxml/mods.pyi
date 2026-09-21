"""Describe the XML fields used by TTWR, which bdrxml creates dynamically."""

from collections.abc import MutableSequence

from eulxml.xmlmap import XmlObject
from lxml.etree import _Element

class Common(XmlObject):
    node: _Element

    def __init__(self, node: _Element | None = None, **kwargs: object) -> None: ...

class TitleInfo(Common):
    title: str | None

class Genre(Common):
    text: str | None
    authority: str | None

class Abstract(Common):
    text: str | None

class DateOther(Common):
    date: str | None
    type: str | None

class OriginInfo(Common):
    other: MutableSequence[DateOther]

class NamePart(Common):
    text: str | None

class Role(Common):
    text: str | None

class Name(Common):
    name_parts: MutableSequence[NamePart]
    roles: MutableSequence[Role]

class ResourceType(Common):
    text: str | None
    authority: str | None

class Note(Common):
    text: str | None
    type: str | None
    label: str | None

class Mods(Common):
    title_info_list: MutableSequence[TitleInfo]
    genres: MutableSequence[Genre]
    abstract: Abstract | None
    origin_info: OriginInfo | None
    names: MutableSequence[Name]
    resource_types: MutableSequence[ResourceType]
    notes: MutableSequence[Note]

    def create_abstract(self) -> None: ...
    def create_origin_info(self) -> None: ...
    def serialize(self, stream: None = None, pretty: bool = False) -> bytes: ...

def make_mods() -> Mods: ...
