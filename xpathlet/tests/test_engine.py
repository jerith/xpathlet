from unittest import TestCase
from StringIO import StringIO

from xpathlet.engine import ExpressionEngine, build_xpath_tree, XPathNodeSet


TEST_XML = '\n'.join([
        '<?xml version="1.0"?>',
        '<carrot>',
        '  <grandfather>',
        '    <aunt/>',
        '    <mother>',
        '      <sister/>',
        '      <foo att1="bar" att2="baz">',
        '        <daughter datt="quux">',
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


class XPathExpressionTestCase(TestCase):
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

    def get_nodeset(self, expr_or_nodeset):
        if isinstance(expr_or_nodeset, XPathNodeSet):
            return expr_or_nodeset
        return self.eval_xpath(expr_or_nodeset, self.get_foo())

    def assert_names(self, expr_or_nodeset, *names):
        nodeset = self.get_nodeset(expr_or_nodeset)
        self.assertEqual(set(names), set(node.name for node in nodeset.value))

    def assert_attrs(self, expr_or_nodeset, **attrs):
        nodeset = self.get_nodeset(expr_or_nodeset)
        self.assertEqual(attrs, dict((node.name, node.value)
                                     for node in nodeset.value))

    def assert_count(self, expr_or_nodeset, count, **node_types):
        nodeset = self.get_nodeset(expr_or_nodeset)
        self.assertEqual(count, len(nodeset.value))
        for node_type, type_count in node_types.items():
            self.assertEqual(type_count, sum(1 for n in nodeset.value
                                             if n.node_type == node_type))


class TestAxes(XPathExpressionTestCase):
    def test_select_self(self):
        node = self.get_foo()
        self.assertEqual(node, self.get_nodeset('self::node()').only())
        self.assertEqual(node, self.get_nodeset('self::*').only())
        self.assertEqual(node, self.get_nodeset('.').only())

    def test_select_child(self):
        self.assert_names('child::daughter', 'daughter')
        self.assert_names('child::*', 'daughter')
        self.assert_count('child::node()', 3)

    def test_select_descendant(self):
        self.assert_names('descendant::daughter', 'daughter')
        self.assert_names('descendant::grandson', 'grandson')
        self.assert_names('descendant::*', 'daughter', 'grandson')
        self.assert_count('descendant::node()', 6, text=4, element=2)
        self.assert_count('descendant::text()', 4, text=4)

    def test_select_parent(self):
        self.assert_names('parent::mother', 'mother')
        self.assert_names('parent::*', 'mother')
        self.assert_count('parent::node()', 1)
        self.assert_count('parent::text()', 0)

    def test_select_ancestor(self):
        self.assert_names('ancestor::mother', 'mother')
        self.assert_names('ancestor::grandfather', 'grandfather')
        self.assert_names('ancestor::*', 'mother', 'grandfather', 'carrot')
        self.assert_count('ancestor::node()', 4, root=1, element=3)
        self.assert_count('ancestor::text()', 0)

    def test_select_descendant_or_self(self):
        self.assert_names('descendant-or-self::foo', 'foo')
        self.assert_names('descendant-or-self::daughter', 'daughter')
        self.assert_names('descendant-or-self::grandson', 'grandson')
        self.assert_names('descendant-or-self::*',
                          'foo', 'daughter', 'grandson')
        self.assert_count('descendant-or-self::node()', 7, text=4, element=3)
        self.assert_count('descendant-or-self::text()', 4, text=4)

    def test_select_ancestor_or_self(self):
        self.assert_names('ancestor-or-self::foo', 'foo')
        self.assert_names('ancestor-or-self::mother', 'mother')
        self.assert_names('ancestor-or-self::grandfather', 'grandfather')
        self.assert_names('ancestor-or-self::*',
                          'foo', 'mother', 'grandfather', 'carrot')
        self.assert_count('ancestor-or-self::node()', 5, root=1, element=4)
        self.assert_count('ancestor-or-self::text()', 0)

    def test_select_attribute(self):
        self.assert_attrs('attribute::*', att1='bar', att2='baz')
        self.assert_attrs('attribute::node()', att1='bar', att2='baz')
        self.assert_attrs('attribute::att1', att1='bar')
        self.assert_attrs('attribute::att2', att2='baz')
        self.assert_attrs('.//attribute::*',
                          att1='bar', att2='baz', datt='quux')


class TestPredicates(XPathExpressionTestCase):
    pass


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
