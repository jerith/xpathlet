# -*- test-case-name: xpathlet.tests.test_engine -*-

# NOTE: Sections of the XPath language specification are quoted in comments
# below. The full document can be found at: http://www.w3.org/TR/xpath/

import math
import operator
from itertools import dropwhile
from xml.etree import ElementTree as ET


# Stuff to work around ElementTree doing silly things.

def split_eqname(name):
    if name.startswith('{'):
        return tuple(name[1:].split('}'))
    return (None, name)


def eqname(prefix, name):
    if prefix is None:
        return name
    return '{%s}%s' % (prefix, name)


# XPath object types

class XPathObject(object):
    object_type = None

    COMP_FUNCTIONS = {
        '=': operator.eq,
        '!=': operator.ne,
        '<': operator.lt,
        '<=': operator.le,
        '>': operator.gt,
        '>=': operator.ge,
        }

    COMP_REFLECTIONS = {
        '=': '=',
        '!=': '!=',
        '<': '>',
        '<=': '>=',
        '>': '<',
        '>=': '<=',
        }

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return '<%s: %r>' % (type(self).__name__, self.value)

    def coerce(self, object_type):
        if object_type in ('object', self.object_type):
            return self
        return getattr(self, 'to_%s' % (object_type.replace('-', '_'),))()

    def compare(self, other, operator):
        return XPathBoolean(self._xpath_cmp(other, operator))

    def _xpath_cmp(self, other, operator):
        raise NotImplementedError()


class XPathNodeSet(XPathObject):
    object_type = 'node-set'

    def __init__(self, value):
        self.value = list(sorted(value, key=lambda i: i._doc_position))

    def only(self):
        [node] = self.value
        return node

    def to_string(self):
        value = ''
        if self.value:
            value = self.value[0].string_value()
        return XPathString(value)

    def to_boolean(self):
        return XPathBoolean(len(self.value) != 0)

    def to_number(self):
        return self.to_string().to_number()

    def _xpath_cmp(self, other, operator):
        # This doesn't actually perform comparisons. It merely transforms
        # itself into something that does.

        # If one object to be compared is a node-set and the other is a
        # boolean, then the comparison will be true if and only if the result
        # of performing the comparison on the boolean and on the result of
        # converting the node-set to a boolean using the boolean function is
        # true.
        if other.object_type == 'boolean':
            return self.coerce('boolean')._xpath_cmp(other, operator)

        # The rest of these iterate over nodes until a successful comparison is
        # found.
        for node in self.value:
            # If both objects to be compared are node-sets, then the comparison
            # will be true if and only if there is a node in the first node-set
            # and a node in the second node-set such that the result of
            # performing the comparison on the string-values of the two nodes
            # is true.

            # If one object to be compared is a node-set and the other is a
            # string, then the comparison will be true if and only if there is
            # a node in the node-set such that the result of performing the
            # comparison on the string-value of the node and the other string
            # is true.
            node_val = XPathString(node.string_value())

            # If one object to be compared is a node-set and the other is a
            # number, then the comparison will be true if and only if there is
            # a node in the node-set such that the result of performing the
            # comparison on the number to be compared and on the result of
            # converting the string-value of that node to a number using the
            # number function is true.
            if other.object_type == 'number':
                node_val = node_val.to_number()

            if node_val._xpath_cmp(other, operator):
                return True

        # Otherwise return False.
        return False


class XPathBoolean(XPathObject):
    object_type = 'boolean'

    def to_string(self):
        return XPathString({True: 'true', False: 'false'}[self.value])

    def to_number(self):
        return XPathNumber({True: 1, False: 0}[self.value])

    def _xpath_cmp(self, other, operator):
        # Only node-sets understand how to unpack themselves for comparison.
        if other.object_type == 'node-set':
            return other._xpath_cmp(self, self.COMP_REFLECTIONS[operator])

        # When neither object to be compared is a node-set and the operator is
        # = or !=, then the objects are compared by converting them to a common
        # type as follows and then comparing them.
        if operator in ('=', '!='):
            # If at least one object to be compared is a boolean, then each
            # object to be compared is converted to a boolean as if by applying
            # the boolean function.
            return self.COMP_FUNCTIONS[operator](
                self.value, other.coerce('boolean').value)

        # When neither object to be compared is a node-set and the operator is
        # <=, <, >= or >, then the objects are compared by converting both
        # objects to numbers and comparing the numbers according to IEEE 754.
        return self.to_number()._xpath_cmp(other, operator)


