# -*- test-case-name: xpathlet.tests.test_parser -*-

from ply import yacc

from xpathlet.lexer import tokens
from xpathlet import ast


def p_location_path(p):
    """LocationPath : RelativeLocationPath
                    | AbsoluteLocationPath
    """
    p[0] = p[1]


def p_absolute_location_path(p):
    """AbsoluteLocationPath : '/'
                            | '/' RelativeLocationPath
                            | DOUBLESLASH RelativeLocationPath
    """
    p[0] = ast.LocationPath(*p[1:])


def p_relative_location_path(p):
    """RelativeLocationPath : Step
                            | RelativeLocationPath '/' Step
                            | RelativeLocationPath DOUBLESLASH Step
    """
    p[0] = ast.LocationPath(*p[1:])


def p_step_with_axis(p):
    """Step : AxisSpecifier NodeTest Predicates
    """
    p[0] = ast.Step(*p[1:])


def p_step_without_axis(p):
    """Step : NodeTest Predicates
            | '.'
            | DOUBLEDOT
    """
    axis = 'child'  # The default axis
    node_test = ast.NodeType('node')  # The default NodeTest
    predicates = []

    if p[1] == '.':
        axis = 'self'
    elif p[1] == '..':
        axis = 'parent'
    else:
        node_test = p[1]
        predicates = p[2]

    p[0] = ast.Step(axis, node_test, *predicates)


def p_axis_specifier(p):
    """AxisSpecifier : NCName DOUBLECOLON
                     | '@'
    """
    p[0] = ast.normalise_axis(p[1])


def p_node_test(p):
    """NodeTest : NameTest
                | NODETYPE '(' ')'
                | NODETYPE '(' Literal ')'
    """
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 4:
        p[0] = ast.NodeType(p[1])
    else:
        p[0] = ast.NodeType(p[1], p[3])


def p_name_test(p):
    """NameTest : '*'
                | NCName ':' '*'
                | QName
    """
    p[0] = ast.NameTest(*p[1:])


def p_predicates(p):
    """Predicates : Predicates Predicate
                  | empty
    """
    if len(p) > 2:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = []


def p_predicate(p):
    """Predicate : '[' Expr ']'
    """
    p[0] = ast.Predicate(p[2])


def p_expr(p):
    """Expr : OrExpr
    """
    p[0] = p[1]


def p_primary_expr(p):
    """PrimaryExpr : VariableReference
                   | '(' Expr ')'
                   | Literal
                   | NUMBER
                   | FunctionCall
    """
    if p[1] == '(':
        p[0] = p[2]
    else:
        p[0] = p[1]


def p_function_call(p):
    """FunctionCall : FunctionName '(' Arguments ')'
    """
    p[0] = ast.FunctionCall(p[1], *p[3])


def p_arguments(p):
    """Arguments : Arguments ',' Expr
                 | Expr
    """
    if len(p) > 2:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]


def p_arguments_empty(p):
    """Arguments : empty
    """
    p[0] = []


def p_union_expr(p):
    """UnionExpr : PathExpr
                 | UnionExpr '|' PathExpr
    """
    if len(p) > 2:
        p[0] = ast.UnionExpr(p[1], p[3])
    else:
        p[0] = p[1]


def p_path_expr(p):
    """PathExpr : LocationPath
                | FilterExpr
                | FilterExpr '/' RelativeLocationPath
                | FilterExpr DOUBLESLASH RelativeLocationPath
    """
    if len(p) > 2:
        p[0] = ast.PathExpr(*p[1:])
    else:
        p[0] = p[1]


def p_filter_expr(p):
    """FilterExpr : PrimaryExpr
                  | FilterExpr Predicate
    """
    if len(p) > 2:
        p[0] = ast.FilterExpr(*p[1:])
    else:
        p[0] = p[1]


def p_operator_exprs(p):
    """OrExpr : AndExpr
              | OrExpr OP_OR AndExpr

       AndExpr : EqualityExpr
               | AndExpr OP_AND EqualityExpr

       EqualityExpr : RelationalExpr
                    | EqualityExpr '=' RelationalExpr
                    | EqualityExpr OP_NE RelationalExpr

       RelationalExpr : AdditiveExpr
                      | RelationalExpr '<' AdditiveExpr
                      | RelationalExpr '>' AdditiveExpr
                      | RelationalExpr OP_LE AdditiveExpr
                      | RelationalExpr OP_GE AdditiveExpr

       AdditiveExpr : MultiplicativeExpr
                    | AdditiveExpr '+' MultiplicativeExpr
                    | AdditiveExpr '-' MultiplicativeExpr

       MultiplicativeExpr : UnaryExpr
                          | MultiplicativeExpr '*' UnaryExpr
                          | MultiplicativeExpr OP_DIV UnaryExpr
                          | MultiplicativeExpr OP_MOD UnaryExpr
    """
    if len(p) > 2:
        p[0] = ast.OperatorExpr(p[2], p[1], p[3])
    else:
        p[0] = p[1]


def p_unary_expr(p):
    """UnaryExpr : UnionExpr
                 | '-' UnaryExpr
    """
    if len(p) > 2:
        p[0] = ast.UnaryExpr(p[1], p[2])
    else:
        p[0] = p[1]


def p_variable_reference(p):
    """VariableReference : '$' QName
    """
    p[0] = ast.VariableReference(p[2])


# There's a bit of madness below to allow us to handle node types and function
# names separately.

def p_ncname(p):
    """NCName : NCNAME
              | NODETYPE
    """
    p[0] = p[1]


def p_function_name(p):
    """FunctionName : NCNAME
                    | NCName ':' NCName
    """
    p[0] = u''.join(p[1:])


def p_qname(p):
    """QName : NCName
             | NCName ':' NCName
    """
    p[0] = u''.join(p[1:])


def p_literal(p):
    """Literal : LITERAL
    """
    p[0] = ast.Literal(p[1])


def p_empty(p):
    "empty :"


# To keep pyflakes happy:
tokens

start = 'Expr'
parser = yacc.yacc()
