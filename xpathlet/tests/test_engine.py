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
    def test_foo(self):
        print "\n-----"
        xpath_root = build_xpath_tree(StringIO(TEST_XML))
        engine = ExpressionEngine(xpath_root)
        result = engine.evaluate(u'/carrot/jr:foo/bar/text()')
        result = engine.evaluate(u'//bar/text()')
        print "\n-----"
        print "result:", result
        print "-----"
