# -*- test-case-name: xpathlet.tests.test_engine -*-

from xpathlet import ast
from xpathlet.parser import parser


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


# XPath object types

class XPathObject(object):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return u'<%s: %s>' % (type(self).__name__, self.value)


class XPathNodeSet(XPathObject):
    def only(self):
        [node] = self.value
        return node


class XPathBoolean(XPathObject):
    pass


class XPathNumber(XPathObject):
    pass


class XPathString(XPathObject):
    pass


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

    def get_root_node(self):
        return self.parent.get_root_node()


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

    def get_root_node(self):
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


class Axis(object):
    def __init__(self, axis):
        assert axis in ast.AXIS_NAMES
        self.axis = axis

    @property
    def principal_node_type(self):
        return {
            'attribute': 'attribute',
            'namespace': 'namespace',
            }.get(self.axis, 'element')

    def select_nodes(self, context):
        if self.axis == 'child':
            return context.node.get_children()

        if self.axis == 'descendant':
            return context.node.get_descendants()

        if self.axis == 'parent':
            return context.node.get_parents()

        if self.axis == 'ancestor':
            return context.node.get_ancestors()

        if self.axis == 'following-sibling':
            pass

        if self.axis == 'preceding-sibling':
            pass

        if self.axis == 'following':
            pass

        if self.axis == 'preceding':
            pass

        if self.axis == 'attribute':
            return context.node.get_attributes()

        if self.axis == 'namespace':
            pass

        if self.axis == 'self':
            return [context.node]

        if self.axis == 'descendant-or-self':
            return context.node.get_descendants(with_self=True)

        if self.axis == 'ancestor-or-self':
            return context.node.get_ancestors(with_self=True)

        raise NotImplementedError('Axis %r' % (self.axis,))


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

    def expand_qname(self, qname):
        prefix, name = '', qname
        if ':' in qname:
            prefix, name = qname.split(':')
        uri = self.namespaces.get(prefix, None)
        return (uri, name)

    def __repr__(self):
        return u'<Context %r>' % (self.node,)


class ExpressionEngine(object):
    def __init__(self, root_node, debug=False):
        self.debug = debug
        self.root_node = root_node

    def dp(self, *args):
        if self.debug:
            print u' '.join(str(a) for a in args)

    def evaluate(self, xpath_expr, context_node=None):
        if context_node is None:
            context_node = self.root_node
        context = Context(context_node, 0, 0, {}, {},
                          self.root_node._namespaces)
        expr = parser.parse(xpath_expr)
        return self._eval_expr(context, expr, None)

    def _eval_expr(self, context, expr, inp):
        self.dp('\n====')
        self.dp('eval:', type(expr).__name__, inp)
        self.dp(' context:', context)
        self.dp(' expr:', expr)
        eval_func = {
            ast.AbsoluteLocationPath: self._eval_location_path,
            ast.LocationPath: self._eval_location_path,
            ast.Step: self._eval_path_step,
            }.get(type(expr), self._bad_ast)
        result = eval_func(context, expr, inp)
        self.dp('result:', result)
        return result

    def _bad_ast(self, context, expr, inp):
        raise NotImplementedError('AST eval: %s' % (type(expr),))

    def _eval_location_path(self, context, expr, inp):
        nodes = set([context.node])
        if expr.absolute:
            nodes = set([context.node.get_root_node()])

        for step in expr.steps:
            assert isinstance(step, ast.Step)
            new_nodes = set()
            for node in nodes:
                new_nodes.update(self._eval_expr(
                        context.sub_context(node=node), step, None))
            nodes = new_nodes

        return XPathNodeSet(nodes)

    def _eval_path_step(self, context, step, inp):
        axis = Axis(step.axis)

        nodes = set()
        for node in axis.select_nodes(context):
            if self._test_node(context, step.node_test, axis, node):
                nodes.add(node)

        for predicate in step.predicates:
            assert isinstance(predicate, ast.Predicate)
            raise NotImplementedError()

        return nodes

    def _test_node(self, context, test_expr, axis, node):
        if isinstance(test_expr, ast.NameTest):
            if node.node_type != axis.principal_node_type:
                return False
            if test_expr.name == '*':
                return True
            return node.expanded_name() == context.expand_qname(test_expr.name)

        if isinstance(test_expr, ast.NodeType):
            return test_expr.node_type in ('node', node.node_type)

        assert False