class XPathNumber(XPathObject):
    object_type = 'number'

    def to_string(self):
        if math.isnan(self.value):
            val = "NaN"
        elif math.isinf(self.value):
            if self.value > 0:
                val = "Infinity"
            else:
                val = "-Infinity"
        elif self.value == int(self.value):
            val = str(int(self.value))
        else:
            val = ("%.16g" % (self.value,)).rstrip('0')
            # val = str(self.value)
        return XPathString(val)

    def to_boolean(self):
        if str(self.value) == str(float("nan")):
            return XPathBoolean(False)
        return XPathBoolean(self.value != 0)

    def _xpath_cmp(self, other, operator):
        # Only node-sets understand how to unpack themselves for comparison.
        if other.object_type == 'node-set':
            return other._xpath_cmp(self, self.COMP_REFLECTIONS[operator])

        # When neither object to be compared is a node-set and the operator is
        # = or !=, then the objects are compared by converting them to a common
        # type as follows and then comparing them.
        if operator in ('=', '!='):
            # If at least one object to be compared is a boolean, then each
            # object to be compared is converted to a boolean as if by applying
            # the boolean function.
            if other.object_type == 'boolean':
                return self.to_boolean()._xpath_cmp(other, operator)

            # Otherwise, if at least one object to be compared is a number,
            # then each object to be compared is converted to a number as if by
            # applying the number function.
            return self.COMP_FUNCTIONS[operator](
                self.value, other.coerce('number').value)

        # When neither object to be compared is a node-set and the operator is
        # <=, <, >= or >, then the objects are compared by converting both
        # objects to numbers and comparing the numbers according to IEEE 754.
        return self.COMP_FUNCTIONS[operator](
            self.value, other.coerce('number').value)


class XPathString(XPathObject):
    object_type = 'string'

    def __init__(self, value):
        self.value = value or ''

    def to_number(self):
        try:
            val = float(self.value)
        except ValueError:
            val = float("nan")
        if str(val) in (str(float("inf")), str(float("-inf"))):
            val = float("nan")
        return XPathNumber(val)

    def to_boolean(self):
        return XPathBoolean(len(self.value) != 0)

    def _xpath_cmp(self, other, operator):
        # Only node-sets understand how to unpack themselves for comparison.
        if other.object_type == 'node-set':
            return other._xpath_cmp(self, self.COMP_REFLECTIONS[operator])

        # When neither object to be compared is a node-set and the operator is
        # = or !=, then the objects are compared by converting them to a common
        # type as follows and then comparing them.
        if operator in ('=', '!='):
            # If at least one object to be compared is a boolean, then each
            # object to be compared is converted to a boolean as if by applying
            # the boolean function.
            if other.object_type == 'boolean':
                return self.to_boolean()._xpath_cmp(other, operator)

            # Otherwise, if at least one object to be compared is a number,
            # then each object to be compared is converted to a number as if by
            # applying the number function.
            if other.object_type == 'number':
                return self.to_number()._xpath_cmp(other, operator)

            # Otherwise, both objects to be compared are converted to strings
            # as if by applying the string function.
            return self.COMP_FUNCTIONS[operator](
                self.value, other.coerce('string').value)

        # When neither object to be compared is a node-set and the operator is
        # <=, <, >= or >, then the objects are compared by converting both
        # objects to numbers and comparing the numbers according to IEEE 754.
        return self.to_number()._xpath_cmp(other, operator)


# XPath function infrastructure

def xpath_function(*arg_types, **kw):
    def func_deco(func):
        name = kw.get('name', func.__name__.replace('_', '-'))
        return_type = kw.get('rtype', 'object')

        def wrapper(self, ctx, *args):
            args = self._process_args(arg_types, args)
            result = func(ctx, *args)
            return self._process_result(return_type, result)

        wrapper.xpath_name = name
        wrapper.xpath_arg_types = arg_types
        wrapper.xpath_return_type = return_type
        return wrapper
    return func_deco


