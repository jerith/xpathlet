# -*- test-case-name: xpathlet.tests.test_parser -*-


class Node(object):
    def to_str(self):
        raise NotImplementedError()

    def __repr__(self):
        return u"<%s: %s>" % (type(self).__name__, self.value)


def _to_str(thing):
    if isinstance(thing, Node):
        return thing.to_str()
    if thing is None:
        return u''
    return u'%s' % (thing,)


AXIS_NAMES = set([
        'ancestor',
        'ancestor-or-self',
        'attribute',
        'child',
        'descendant',
        'descendant-or-self',
        'following',
        'following-sibling',
        'namespace',
        'parent',
        'preceding',
        'preceding-sibling',
        'self',
        ])


def normalise_axis(name):
    if name == '@':
        name = 'attribute'
    assert name in AXIS_NAMES
    return name


class Step(Node):
    def __init__(self, axis, node_test, predicates):
        self.axis = axis
        self.node_test = node_test
        self.predicates = predicates

    def __repr__(self):
        return u'<Step %s::%s %s>' % (
            self.axis, self.node_test, self.predicates)

    def to_str(self):
        return u'%s::%s%s' % (self.axis, self.node_test.to_str(),
                              u''.join(p.to_str() for p in self.predicates))


class NodeType(Node):
    def __init__(self, node_type, param=None):
        self.node_type = node_type
        if param is not None:
            assert node_type == 'processing-instruction'
        self.param = param

    def __repr__(self):
        return u'<NodeType %s(%s)>' % (self.node_type, self.param or '')

    def to_str(self):
        return u'%s(%s)' % (self.node_type, _to_str(self.param))


class NameTest(Node):
    def __init__(self, *bits):
        self.name = u''.join(bits)

    def __repr__(self):
        return u'<NameTest %s>' % self.name

    def to_str(self):
        return self.name


class Predicate(Node):
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return u'<Predicate %s>' % self.expr

    def to_str(self):
        return u'[%s]' % (self.expr.to_str(),)


class LocationPath(Node):
    absolute = False

    def __init__(self, *steps):
        self.steps = []
        for step in steps:
            if step == '/':
                # Ignore these.
                pass
            elif isinstance(step, LocationPath):
                self.steps.extend(step.steps)
            else:
                self.steps.append(step)

    def __repr__(self):
        return u"<%s: %s>" % (type(self).__name__, self.steps)

    def to_str(self):
        return u'/'.join(_to_str(s) for s in self.steps)


class AbsoluteLocationPath(LocationPath):
    absolute = True

    def to_str(self):
        return u'/' + super(AbsoluteLocationPath, self).to_str()


class PathExpr(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return u"<PathExpr: (%s, %s)>" % (self.left, self.right)

    def to_str(self):
        return u'%s/%s' % (_to_str(self.left), _to_str(self.right))


class FilterExpr(Node):
    def __init__(self, expr, predicate=None):
        self.expr = expr
        self.predicates = []
        if isinstance(expr, FilterExpr):
            self.expr = expr.expr
            self.predicates.extend(expr.predicates)
        if predicate is not None:
            self.predicates.append(predicate)

    def __repr__(self):
        return u"<FilterExpr: %s %s>" % (self.expr, self.predicates)

    def to_str(self):
        return u'%s%s' % (self.expr.to_str(),
                          u''.join(p.to_str() for p in self.predicates))


class OperatorExpr(Node):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def __repr__(self):
        return u"<OperatorExpr %s: (%s, %s)>" % (
            self.op, self.left, self.right)

    def to_str(self):
        return u'%s %s %s' % (_to_str(self.left), self.op, _to_str(self.right))


class UnaryExpr(Node):
    def __init__(self, op, expr):
        self.op = op
        self.expr = expr

    def __repr__(self):
        return u"<UnaryExpr %s: (%s, %s)>" % (
            self.op, self.left, self.right)

    def to_str(self):
        return u'%s%s' % (self.op, _to_str(self.right))


class VariableReference(Node):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return u"<VariableReference: %s>" % (self.name,)

    def to_str(self):
        return u'$%s' % (self.name,)


class FunctionCall(Node):
    def __init__(self, name, *args):
        self.name = name
        self.args = args

    def __repr__(self):
        return u"<FunctionCall %s: %s>" % (self.name, self.args)

    def to_str(self):
        return u'%s(%s)' % (self.name,
                            u', '.join(_to_str(a) for a in self.args))


class StringLiteral(Node):
    def __init__(self, value):
        self.value = value

    def to_str(self):
        # TODO: What about non-ASCII, etc.?
        return repr(self.value).lstrip('u')


class Number(Node):
    def __init__(self, value):
        self.value = float(value)

    def to_str(self):
        # TODO: What about non-ASCII, etc.?
        return repr(self.value)
