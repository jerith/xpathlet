# -*- test-case-name: xpathlet.tests.test_engine -*-

from xpathlet.parser import parser


# XPath object types

class XPathObject(object):
    def __init__(self, value):
        self.value = value


class XPathNodeSet(XPathObject):
    def __init__(self, nodes):
        self.nodes = set(nodes)


class XPathBoolean(XPathObject):
    pass


class XPathNumber(XPathObject):
    pass


class XPathString(XPathObject):
    pass


# XPath node types

class XPathNode(object):
    def string_value(self):
        raise NotImplementedError

    def expanded_name(self):
        return None

    def _walk_children(self, node_type=None):
        for child in self.get_children():
            if (node_type is None) or isinstance(child, node_type):
                yield child
            for desc in child._walk_children():
                if (node_type is None) or isinstance(desc, node_type):
                    yield desc

    def get_children(self):
        return ()

    def get_root_node(self):
        return self.parent.get_root_node()


class XPathRootNode(XPathNode):
    # TODO: Build non-element children.
    def __init__(self, document, namespaces):
        self._document = document
        self._namespaces = namespaces
        self._children = None

    def get_children(self):
        if self._children is None:
            self._children = [XPathElementNode(self, self._document.getroot())]
        return self._children

    def string_value(self):
        # Concatenation of all Text node descendents.
        return u''.join(n.string_value()
                        for n in self._walk_children(XPathTextNode))

    def get_root_node(self):
        return self


class XPathElementNode(XPathNode):
    def __init__(self, parent, enode):
        self.parent = parent
        self._enode = enode
        self.prefix, self.name = split_eqname(enode.tag)
        self._children = None
        self._attributes = None
        self.xml_id = None

    def get_children(self):
        if self._children is None:
            self._children = [
                XPathElementNode(self, enode) for enode in self._enode]
        return self._children

    def get_attributes(self):
        if self._attributes is None:
            self._attributes = [XPathAttributeNode(self, k, v)
                                for k, v in self._enode.attrib.items()]
        return self._attributes

    def expanded_name(self):
        return (self.prefix, self.name)

    def string_value(self):
        # Concatenation of all Text node descendents.
        return u''.join(n.string_value()
                        for n in self._walk_children(XPathTextNode))

    def __repr__(self):
        return u'<XPathElementNode %s>' % (eqname(self.prefix, self.name),)


class XPathAttributeNode(XPathNode):
    def __init__(self, parent, name, value):
        self.parent = parent
        self.prefix, self.name = split_eqname(name)
        self._value = value

    def expanded_name(self):
        return (self.prefix, self.name)

    def string_value(self):
        # TODO: Figure out what this means.
        return self._value

    def __repr__(self):
        return u'<XPathAttributeNode %s=%r>' % (eqname(self.prefix, self.name),
                                                self._value)


class XPathNamespaceNode(XPathNode):
    def __init__(self, parent, prefix, uri):
        self.parent = parent
        self._prefix = prefix
        self._uri = uri

    def expanded_name(self):
        return (None, self._prefix)

    def string_value(self):
        return self._uri


class XPathTextNode(XPathNode):
    def __init__(self, parent, text):
        self.parent = parent
        self._text = text

    def string_value(self):
        return self._text


class XPathProcessingInstructionNode(XPathNode):
    def __init__(self, parent, enode):
        # TODO: Implement this?
        raise NotImplementedError()


class XPathCommentNode(XPathNode):
    def __init__(self, parent, enode):
        # TODO: Implement this?
        raise NotImplementedError()


class Context(object):
    def __init__(self, node, position, size, variables, functions, namespaces):
        self.node = node
        self.position = position
        self.size = size
        self.variables = variables
        self.functions = functions
        self.namespaces = namespaces

    def sub_context(self, node=None, position=None, size=None):
        if node is None:
            node = self.node
        if position is None:
            position = self.position
        if size is None:
            size = self.size
        return Context(node, position, size, self.variables, self.functions,
                       self.namespaces)


class ExpressionEngine(object):
    def __init__(self, doc, functions, namespaces):
        pass


# Stuff to work around ElementTree doing silly things.

def split_eqname(name):
    if name.startswith('{'):
        return tuple(name[1:].split('}'))
    return (None, name)


def eqname(prefix, name):
    if prefix is None:
        return name
    return '{%s}%s' % (prefix, name)


def build_xpath_tree(source):
    """This builds an XPath node tree with namespace prefix mappings."""
    # TODO: Handle namespace prefix scoping?
    from xml.etree.ElementTree import iterparse, ElementTree

    ip = iterparse(source, ['start-ns'])
    namespaces = {}
    for _, (prefix, uri) in ip:
        if namespaces.get(prefix, uri) != uri:
            raise ValueError(
                'Redefined namespace prefix: %r' % (prefix,))
        namespaces[prefix] = uri

    doc = ElementTree(ip.root)
    return XPathRootNode(doc, namespaces)