class FunctionLibrary(object):
    def __init__(self, prefix=None):
        self._prefix = prefix
        self._collect_functions()

    def _collect_functions(self):
        self._functions = {}
        for attr in dir(self):
            obj = getattr(self, attr)
            xpath_name = getattr(obj, 'xpath_name', None)
            if xpath_name is not None:
                self._functions[xpath_name] = obj

    def _process_args(self, arg_types, args):
        # TODO: Validate arg_types?
        out_args = []
        args = list(args)
        arg_types = list(arg_types)

        while args:
            arg = args.pop(0)
            arg_type = arg_types.pop(0)

            if arg_type.endswith('*'):
                arg_types.append(arg_type)
                arg_type = arg_type[:-1]
            elif arg_type.endswith('?'):
                arg_type = arg_type[:-1]

            out_args.append(arg.coerce(arg_type))

        return out_args

    def _process_result(self, return_type, result):
        # TODO: Something useful here?
        if return_type == 'object':
            return result
        assert result.object_type == return_type, "%s != %s" % (
            result.object_type, return_type)
        return result

    def __getitem__(self, name):
        return self._functions[name]

    def __contains__(self, name):
        return name in self._functions


# XPath node types

class XPathNode(object):
    node_type = None

    def _build_node(self):
        pass

    def string_value(self):
        raise NotImplementedError()

    def expanded_name(self):
        return None

    def _walk_in_doc_order(self):
        yield self
        for child in self.get_children():
            for node in child._walk_in_doc_order():
                yield node

    def get_children(self):
        return ()

    def get_attributes(self):
        return ()

    def get_descendants(self, with_self=False):
        if with_self:
            yield self
        for child in self.get_children():
            yield child
            for desc in child.get_descendants():
                yield desc

    def get_parents(self):
        # The silly name is so that we can return a zero-or-one list to handle
        # the root element not having a parent.
        return [self.parent]

    def get_ancestors(self, with_self=False):
        if with_self:
            yield self
        parents = self.get_parents()
        while parents:
            [parent] = parents
            yield parent
            parents = parent.get_parents()

    def _after(self, nodeiter):
        # Drop all nodes until we find self.
        nodeiter = dropwhile(lambda n: n is not self, nodeiter)
        # Drop self
        nodeiter.next()
        return nodeiter

    def get_preceeding(self, only_siblings=False):
        # TODO: Find a better way.
        if only_siblings:
            # Get all siblings in reverse document order.
            for sib in self._after(reversed(list(self.parent.get_children()))):
                yield sib
            return

        # Otherwise get all nodes in reverse document order.
        ancestors = set(self.get_ancestors())
        nodeiter = self._after(
            reversed(list(self.get_root().get_descendants())))
        for node in nodeiter:
            if node not in ancestors:
                yield node

    def get_following(self, only_siblings=False):
        # TODO: Find a better way.
        if only_siblings:
            # Get all siblings in document order.
            return self._after(self.parent.get_children())
        # Get all nodes in document order.
        nodeiter = self._after(self.get_root().get_descendants())
        descendants = list(self.get_descendants())
        if descendants:
            nodeiter = dropwhile(lambda n: n is not descendants[-1], nodeiter)
            next(nodeiter)
        return nodeiter

    def get_root(self):
        return self.parent.get_root()


class XPathRootNode(XPathNode):
    node_type = 'root'

    def __init__(self, document, namespaces):
        self._document = document
        self._namespaces = namespaces
        self._children = None
        self._xml_ids = {}
        self._build_tree()

    def _build_tree(self):
        self._build_node()
        for i, node in enumerate(self._walk_in_doc_order()):
            node._doc_position = i
            if isinstance(node, XPathElementNode) and node.xml_id is not None:
                self._xml_ids.setdefault(node.xml_id, node)

    def _build_node(self):
        # TODO: Build non-element children.
        if self._children is None:
            self._children = [XPathElementNode(self, self._document.getroot())]

    def get_children(self):
        return self._children[:]

    def get_parents(self):
        return []

    def string_value(self):
        # Concatenation of all Text node descendants.
        return u''.join(n.string_value()
                        for n in self.get_descendants(XPathTextNode)
                        if n.node_type == 'text')

    def get_preceeding(self, only_siblings=False):
        return ()

    def get_following(self, only_siblings=False):
        return ()

    def get_root(self):
        return self

    def to_et(self):
        raise NotImplementedError()


