# -*- test-case-name: xpathlet.tests.test_lexer -*-

import re

from ply import lex


tokens = (
    'LITERAL',
    'NUMBER',
    'NCNAME',
    'DOUBLECOLON',
    'DOUBLEDOT',
    'DOUBLESLASH',
    'OP_NE',
    'OP_LE',
    'OP_GE',
    'OP_AND',
    'OP_OR',
    'OP_MOD',
    'OP_DIV',
    'NODETYPE',
    )


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

_ncname = u'[%s][%s]*' % (_ncname_start_chars, _ncname_chars)


t_ignore = ' \t\r\n'


def t_LITERAL(t):
    '''("[^"]*")|('[^']*')'''
    t.value = t.value[1:-1]
    return t

t_NUMBER = r'([0-9]+(\.([0-9]+)?)?)|(\'[0-9]+)|(\.[0-9]+)'


literals = '()[].,@/|+-=<>*:$'

t_DOUBLECOLON = '::'
t_DOUBLEDOT = r'\.\.'
t_DOUBLESLASH = '//'

t_OP_NE = r'!='
t_OP_LE = r'<='
t_OP_GE = r'>='

_special_words = {
    'and': 'OP_AND',
    'or': 'OP_OR',
    'mod': 'OP_MOD',
    'div': 'OP_DIV',
    'comment': 'NODETYPE',
    'text': 'NODETYPE',
    'processing-instruction': 'NODETYPE',
    'node': 'NODETYPE',
    }


@lex.TOKEN(_ncname)
def t_NCNAME(t):
    t.type = _special_words.get(t.value, 'NCNAME')
    return t


def t_error(t):
    print " - Illegal character: %s" % (t,)
    # t.lexer.skip(1)


lexer = lex.lex(reflags=re.UNICODE)
