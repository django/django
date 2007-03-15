"""
XML serializer.
"""

from django.conf import settings
from django.core.serializers import base
from django.db import models
from django.utils.xmlutils import SimplerXMLGenerator
from xml.dom import pulldom

class Serializer(base.Serializer):
    """
    Serializes a QuerySet to XML.
    """
    
    def indent(self, level):
        if self.options.get('indent', None) is not None:
            self.xml.ignorableWhitespace('\n' + ' ' * self.options.get('indent', None) * level)

    def start_serialization(self):
        """
        Start serialization -- open the XML document and the root element.
        """
        self.xml = SimplerXMLGenerator(self.stream, self.options.get("encoding", settings.DEFAULT_CHARSET))
        self.xml.startDocument()
        self.xml.startElement("django-objects", {"version" : "1.0"})
        
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
            raise base.SerializationError("Non-model object (%s) encountered during serialization" % type(obj))
            
        self.indent(1)
        self.xml.startElement("object", {
            "pk"    : str(obj._get_pk_val()),
            "model" : str(obj._meta),
        })
        
    def end_object(self, obj):
        """
        Called after handling all fields for an object.
        """
        self.indent(1)
        self.xml.endElement("object")
        
    def handle_field(self, obj, field):
        """
        Called to handle each field on an object (except for ForeignKeys and
        ManyToManyFields)
        """
        self.indent(2)
        self.xml.startElement("field", {
            "name" : field.name,
            "type" : field.get_internal_type()
        })
        
        # Get a "string version" of the object's data (this is handled by the
        # serializer base class). 
        if getattr(obj, field.name) is not None:
            value = self.get_string_value(obj, field)
            self.xml.characters(str(value))
        else:
            self.xml.addQuickElement("None")

        self.xml.endElement("field")
        
    def handle_fk_field(self, obj, field):
        """
        Called to handle a ForeignKey (we need to treat them slightly
        differently from regular fields).
        """
        self._start_relational_field(field)
        related = getattr(obj, field.name)
        if related is not None:
            self.xml.characters(str(related._get_pk_val()))
        else:
            self.xml.addQuickElement("None")
        self.xml.endElement("field")
    
    def handle_m2m_field(self, obj, field):
        """
        Called to handle a ManyToManyField. Related objects are only
        serialized as references to the object's PK (i.e. the related *data*
        is not dumped, just the relation).
        """
        self._start_relational_field(field)
        for relobj in getattr(obj, field.name).iterator():
            self.xml.addQuickElement("object", attrs={"pk" : str(relobj._get_pk_val())})
        self.xml.endElement("field")
        
    def _start_relational_field(self, field):
        """
        Helper to output the <field> element for relational fields
        """
        self.indent(2)
        self.xml.startElement("field", {
            "name" : field.name,
            "rel"  : field.rel.__class__.__name__,
            "to"   : str(field.rel.to._meta),
        })
        
class Deserializer(base.Deserializer):
    """
    Deserialize XML.
    """
    
    def __init__(self, stream_or_string, **options):
        super(Deserializer, self).__init__(stream_or_string, **options)
        self.encoding = self.options.get("encoding", settings.DEFAULT_CHARSET)
        self.event_stream = pulldom.parse(self.stream) 
    
    def next(self):
        for event, node in self.event_stream:
            if event == "START_ELEMENT" and node.nodeName == "object":
                self.event_stream.expandNode(node)
                return self._handle_object(node)
        raise StopIteration
        
    def _handle_object(self, node):
        """
        Convert an <object> node to a DeserializedObject.
        """
        # Look up the model using the model loading mechanism. If this fails, bail.
        Model = self._get_model_from_node(node, "model")
        
        # Start building a data dictionary from the object.  If the node is
        # missing the pk attribute, bail.
        pk = node.getAttribute("pk")
        if not pk:
            raise base.DeserializationError("<object> node is missing the 'pk' attribute")

        data = {Model._meta.pk.attname : Model._meta.pk.to_python(pk)}
        
        # Also start building a dict of m2m data (this is saved as
        # {m2m_accessor_attribute : [list_of_related_objects]})
        m2m_data = {}
        
        # Deseralize each field.
        for field_node in node.getElementsByTagName("field"):
            # If the field is missing the name attribute, bail (are you
            # sensing a pattern here?)
            field_name = field_node.getAttribute("name")
            if not field_name:
                raise base.DeserializationError("<field> node is missing the 'name' attribute")
            
            # Get the field from the Model. This will raise a
            # FieldDoesNotExist if, well, the field doesn't exist, which will
            # be propagated correctly.
            field = Model._meta.get_field(field_name)
            
            # As is usually the case, relation fields get the special treatment.
            if field.rel and isinstance(field.rel, models.ManyToManyRel):
                m2m_data[field.name] = self._handle_m2m_field_node(field_node, field)
            elif field.rel and isinstance(field.rel, models.ManyToOneRel):
                data[field.attname] = self._handle_fk_field_node(field_node, field)
            else:
                if len(field_node.childNodes) == 1 and field_node.childNodes[0].nodeName == 'None':
                    value = None
                else:
                    value = field.to_python(getInnerText(field_node).strip().encode(self.encoding))
                data[field.name] = value
        
        # Return a DeserializedObject so that the m2m data has a place to live.
        return base.DeserializedObject(Model(**data), m2m_data)
        
    def _handle_fk_field_node(self, node, field):
        """
        Handle a <field> node for a ForeignKey
        """
        # Check if there is a child node named 'None', returning None if so.
        if len(node.childNodes) == 1 and node.childNodes[0].nodeName == 'None':
            return None
        else:
            return field.rel.to._meta.pk.to_python(
                       getInnerText(node).strip().encode(self.encoding))
        
    def _handle_m2m_field_node(self, node, field):
        """
        Handle a <field> node for a ManyToManyField
        """
        return [field.rel.to._meta.pk.to_python(
                    c.getAttribute("pk").encode(self.encoding)) 
                    for c in node.getElementsByTagName("object")]
    
    def _get_model_from_node(self, node, attr):
        """
        Helper to look up a model from a <object model=...> or a <field
        rel=... to=...> node.
        """
        model_identifier = node.getAttribute(attr)
        if not model_identifier:
            raise base.DeserializationError(
                "<%s> node is missing the required '%s' attribute" \
                    % (node.nodeName, attr))
        try:
            Model = models.get_model(*model_identifier.split("."))
        except TypeError:
            Model = None
        if Model is None:
            raise base.DeserializationError(
                "<%s> node has invalid model identifier: '%s'" % \
                    (node.nodeName, model_identifier))
        return Model
        
    
def getInnerText(node):
    """
    Get all the inner text of a DOM node (recursively).
    """
    # inspired by http://mail.python.org/pipermail/xml-sig/2005-March/011022.html
    inner_text = []
    for child in node.childNodes:
        if child.nodeType == child.TEXT_NODE or child.nodeType == child.CDATA_SECTION_NODE:
            inner_text.append(child.data)
        elif child.nodeType == child.ELEMENT_NODE:
            inner_text.extend(getInnerText(child))
        else:
           pass
    return "".join(inner_text)