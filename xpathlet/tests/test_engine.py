from unittest import TestCase
from StringIO import StringIO

from xpathlet.engine import ExpressionEngine, build_xpath_tree


TEST_XML = '\n'.join([
        '<?xml version="1.0"?>',
        '<carrot xmlns:jr="http://openrosa.org/javarosa">',
        '  <jr:foo>',
        '    <bar>one<baz><bar>fraction</bar></baz></bar>',
        '    <bar>two</bar>',
        '    <bar>three</bar>',
        '  </jr:foo>',
        '</carrot>',
        ])


class TestEngine(TestCase):
    def eval_xpath(self, xpath_expr, debug=False):
        print "\n-----"
        print "XPath:", xpath_expr

        xpath_root = build_xpath_tree(StringIO(TEST_XML))
        engine = ExpressionEngine(xpath_root, debug=debug)
        result = engine.evaluate(xpath_expr)

        if debug:
            print "\n-----"
        print "Result:", result
        print "-----"

    def test_foo(self):
        self.eval_xpath(u'/carrot/jr:foo/bar/text()')
        self.eval_xpath(u'//bar/text()')
