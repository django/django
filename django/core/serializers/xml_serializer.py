"""
XML serializer.
"""
import json
from xml.dom import pulldom
from xml.sax import handler
from xml.sax.expatreader import ExpatParser as _ExpatParser

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers import base
from django.db import DEFAULT_DB_ALIAS, models
from django.utils.xmlutils import SimplerXMLGenerator, UnserializableContentError


class Serializer(base.Serializer):
    """Serialize a QuerySet to XML."""

    def indent(self, level):
        if self.options.get("indent") is not None:
            self.xml.ignorableWhitespace(
                "\n" + " " * self.options.get("indent") * level
            )

    def start_serialization(self):
        """
        Start serialization -- open the XML document and the root element.
        """
        self.xml = SimplerXMLGenerator(
            self.stream, self.options.get("encoding", settings.DEFAULT_CHARSET)
        )
        self.xml.startDocument()
        self.xml.startElement("django-objects", {"version": "1.0"})

    def end_serialization(self):
        """
        End serialization -- end the document.
        """
        self.indent(0)
        self.xml.endElement("django-objects")
        self.xml.endDocument()

    def start_object(self, obj):
        """
        Called as each object is handled.
        """
        if not hasattr(obj, "_meta"):
            raise base.SerializationError(
                "Non-model object (%s) encountered during serialization" % type(obj)
            )

        self.indent(1)
        attrs = {"model": str(obj._meta)}
        if not self.use_natural_primary_keys or not hasattr(obj, "natural_key"):
            obj_pk = obj.pk
            if obj_pk is not None:
                attrs["pk"] = str(obj_pk)

        self.xml.startElement("object", attrs)

    def end_object(self, obj):
        """
        Called after handling all fields for an object.
        """
        self.indent(1)
        self.xml.endElement("object")

    def handle_field(self, obj, field):
        """
        Handle each field on an object (except for ForeignKeys and
        ManyToManyFields).
        """
        self.indent(2)
        self.xml.startElement(
            "field",
            {
                "name": field.name,
                "type": field.get_internal_type(),
            },
        )

        # Get a "string version" of the object's data.
        if getattr(obj, field.name) is not None:
            value = field.value_to_string(obj)
            if field.get_internal_type() == "JSONField":
                # Dump value since JSONField.value_to_string() doesn't output
                # strings.
                value = json.dumps(value, cls=field.encoder)
            try:
                self.xml.characters(value)
            except UnserializableContentError:
                raise ValueError(
                    "%s.%s (pk:%s) contains unserializable characters"
                    % (obj.__class__.__name__, field.name, obj.pk)
                )
        else:
            self.xml.addQuickElement("None")

        self.xml.endElement("field")

    def handle_fk_field(self, obj, field):
        """
        Handle a ForeignKey (they need to be treated slightly
        differently from regular fields).
        """
        self._start_relational_field(field)
        related_att = getattr(obj, field.get_attname())
        if related_att is not None:
            if self.use_natural_foreign_keys and hasattr(
                field.remote_field.model, "natural_key"
            ):
                related = getattr(obj, field.name)
                # If related object has a natural key, use it
                related = related.natural_key()
                # Iterable natural keys are rolled out as subelements
                for key_value in related:
                    self.xml.startElement("natural", {})
                    self.xml.characters(str(key_value))
                    self.xml.endElement("natural")
            else:
                self.xml.characters(str(related_att))
        else:
            self.xml.addQuickElement("None")
        self.xml.endElement("field")

    def handle_m2m_field(self, obj, field):
        """
        Handle a ManyToManyField. Related objects are only serialized as
        references to the object's PK (i.e. the related *data* is not dumped,
        just the relation).
        """
        if field.remote_field.through._meta.auto_created:
            self._start_relational_field(field)
            if self.use_natural_foreign_keys and hasattr(
                field.remote_field.model, "natural_key"
            ):
                # If the objects in the m2m have a natural key, use it
                def handle_m2m(value):
                    natural = value.natural_key()
                    # Iterable natural keys are rolled out as subelements
                    self.xml.startElement("object", {})
                    for key_value in natural:
                        self.xml.startElement("natural", {})
                        self.xml.characters(str(key_value))
                        self.xml.endElement("natural")
                    self.xml.endElement("object")

                def queryset_iterator(obj, field):
                    return getattr(obj, field.name).iterator()

            else:

                def handle_m2m(value):
                    self.xml.addQuickElement("object", attrs={"pk": str(value.pk)})

                def queryset_iterator(obj, field):
                    return getattr(obj, field.name).only("pk").iterator()

            m2m_iter = getattr(obj, "_prefetched_objects_cache", {}).get(
                field.name,
                queryset_iterator(obj, field),
            )
            for relobj in m2m_iter:
                handle_m2m(relobj)

            self.xml.endElement("field")

    def _start_relational_field(self, field):
        """Output the <field> element for relational fields."""
        self.indent(2)
        self.xml.startElement(
            "field",
            {
                "name": field.name,
                "rel": field.remote_field.__class__.__name__,
                "to": str(field.remote_field.model._meta),
            },
        )


