import re

import parsley

from xpathlet import ast


_ncname_start_chars = (
    u'a-zA-Z_'
    u'\u00C0-\u00D6'
    u'\u00D8-\u00F6'
    u'\u00F8-\u02FF'
    u'\u0370-\u037D'
    u'\u037F-\u1FFF'
    u'\u200C-\u200D'
    u'\u2070-\u218F'
    u'\u2C00-\u2FEF'
    u'\u3001-\uD7FF'
    u'\uF900-\uFDCF'
    u'\uFDF0-\uFFFD'
    # u'\u10000-\uEFFFF'
    )

_ncname_chars = u''.join([
        u'-.0-9', _ncname_start_chars,
        unichr(0xB7),
        u'\u0300-\u036F',
        u'\u203F-\u2040',
        ])

_ncname_start_char_re = re.compile(u'[%s]' % (_ncname_start_chars,))
_ncname_char_re = re.compile(u'[%s]' % (_ncname_chars,))


def is_NCNameStartChar(ch):
    return _ncname_start_char_re.match(ch) is not None


def is_NCNameChar(ch):
    return _ncname_char_re.match(ch) is not None


def is_NodeType(text):
    return text in ['comment', 'text', 'processing-instruction', 'node']


def is_AxisName(text):
    return text in [
        'ancestor', 'ancestor-or-self', 'attribute', 'child', 'descendant',
        'descendant-or-self', 'following', 'following-sibling', 'namespace',
        'parent', 'preceding', 'preceding-sibling', 'self']


