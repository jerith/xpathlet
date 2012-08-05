from unittest import TestCase
from StringIO import StringIO

from xpathlet.engine import ExpressionEngine, build_xpath_tree


TEST_XML = '\n'.join([
        '<?xml version="1.0"?>',
        '<carrot>',
        '  <grandfather>',
        '    <aunt/>',
        '    <mother>',
        '      <sister/>',
        '      <foo>',
        '        <daughter>',
        '          <grandson/>',
        '        </daughter>',
        '      </foo>',
        '      <brother/>',
        '    </mother>',
        '    <uncle/>',
        '  </grandfather>',
        '</carrot>',
        ])


TEST_XML2 = '\n'.join([
        '<?xml version="1.0"?>',
        '<carrot xmlns:jr="http://openrosa.org/javarosa">',
        '  <jr:foo>',
        '    <bar>one<baz><bar>fraction</bar></baz></bar>',
        '    <bar>two</bar>',
        '    <bar>three</bar>',
        '  </jr:foo>',
        '</carrot>',
        ])


class TestAxes(TestCase):
    DEBUG = False

    def setUp(self):
        self.xpath_root = build_xpath_tree(StringIO(TEST_XML))
        self.engine = ExpressionEngine(self.xpath_root)

    def eval_xpath(self, xpath_expr, node=None):
        if self.DEBUG:
            print "\n-----"
            print "XPath:", xpath_expr
            self.engine.debug = True

        result = self.engine.evaluate(xpath_expr, node)

        if self.DEBUG:
            print "\n-----"
            print "Result:", result
            print "-----"

        return result

    def get_foo(self):
        node = self.engine.evaluate('//foo').only()
        self.assertEqual('element', node.node_type)
        self.assertEqual('foo', node.name)
        return node

    def test_select_self(self):
        node = self.get_foo()
        self.assertEqual(node, self.eval_xpath('self::node()', node).only())
        self.assertEqual(node, self.eval_xpath('self::*', node).only())
        self.assertEqual(node, self.eval_xpath('.', node).only())

    def test_select_child(self):
        node = self.get_foo()
        self.assertEqual('daughter',
                         self.eval_xpath('child::daughter', node).only().name)
        self.assertEqual('daughter',
                         self.eval_xpath('child::*', node).only().name)
        self.assertEqual(3, len(self.eval_xpath('child::node()', node).value))


class TestEngine(TestCase):
    def eval_xpath(self, xpath_expr, debug=False):
        print "\n-----"
        print "XPath:", xpath_expr

        xpath_root = build_xpath_tree(StringIO(TEST_XML2))
        engine = ExpressionEngine(xpath_root, debug=debug)
        result = engine.evaluate(xpath_expr)

        if debug:
            print "\n-----"
        print "Result:", result
        print "-----"

    def test_foo(self):
        self.eval_xpath(u'/carrot/jr:foo/bar/text()')
        self.eval_xpath(u'//bar/text()')
