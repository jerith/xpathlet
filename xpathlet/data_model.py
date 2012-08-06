# -*- test-case-name: xpathlet.tests.test_engine -*-

from itertools import dropwhile


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

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return u'<%s: %s>' % (type(self).__name__, self.value)

    def coerce(self, object_type):
        if object_type in ('object', self.object_type):
            return self
        return getattr(self, 'to_%s' % (object_type.replace('-', '_'),))()


class XPathNodeSet(XPathObject):
    object_type = 'node-set'

    def only(self):
        [node] = self.value
        return node

    def to_string(self):
        # TODO: implement this
        raise NotImplementedError()

    def to_boolean(self):
        return XPathBoolean(len(self.value) != 0)

    def to_number(self):
        return self.to_string().to_number()


class XPathBoolean(XPathObject):
    object_type = 'boolean'

    def to_string(self):
        return XPathString({
                True: 'true',
                False: 'false',
                }[self.value])

    def to_number(self):
        return XPathNumber({
                True: 1,
                False: 0,
                }[self.value])


class XPathNumber(XPathObject):
    object_type = 'number'

    def to_string(self):
        # TODO: implement this
        raise NotImplementedError()

    def to_boolean(self):
        return XPathBoolean(self.value != 0)

    def to_number(self):
        # TODO: implement this
        raise NotImplementedError()


class XPathString(XPathObject):
    object_type = 'string'

    def to_boolean(self):
        return XPathBoolean(len(self.value) != 0)


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
        args = args[:]
        arg_types = arg_types[:]

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
        assert result.object_type == return_type
        return result

    def __getitem__(self, name):
        return self._functions[name]

    def __contains__(self, name):
        return name in self._functions


# XPath node types

class XPathNode(object):
    node_type = None

    def string_value(self):
        raise NotImplementedError

    def expanded_name(self):
        return None

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
        if only_siblings:
            # Get all siblings in reverse document order.
            return self._after(reversed(list(self.parent.get_children())))

        # Otherwise get all nodes in reverse document order.
        return self._after(reversed(list(self.get_root().get_descendants())))

    def get_following(self, only_siblings=False):
        if only_siblings:
            # Get all siblings in document order.
            return self._after(self.parent.get_children())
        # Get all nodes in document order.
        return self._after(self.get_root().get_descendants())

    def get_root(self):
        return self.parent.get_root()


class XPathRootNode(XPathNode):
    node_type = 'root'

    def __init__(self, document, namespaces):
        self._document = document
        self._namespaces = namespaces
        self._children = None
        # Unlazy this for now.
        self.get_children()

    def get_children(self):
        # TODO: Build non-element children.
        if self._children is None:
            self._children = [XPathElementNode(self, self._document.getroot())]
        return self._children

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
        if only_siblings:
            return ()
        return self.get_descendants()

    def get_root(self):
        return self


class XPathElementNode(XPathNode):
    node_type = 'element'

    def __init__(self, parent, enode):
        self.parent = parent
        self._enode = enode
        self.prefix, self.name = split_eqname(enode.tag)
        self._children = None
        self._attributes = None
        self.xml_id = None
        # Unlazy this for now.
        self.get_children()

    def get_children(self):
        # TODO: Build non-{element, text} children.
        if self._children is None:
            self._children = []
            if self._enode.text is not None:
                self._children.append(XPathTextNode(self, self._enode.text))
            for enode in self._enode:
                self._children.append(XPathElementNode(self, enode))
                if enode.tail is not None:
                    self._children.append(XPathTextNode(self, enode.tail))
        return self._children

    def get_attributes(self):
        if self._attributes is None:
            self._attributes = [XPathAttributeNode(self, k, v)
                                for k, v in self._enode.attrib.items()]
        return self._attributes

    def expanded_name(self):
        return (self.prefix, self.name)

    def string_value(self):
        # Concatenation of all Text node descendants.
        return u''.join(n.string_value()
                        for n in self.get_descendants(XPathTextNode)
                        if n.node_type == 'text')

    def __repr__(self):
        return u'<XPathElementNode %s>' % (eqname(self.prefix, self.name),)


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
