class Node(object):
    pass


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
    def __init__(self, axis, node_test, *predicates):
        self.axis = axis
        self.node_test = node_test
        self.predicates = predicates

    def __repr__(self):
        return u'<Step %s::%s %s>' % (
            self.axis, self.node_test, self.predicates)


class NodeType(Node):
    def __init__(self, node_type, param=None):
        self.node_type = node_type
        if param is not None:
            assert node_type == 'processing-instruction'
        self.param = param

    def __repr__(self):
        return u'<NodeType %s(%s)>' % (self.node_type, self.param or '')


class NameTest(Node):
    def __init__(self, *bits):
        self.name = u''.join(bits)

    def __repr__(self):
        return u'<NameTest %s>' % self.name


class Predicate(Node):
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return u'<Predicate %s>' % self.expr


class LocationPath(Node):
    def __init__(self, *steps):
        self.steps = []
        for step in steps:
            if isinstance(step, LocationPath):
                self.steps.extend(step.steps)
            else:
                self.steps.append(step)

    def __repr__(self):
        return u"<LocationPath: %s>" % (self.steps,)


class PathExpr(Node):
    def __init__(self, *parts):
        self.parts = parts

    def __repr__(self):
        return u"<PathExpr: %s>" % (self.parts,)


class FilterExpr(Node):
    def __init__(self, expr, predicate=None):
        self.expr = expr
        self.predicates = []
        if isinstance(expr, FilterExpr):
            self.expr = expr.expr
            self.predicates.extend(expr.predicates)
        if predicate is not None:
            self.predicates.appen(predicate)

    def __repr__(self):
        return u"<FilterExpr: %s %s>" % (self.expr, self.predicates)


class OperatorExpr(Node):
    def __init__(self, op, *parts):
        self.op = op
        self.parts = []
        for part in parts:
            # if isinstance(part, OperatorExpr) and part.op == op:
            #     self.parts.extend(part.parts)
            # else:
            #     self.parts.append(part)
            self.parts.append(part)

    def __repr__(self):
        return u"<OperatorExpr %s: %s>" % (self.op, self.parts)


class UnaryExpr(Node):
    def __init__(self, op, expr):
        self.op = op
        self.expr = expr

    def __repr__(self):
        return u"<UnaryExpr %s: %s>" % (self.op, self.parts)


class VariableReference(Node):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return u"<VariableReference: %s>" % (self.name,)


class FunctionCall(Node):
    def __init__(self, name, *args):
        self.name = name
        self.args = args

    def __repr__(self):
        return u"<FunctionCall %s: %s>" % (self.name, self.args)
