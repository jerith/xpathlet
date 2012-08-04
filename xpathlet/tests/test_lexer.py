from unittest import TestCase

from xpathlet.lexer import lexer


class TestLexer(TestCase):
    def test_foo(self):
        print "\n-----"

        lexer.input(u'foo 4 div text bar != \u200C-')
        for tok in lexer:
            print tok

        print "\n-----"