class Deserializer(base.Deserializer):
    """Deserialize XML."""

    def __init__(
        self,
        stream_or_string,
        *,
        using=DEFAULT_DB_ALIAS,
        ignorenonexistent=False,
        **options,
    ):
        super().__init__(stream_or_string, **options)
        self.handle_forward_references = options.pop("handle_forward_references", False)
        self.event_stream = pulldom.parse(self.stream, self._make_parser())
        self.db = using
        self.ignore = ignorenonexistent

    def _make_parser(self):
        """Create a hardened XML parser (no custom/external entities)."""
        return DefusedExpatParser()

    def __next__(self):
        for event, node in self.event_stream:
            if event == "START_ELEMENT" and node.nodeName == "object":
                self.event_stream.expandNode(node)
                return self._handle_object(node)
        raise StopIteration

    def _handle_object(self, node):
        """Convert an <object> node to a DeserializedObject."""
        # Look up the model using the model loading mechanism. If this fails,
        # bail.
        Model = self._get_model_from_node(node, "model")

        # Start building a data dictionary from the object.
        data = {}
        if node.hasAttribute("pk"):
            data[Model._meta.pk.attname] = Model._meta.pk.to_python(
                node.getAttribute("pk")
            )

        # Also start building a dict of m2m data (this is saved as
        # {m2m_accessor_attribute : [list_of_related_objects]})
        m2m_data = {}
        deferred_fields = {}

        field_names = {f.name for f in Model._meta.get_fields()}
        # Deserialize each field.
        for field_node in node.getElementsByTagName("field"):
            # If the field is missing the name attribute, bail (are you
            # sensing a pattern here?)
            field_name = field_node.getAttribute("name")
            if not field_name:
                raise base.DeserializationError(
                    "<field> node is missing the 'name' attribute"
                )

            # Get the field from the Model. This will raise a
            # FieldDoesNotExist if, well, the field doesn't exist, which will
            # be propagated correctly unless ignorenonexistent=True is used.
            if self.ignore and field_name not in field_names:
                continue
            field = Model._meta.get_field(field_name)

            # As is usually the case, relation fields get the special treatment.
            if field.remote_field and isinstance(
                field.remote_field, models.ManyToManyRel
            ):
                value = self._handle_m2m_field_node(field_node, field)
                if value == base.DEFER_FIELD:
                    deferred_fields[field] = [
                        [
                            getInnerText(nat_node).strip()
                            for nat_node in obj_node.getElementsByTagName("natural")
                        ]
                        for obj_node in field_node.getElementsByTagName("object")
                    ]
                else:
                    m2m_data[field.name] = value
            elif field.remote_field and isinstance(
                field.remote_field, models.ManyToOneRel
            ):
                value = self._handle_fk_field_node(field_node, field)
                if value == base.DEFER_FIELD:
                    deferred_fields[field] = [
                        getInnerText(k).strip()
                        for k in field_node.getElementsByTagName("natural")
                    ]
                else:
                    data[field.attname] = value
            else:
                if field_node.getElementsByTagName("None"):
                    value = None
                else:
                    value = field.to_python(getInnerText(field_node).strip())
                    # Load value since JSONField.to_python() outputs strings.
                    if field.get_internal_type() == "JSONField":
                        value = json.loads(value, cls=field.decoder)
                data[field.name] = value

        obj = base.build_instance(Model, data, self.db)

        # Return a DeserializedObject so that the m2m data has a place to live.
        return base.DeserializedObject(obj, m2m_data, deferred_fields)

    def _handle_fk_field_node(self, node, field):
        """
        Handle a <field> node for a ForeignKey
        """
        # Check if there is a child node named 'None', returning None if so.
        if node.getElementsByTagName("None"):
            return None
        else:
            model = field.remote_field.model
            if hasattr(model._default_manager, "get_by_natural_key"):
                keys = node.getElementsByTagName("natural")
                if keys:
                    # If there are 'natural' subelements, it must be a natural key
                    field_value = [getInnerText(k).strip() for k in keys]
                    try:
                        obj = model._default_manager.db_manager(
                            self.db
                        ).get_by_natural_key(*field_value)
                    except ObjectDoesNotExist:
                        if self.handle_forward_references:
                            return base.DEFER_FIELD
                        else:
                            raise
                    obj_pk = getattr(obj, field.remote_field.field_name)
                    # If this is a natural foreign key to an object that
                    # has a FK/O2O as the foreign key, use the FK value
                    if field.remote_field.model._meta.pk.remote_field:
                        obj_pk = obj_pk.pk
                else:
                    # Otherwise, treat like a normal PK
                    field_value = getInnerText(node).strip()
                    obj_pk = model._meta.get_field(
                        field.remote_field.field_name
                    ).to_python(field_value)
                return obj_pk
            else:
                field_value = getInnerText(node).strip()
                return model._meta.get_field(field.remote_field.field_name).to_python(
                    field_value
                )

    def _handle_m2m_field_node(self, node, field):
        """
        Handle a <field> node for a ManyToManyField.
        """
        model = field.remote_field.model
        default_manager = model._default_manager
        if hasattr(default_manager, "get_by_natural_key"):

            def m2m_convert(n):
                keys = n.getElementsByTagName("natural")
                if keys:
                    # If there are 'natural' subelements, it must be a natural key
                    field_value = [getInnerText(k).strip() for k in keys]
                    obj_pk = (
                        default_manager.db_manager(self.db)
                        .get_by_natural_key(*field_value)
                        .pk
                    )
                else:
                    # Otherwise, treat like a normal PK value.
                    obj_pk = model._meta.pk.to_python(n.getAttribute("pk"))
                return obj_pk

        else:

            def m2m_convert(n):
                return model._meta.pk.to_python(n.getAttribute("pk"))

        values = []
        try:
            for c in node.getElementsByTagName("object"):
                values.append(m2m_convert(c))
        except Exception as e:
            if isinstance(e, ObjectDoesNotExist) and self.handle_forward_references:
                return base.DEFER_FIELD
            else:
                raise base.M2MDeserializationError(e, c)
        else:
            return values

    def _get_model_from_node(self, node, attr):
        """
        Look up a model from a <object model=...> or a <field rel=... to=...>
        node.
        """
        model_identifier = node.getAttribute(attr)
        if not model_identifier:
            raise base.DeserializationError(
                "<%s> node is missing the required '%s' attribute"
                % (node.nodeName, attr)
            )
        try:
            return apps.get_model(model_identifier)
        except (LookupError, TypeError):
            raise base.DeserializationError(
                "<%s> node has invalid model identifier: '%s'"
                % (node.nodeName, model_identifier)
            )


