# -*- test-case-name: xpathlet.tests.test_engine -*-

import math
import operator

from xpathlet import ast
from xpathlet.parser import parser
# from xpathlet.new_parser import parser
from xpathlet.constants import XML_NAMESPACE
from xpathlet.data_model import (
    XPathRootNode, XPathNodeSet, XPathNumber, XPathString, XPathBoolean)
from xpathlet.core_functions import CoreFunctionLibrary


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
            return context.node.get_following(only_siblings=True)

        if self.axis == 'preceding-sibling':
            return context.node.get_preceeding(only_siblings=True)

        if self.axis == 'following':
            return context.node.get_following()

        if self.axis == 'preceding':
            return context.node.get_preceeding()

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
    def __init__(self, node, position, size, variables, functions, namespaces,
                 expression=None, root_node=None, metadata=None,
                 trace_collector=None):
        self.node = node
        self.position = position
        self.size = size
        self.variables = variables
        self.functions = functions
        self.namespaces = dict({'xml': XML_NAMESPACE}, **namespaces)
        self.expression = expression
        self.root_node = root_node
        self.metadata = metadata or {}
        self.trace_collector = trace_collector

    def sub_context(self, node=None, position=None, size=None):
        if node is None:
            node = self.node
        if position is None:
            position = self.position
        if size is None:
            size = self.size
        return Context(node, position, size, self.variables, self.functions,
                       self.namespaces, self.expression, self.root_node,
                       self.metadata, self.trace_collector)

    def expand_qname(self, qname):
        prefix, name = '', qname
        if ':' in qname:
            prefix, name = qname.split(':')
        # Ignore the default namespace here.
        uri = None
        if prefix:
            uri = self.namespaces[prefix]
        return (uri, name)

    def __repr__(self):
        return u'<Context %r, %s/%s>' % (self.node, self.position, self.size)

    def start_trace(self, expr_node):
        if self.trace_collector is not None:
            return self.trace_collector.start_step(
                self.expression, expr_node,
                self.root_node, self.node, self.position, self.size)

    def finish_trace(self, step_id, result):
        if step_id is not None:
            self.trace_collector.finish_step(step_id, result)


