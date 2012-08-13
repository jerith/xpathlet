from unittest import TestCase

from xpathlet.lexer import lexer


class TestLexer(TestCase):
    def test_foo(self):
        print "\n-----"

        lexer.input(u'foo 4 div text bar != \u200C-')
        for tok in lexer:
            print tok

        lexer.input(u"j[@l='12'] != j[@w='45']")
        for tok in lexer:
            print tok

        print "\n-----"