def getInnerText(node):
    """Get all the inner text of a DOM node (recursively)."""
    # inspired by https://mail.python.org/pipermail/xml-sig/2005-March/011022.html
    inner_text = []
    for child in node.childNodes:
        if (
            child.nodeType == child.TEXT_NODE
            or child.nodeType == child.CDATA_SECTION_NODE
        ):
            inner_text.append(child.data)
        elif child.nodeType == child.ELEMENT_NODE:
            inner_text.extend(getInnerText(child))
        else:
            pass
    return "".join(inner_text)


# Below code based on Christian Heimes' defusedxml


class DefusedExpatParser(_ExpatParser):
    """
    An expat parser hardened against XML bomb attacks.

    Forbid DTDs, external entity references
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFeature(handler.feature_external_ges, False)
        self.setFeature(handler.feature_external_pes, False)

    def start_doctype_decl(self, name, sysid, pubid, has_internal_subset):
        raise DTDForbidden(name, sysid, pubid)

    def entity_decl(
        self, name, is_parameter_entity, value, base, sysid, pubid, notation_name
    ):
        raise EntitiesForbidden(name, value, base, sysid, pubid, notation_name)

    def unparsed_entity_decl(self, name, base, sysid, pubid, notation_name):
        # expat 1.2
        raise EntitiesForbidden(name, None, base, sysid, pubid, notation_name)

    def external_entity_ref_handler(self, context, base, sysid, pubid):
        raise ExternalReferenceForbidden(context, base, sysid, pubid)

    def reset(self):
        _ExpatParser.reset(self)
        parser = self._parser
        parser.StartDoctypeDeclHandler = self.start_doctype_decl
        parser.EntityDeclHandler = self.entity_decl
        parser.UnparsedEntityDeclHandler = self.unparsed_entity_decl
        parser.ExternalEntityRefHandler = self.external_entity_ref_handler


class DefusedXmlException(ValueError):
    """Base exception."""

    def __repr__(self):
        return str(self)


class DTDForbidden(DefusedXmlException):
    """Document type definition is forbidden."""

    def __init__(self, name, sysid, pubid):
        super().__init__()
        self.name = name
        self.sysid = sysid
        self.pubid = pubid

    def __str__(self):
        tpl = "DTDForbidden(name='{}', system_id={!r}, public_id={!r})"
        return tpl.format(self.name, self.sysid, self.pubid)


class EntitiesForbidden(DefusedXmlException):
    """Entity definition is forbidden."""

    def __init__(self, name, value, base, sysid, pubid, notation_name):
        super().__init__()
        self.name = name
        self.value = value
        self.base = base
        self.sysid = sysid
        self.pubid = pubid
        self.notation_name = notation_name

    def __str__(self):
        tpl = "EntitiesForbidden(name='{}', system_id={!r}, public_id={!r})"
        return tpl.format(self.name, self.sysid, self.pubid)


class ExternalReferenceForbidden(DefusedXmlException):
    """Resolving an external reference is forbidden."""

    def __init__(self, context, base, sysid, pubid):
        super().__init__()
        self.context = context
        self.base = base
        self.sysid = sysid
        self.pubid = pubid

    def __str__(self):
        tpl = "ExternalReferenceForbidden(system_id='{}', public_id={})"
        return tpl.format(self.sysid, self.pubid)