xpath_grammar = r"""
    # Basic name tokens
    # =================

    QName = <NCName ':' NCName> | <NCName>
    NCName = NCNameStartChar NCNameChar*

    NCNameStartChar = anything:x ?(is_NCNameStartChar(x)) -> x
    NCNameChar = anything:x ?(is_NCNameChar(x)) -> x

    # S = ' ' | '\t' | '\r' | '\n'

    # Location Paths (section 2)
    # ==========================

    DSlash = ws_token('//')
               -> ast.Step('descendant-or-self', ast.NodeType('node'))

    LocationPath = RelativeLocationPath
                 | AbsoluteLocationPath
    AbsoluteLocationPath = DSlash:d RelativeLocationPath:rlp
                             -> ast.AbsoluteLocationPath(d, rlp)
                         | '/' RelativeLocationPath?:rlp
                             -> ast.AbsoluteLocationPath(rlp)
    RelativeLocationPath = RelativeLocationPath:rlp DSlash:d Step:s
                             -> ast.LocationPath(rlp, d, s)
                         | RelativeLocationPath:rlp '/' Step:s
                             -> ast.LocationPath(rlp, s)
                         | Step:s -> ast.LocationPath(s)

    # Location Steps (section 2.1)
    # ============================

    Step = ws_token('..'):x -> ast.Step(x, None)
         | '.':x -> ast.Step(x, None)
         | AxisSpecifier:a NodeTest:nt Predicate*:ps -> ast.Step(a, nt, ps)
    AxisSpecifier = AxisName:an ws_token('::') -> an
                  | '@'?

    # Axes (section 2.2)
    # ==================

    AxisName = QName:x ?(is_AxisName(x)) -> x

    # Node Tests (section 2.3)
    # ========================

    NodeTest = token("processing-instruction")
                 ws_token('(') Literal ws_token(')')
                 -> ast.NodeType('processing-instruction')  # FIXME: Handle arg
             | NodeType:nt ws_token('(') ws_token(')') -> ast.NodeType(nt)
             | NameTest:nt -> ast.NameTest(nt)

    # Predicates (section 2.4)
    # ========================

    Predicate = ws_token('[') PredicateExpr:pe ws_token(']')
                  -> ast.Predicate(pe)
    PredicateExpr = Expr

    # Abbreviations (section 2.5)
    # ===========================

    # Merged into Location Path and Location Step rules above.

    # Expression Basics (section 3.1)
    # ===============================

    Expr = OrExpr
    PrimaryExpr = spaces ( VariableReference
                         | ws_token('(') Expr:e ws_token(')') -> e
                         | Literal
                         | Number
                         | FunctionCall )

    # Function Calls (section 3.2)
    # ============================

    FunctionCall = FunctionName:fn ws_token('(') Args:args ws_token(')')
                     -> ast.FunctionCall(fn, *args)
    Args = Expr:a NextArg*:args -> [a] + args
         | -> []
    NextArg = ws_token(',') Expr

    # Node Sets (section 3.3)
    # =======================

    UnionExpr = UnionExpr:ue ws_token('|') PathExpr:pe
                  -> ast.OperatorExpr('|', ue, pe)
              | PathExpr
    PathExpr = FilterExpr:fe DSlash:d RelativeLocationPath:rlp
                 -> ast.PathExpr(fe, ast.LocationPath(d, rlp))
             | FilterExpr:fe '/' RelativeLocationPath:rlp
                 -> ast.PathExpr(fe, rlp)
             | FilterExpr
             | LocationPath
    FilterExpr = FilterExpr:fe Predicate:p -> ast.FilterExpr(fe, p)
               | PrimaryExpr

    # Boolean Expressions (section 3.4)
    # =================================

    OrExpr = OrExpr:l ws_token('or') AndExpr:r -> ast.OperatorExpr('or', l, r)
           | AndExpr
    AndExpr = AndExpr:l ws_token('and') EqualityExpr:r
                -> ast.OperatorExpr('and', l, r)
            | EqualityExpr
    EqualityExpr = EqualityExpr:l ws_token('=') RelationalExpr:r
                     -> ast.OperatorExpr('=', l, r)
                 | EqualityExpr:l ws_token('!=') RelationalExpr:r
                     -> ast.OperatorExpr('!=', l, r)
                 | RelationalExpr
    RelationalExpr = RelationalExpr:l ws_token('<') AdditiveExpr:r
                      -> ast.OperatorExpr('<', l, r)
                   | RelationalExpr:l ws_token('>') AdditiveExpr:r
                      -> ast.OperatorExpr('>', l, r)
                   | RelationalExpr:l ws_token('<=') AdditiveExpr:r
                      -> ast.OperatorExpr('<=', l, r)
                   | RelationalExpr:l ws_token('>=') AdditiveExpr:r
                      -> ast.OperatorExpr('>=', l, r)
                   | AdditiveExpr

    # Numeric Expressions (section 3.5)
    # =================================

    AdditiveExpr = AdditiveExpr:l ws_token('+') MultiplicativeExpr:r
                     -> ast.OperatorExpr('+', l, r)
                 | AdditiveExpr:l ws_token('-') MultiplicativeExpr:r
                     -> ast.OperatorExpr('-', l, r)
                 | MultiplicativeExpr
    MultiplicativeExpr = MultiplicativeExpr:l ws_token('*') UnaryExpr:r
                           -> ast.OperatorExpr('*', l, r)
                       | MultiplicativeExpr:l ws_token('div') UnaryExpr:r
                           -> ast.OperatorExpr('div', l, r)
                       | MultiplicativeExpr:l ws_token('mod') UnaryExpr:r
                           -> ast.OperatorExpr('mod', l, r)
                       | UnaryExpr
    UnaryExpr = '-' UnaryExpr:ue -> ast.UnaryExpr('-', ue)
              | UnionExpr

    # Tokens (section 3.7)
    # ====================

    # ExprToken = S* ( <'.' '.'> | <':' ':'>
    #                | '(' | ')' | '[' | ']' | '.' | '@' | ',' |
    #                | NameTest
    #                | NodeType
    #                | Operator
    #                | FunctionName
    #                | AxisName
    #                | Literal
    #                | Number
    #                | VariableReference )
    Literal = '"' (~'"' anything)*:x '"' -> ast.StringLiteral(''.join(x))
            | "'" (~"'" anything)*:x "'" -> ast.StringLiteral(''.join(x))
    Number = <digit+ ('.' digit*)?>:x -> ast.Number(x)
           | <'.' digit+>:x -> ast.Number(x)
    # Operator = OperatorName
    #          | <'!' '='> | <'<' '='> | <'>' '='> | <'/' '/'>
    #          | MultiplyOperator
    #          | '/' | '|' | '+' | '-'
    #          | '=' | '<' | '>'
    # OperatorName = <'a' 'n' 'd'> | <'o' 'r'> | <'m' 'o' 'd'> | <'d' 'i' 'v'>
    # MultiplyOperator = '*'
    FunctionName = ~NodeType QName
    VariableReference = ws_token('$') QName:qn -> ast.VariableReference(qn)
    NameTest = '*'
             | <NCName ':' '*'>
             | QName
    NodeType = <NCName>:x ?(is_NodeType(x)) -> x

    ws_token :stuff = token(stuff):x spaces -> x
"""

xpath_parser = parsley.makeGrammar(xpath_grammar, {
    'is_NCNameStartChar': is_NCNameStartChar,
    'is_NCNameChar': is_NCNameChar,
    'is_NodeType': is_NodeType,
    'is_AxisName': is_AxisName,
    'ast': ast,
    })


class ParserWrapper(object):
    def parse(self, stream):
        return xpath_parser(stream).Expr()

parser = ParserWrapper()