class ExpressionEngine(object):
    def __init__(self, root_node, variables=None, function_libraries=None,
                 debug=False):
        self.debug = debug
        self.root_node = root_node
        if variables is None:
            variables = {}
        self.variables = variables
        self.function_libraries = [CoreFunctionLibrary()]
        if function_libraries is not None:
            self.function_libraries.extend(function_libraries)

    def dp(self, *args):
        if self.debug:
            print u' '.join(str(a) for a in args)

    def evaluate(self, xpath_expr, context_node=None, variables=None,
                 context_position=1, context_size=1, metadata=None,
                 trace_collector=None):
        if context_node is None:
            context_node = self.root_node
        if variables is None:
            variables = self.variables
        expr = parser.parse(xpath_expr)
        context = Context(context_node, context_position, context_size,
                          variables.copy(), {}, self.root_node._namespaces,
                          expr, self.root_node, metadata, trace_collector)
        return self._eval_expr(context, expr)

    def _eval_expr(self, context, expr):
        self.dp('\n====')
        self.dp('eval:', type(expr).__name__)
        self.dp(' context:', context)
        self.dp(' expr:', expr)

        eval_func = {
            ast.PathExpr: self._eval_path_expr,
            ast.FilterExpr: self._eval_filter_expr,
            ast.AbsoluteLocationPath: self._eval_location_path,
            ast.LocationPath: self._eval_location_path,
            ast.Step: self._eval_path_step,
            ast.Predicate: self._eval_predicate,
            ast.Number: self._eval_number,
            ast.StringLiteral: self._eval_string_literal,
            ast.VariableReference: self._eval_variable_reference,
            ast.FunctionCall: self._eval_function_call,
            ast.OperatorExpr: self._eval_operator_expr,
            ast.UnaryExpr: self._eval_unary_expr,
            }.get(type(expr), self._bad_ast)
        trace_id = context.start_trace(expr)
        result = eval_func(context, expr)
        context.finish_trace(trace_id, result)

        self.dp('result:', result)
        return result

    def _bad_ast(self, context, expr):
        raise NotImplementedError('AST eval: %s' % (type(expr),))

    def _eval_path_expr(self, context, expr):
        nodes = set(self._eval_expr(context, expr.left).value)
        return self._apply_location_path(context, expr.right, nodes)

    def _eval_filter_expr(self, context, filter_expr):
        node_set = self._eval_expr(context, filter_expr.expr)
        assert node_set.object_type == 'node-set'

        nodes = [(i + 1, n) for i, n in enumerate(node_set.value)]
        nodes = self._filter_predicates(context, filter_expr.predicates, nodes)
        return XPathNodeSet([n for _i, n in nodes])

    def _eval_location_path(self, context, expr):
        nodes = set([context.node])
        if expr.absolute:
            nodes = set([context.node.get_root()])
        return self._apply_location_path(context, expr, nodes)

    def _apply_location_path(self, context, expr, nodes):
        assert isinstance(expr, ast.LocationPath)
        for step in expr.steps:
            assert isinstance(step, ast.Step)
            new_nodes = set()
            for node in nodes:
                new_nodes.update(self._eval_expr(
                        context.sub_context(node=node), step).value)
            nodes = new_nodes

        return XPathNodeSet(nodes)

    def _eval_path_step(self, context, step):
        axis = Axis(step.axis)

        nodes = []
        i = 1
        for node in axis.select_nodes(context):
            if self._test_node(context, step.node_test, axis, node):
                nodes.append((i, node))
                i += 1

        nodes = self._filter_predicates(context, step.predicates, nodes)
        return XPathNodeSet([node for _i, node in nodes])

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

    def _filter_predicates(self, context, predicates, nodes):
        for predicate in predicates:
            assert isinstance(predicate, ast.Predicate)
            new_nodes = self._filter_predicate(context, predicate, nodes)
            if not new_nodes:
                return []
            nodes = [(i + 1, n[1]) for i, n in enumerate(sorted(new_nodes))]
        return nodes

    def _filter_predicate(self, context, predicate, nodes):
        ctx = context.sub_context(size=len(nodes))
        new_nodes = []
        for i, node in nodes:
            if self._eval_expr(
                ctx.sub_context(node, position=i), predicate).value:
                new_nodes.append((i, node))
        return new_nodes

    def _eval_predicate(self, context, predicate):
        result = self._eval_expr(context, predicate.expr)
        if isinstance(result, XPathNumber):
            return XPathBoolean(result.value == context.position)
        return result.coerce('boolean')

    def _eval_number(self, context, number):
        return XPathNumber(number.value)

    def _eval_string_literal(self, context, string_literal):
        return XPathString(string_literal.value)

    def _eval_variable_reference(self, context, variable_reference):
        return context.variables[variable_reference.name]

    def _eval_function_call(self, context, function_call):
        # TODO: Context function libraries?
        args = [self._eval_expr(context, arg) for arg in function_call.args]
        for func_lib in reversed(self.function_libraries):
            if function_call.name in func_lib:
                return func_lib[function_call.name](context, *args)
        raise ValueError("Undefined function: '%s'" % (function_call.name,))

    def _eval_operator_expr(self, context, operator_expr):
        if operator_expr.op in ('and', 'or'):
            return self._apply_boolean_op(context, operator_expr)

        left = self._eval_expr(context, operator_expr.left)
        right = self._eval_expr(context, operator_expr.right)

        if operator_expr.op == '|':
            assert all(n.object_type == 'node-set' for n in (left, right))
            return XPathNodeSet(set(left.value) | set(right.value))

        if operator_expr.op in set(['=', '!=', '<=', '<', '>=', '>']):
            return left.compare(right, operator_expr.op)

        if operator_expr.op in set(['+', '-', '*', 'div', 'mod']):
            return self._apply_numeric_op(operator_expr.op, left, right)

        raise NotImplementedError()

    def _apply_boolean_op(self, context, operator_expr):
        left = self._eval_expr(context, operator_expr.left).coerce('boolean')

        if (operator_expr.op == 'and') and (not left.value):
            return left
        elif (operator_expr.op == 'or') and left.value:
            return left

        return self._eval_expr(context, operator_expr.right).coerce('boolean')

    def _apply_numeric_op(self, op, left, right):
        left = left.coerce('number').value
        right = right.coerce('number').value
        op_func = {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            'div': operator.div,
            'mod': math.fmod,
            }[op]
        try:
            return XPathNumber(op_func(left, right))
        except ZeroDivisionError:
            if left == 0:
                return XPathNumber(float('nan'))
            return XPathNumber(left * math.copysign(float('inf'), right))

    def _eval_unary_expr(self, context, unary_expr):
        assert unary_expr.op == '-'
        val = self._eval_expr(context, unary_expr.expr).coerce('number')
        return XPathNumber(operator.neg(val.value))