class XPathElementNode(XPathNode):
    node_type = 'element'

    def __init__(self, parent, enode):
        self.parent = parent
        self._enode = enode
        self.prefix, self.name = split_eqname(enode.tag)
        self._children = None
        self._attributes = None
        self.xml_id = None
        self._build_node()

    def _build_node(self):
        self._attributes = []
        # We sort attributes in lexicographic order for determinism.
        for attr, value in sorted(self._enode.attrib.items()):
            self._attributes.append(XPathAttributeNode(self, attr, value))
            # TODO: Choose an appropriate ID attribute based on the DTD?
            if attr == 'id':
                self.xml_id = value

        # TODO: Build non-{element, text} children.
        self._children = []
        if self._enode.text is not None:
            self._children.append(XPathTextNode(self, self._enode.text))
        for enode in self._enode:
            self._children.append(XPathElementNode(self, enode))
            if enode.tail is not None:
                self._children.append(XPathTextNode(self, enode.tail))

    def _walk_in_doc_order(self):
        yield self
        # TODO: Namespace nodes.
        for attr in self.get_attributes():
            for node in attr._walk_in_doc_order():
                yield node
        for child in self.get_children():
            for node in child._walk_in_doc_order():
                yield node

    def get_children(self):
        return self._children[:]

    def get_attributes(self):
        return self._attributes[:]

    def expanded_name(self):
        return (self.prefix, self.name)

    def string_value(self):
        # Concatenation of all Text node descendants.
        return u''.join(n.string_value()
                        for n in self.get_descendants(XPathTextNode)
                        if n.node_type == 'text')

    def __repr__(self):
        return u'<XPathElementNode %s>' % (eqname(self.prefix, self.name),)

    def to_et(self):
        elem = ET.Element(eqname(self.prefix, self.name))
        for attr in self.get_attributes():
            elem.set(eqname(attr.prefix, attr.name), attr.value)

        prior_elem = None
        for node in self.get_children():
            if node.node_type == 'text':
                if prior_elem is None:
                    elem.text = node.text
                else:
                    prior_elem.tail = node.text
            elif node.node_type == 'element':
                prior_elem = node.to_et()
                elem.append(prior_elem)
            else:
                raise NotImplementedError()

        return elem

    def remove_child(self, child):
        self._children.remove(child)


class XPathAttributeNode(XPathNode):
    node_type = 'attribute'

    def __init__(self, parent, name, value):
        self.parent = parent
        self.prefix, self.name = split_eqname(name)
        self.value = value

    def expanded_name(self):
        return (self.prefix, self.name)

    def string_value(self):
        # TODO: Figure out what this means.
        return self.value

    def __repr__(self):
        return u'<XPathAttributeNode %s=%r>' % (eqname(self.prefix, self.name),
                                                self.value)

    def _after(self, nodeiter):
        # Drop all nodes until we find parent.
        nodeiter = dropwhile(lambda n: n is not self.parent, nodeiter)
        # Drop parent
        nodeiter.next()
        return nodeiter

    def get_preceeding(self, only_siblings=False):
        if only_siblings:
            return ()
        return XPathNode.get_preceeding(self)

    def get_following(self, only_siblings=False):
        if only_siblings:
            return ()
        return XPathNode.get_following(self)


class XPathNamespaceNode(XPathNode):
    node_type = 'namespace'

    def __init__(self, parent, prefix, uri):
        self.parent = parent
        self._prefix = prefix
        self._uri = uri

    def expanded_name(self):
        return (None, self._prefix)

    def string_value(self):
        return self._uri

    def _after(self, nodeiter):
        # Drop all nodes until we find parent.
        nodeiter = dropwhile(lambda n: n is not self.parent, nodeiter)
        # Drop parent
        nodeiter.next()
        return nodeiter

    def get_preceeding(self, only_siblings=False):
        if only_siblings:
            return ()
        return XPathNode.get_preceeding(self)

    def get_following(self, only_siblings=False):
        if only_siblings:
            return ()
        return XPathNode.get_following(self)


class XPathTextNode(XPathNode):
    node_type = 'text'

    def __init__(self, parent, text):
        self.parent = parent
        self.text = text

    def string_value(self):
        return self.text

    def __repr__(self):
        return u'<XPathTextNode %r>' % (self.text,)


class XPathProcessingInstructionNode(XPathNode):
    node_type = 'processing-instruction'

    def __init__(self, parent, enode):
        # TODO: Implement this?
        raise NotImplementedError()


class XPathCommentNode(XPathNode):
    node_type = 'comment'

    def __init__(self, parent, enode):
        # TODO: Implement this?
        raise NotImplementedError()
