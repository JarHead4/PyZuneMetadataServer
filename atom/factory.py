from typing import Dict, Any
from xml.dom import minidom
from xml.dom.minidom import Element, Document, Text
from datetime import datetime

MIME_XML = "text/xml"
MIME_APP_XML = "application/xml"
MIME_ATOM_XML = "application/atom+xml"
MIME_UIX = "application/uix"
MIME_JPG = "image/jpeg"


def set_element_value(element: Element, value: str):
    content = Text()
    content.data = value
    element.appendChild(content)


def set_value_as_element(doc: Document, element: Element, name: str, value: Any):
    prop_element: Element = doc.createElement(name)
    if type(value) is dict:
        set_values_as_elements(doc, prop_element, value)
    else:
        set_element_value(prop_element, value)
    element.appendChild(prop_element)


def set_values_as_elements(doc: Document, element: Element, props: Dict[str, Any]):
    for name in props:
        set_value_as_element(doc, element, name, props[name])


def create_feed(doc: Document, title: str, id: str, href: str, date_updated: datetime = datetime.today()) -> Element:
    feed = create_empty_feed(doc)

    feed.appendChild(create_link(doc, href))
    feed.appendChild(create_updated(doc, date_updated))
    feed.appendChild(create_title(doc, title))
    feed.appendChild(create_id(doc, id))

    return feed


def create_empty_feed(doc: Document) -> Element:
    # Add namespaces
    feed: Element = doc.createElement("a:feed")
    feed.setAttribute("xmlns:a", "http://www.w3.org/2005/Atom")
    feed.setAttribute("xmlns:os", "http://a9.com/-/spec/opensearch/1.1/")
    feed.setAttribute("xmlns", "http://schemas.zune.net/catalog/music/2007/10")
    doc.appendChild(feed)

    return feed


def create_link(doc: Document, href: str, rel: str = "self", type: str = MIME_ATOM_XML) -> Element:
    link: Element = doc.createElement("a:link")
    link.setAttribute("rel", rel)
    link.setAttribute("type", type)
    link.setAttribute("href", href)
    return link


def create_updated(doc: Document, date_updated: datetime = datetime.today()) -> Element:
    updated: Element = doc.createElement("a:updated")
    set_element_value(updated, date_updated.isoformat())
    return updated


def create_title(doc: Document, title: str, type: str = "text") -> Element:
    title_elem: Element = doc.createElement("a:title")
    title_elem.setAttribute("type", type)
    set_element_value(title_elem, title)
    return title_elem


def create_id(doc: Document, id: str) -> Element:
    id_elem: Element = doc.createElement("a:id")
    set_element_value(id_elem, id)
    return id_elem


def create_entry(doc: Document, title: str, id: str, href: str, date_updated: datetime = datetime.today()) -> Element:
    entry: Element = doc.createElement("a:entry")

    entry.appendChild(create_link(doc, href))
    entry.appendChild(create_updated(doc, date_updated))
    entry.appendChild(create_title(doc, title))
    entry.appendChild(create_id(doc, id))

    return entry


def create_author(doc: Document, name: str) -> Element:
    author_elem: Element = doc.createElement("a:author")
    author_name_elem: Element = doc.createElement("a:name")
    set_element_value(author_name_elem, name)
    author_elem.appendChild(author_name_elem)
    return author_elem
