from unittest import TestCase
from StringIO import StringIO

from xpathlet.data_model import XPathNumber, XPathNodeSet
from xpathlet.engine import ExpressionEngine, build_xpath_tree


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

    test_xml = TEST_XML

    def setUp(self):
        self.xpath_root = build_xpath_tree(StringIO(self.test_xml))
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

    def assert_count(self, expr_or_nodeset, count=None, **node_types):
        if count is None:
            count = sum(node_types.values())
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
        self.assert_count('descendant::node()', text=4, element=2)
        self.assert_count('descendant::text()', text=4)

    def test_select_parent(self):
        self.assert_names('parent::mother', 'mother')
        self.assert_names('parent::*', 'mother')
        self.assert_count('parent::node()', 1)
        self.assert_count('parent::text()', 0)

    def test_select_ancestor(self):
        self.assert_names('ancestor::mother', 'mother')
        self.assert_names('ancestor::grandfather', 'grandfather')
        self.assert_names('ancestor::*', 'mother', 'grandfather', 'carrot')
        self.assert_count('ancestor::node()', root=1, element=3)
        self.assert_count('ancestor::text()', 0)

    def test_select_preceeding(self):
        self.assert_names('preceding::*',
                          'sister', 'mother', 'aunt', 'grandfather', 'carrot')
        self.assert_names('../preceding::*', 'aunt', 'grandfather', 'carrot')
        self.assert_names('/preceding::*')
        self.assert_count('preceding::node()', text=5, element=5)

    def test_select_following(self):
        self.assert_names('following::*',
                          'daughter', 'grandson', 'brother', 'uncle')
        self.assert_names('../following::*', 'sister', 'foo',
                          'daughter', 'grandson', 'brother', 'uncle')
        self.assertEqual(self.eval_xpath('/following::*').value,
                         self.eval_xpath('/descendant::*').value)
        self.assert_count('following::node()', text=9, element=4)

    def test_select_preceeding_siblings(self):
        self.assert_names('preceding-sibling::*', 'sister')
        self.assert_names('../preceding-sibling::*', 'aunt')
        self.assert_names('/preceding-sibling::*')
        self.assert_count('preceding-sibling::node()', text=2, element=1)

    def test_select_following_siblings(self):
        self.assert_names('following-sibling::*', 'brother')
        self.assert_names('../following-sibling::*', 'uncle')
        self.assert_names('/following-sibling::*')
        self.assert_count('following-sibling::node()', text=2, element=1)

    def test_select_descendant_or_self(self):
        self.assert_names('descendant-or-self::foo', 'foo')
        self.assert_names('descendant-or-self::daughter', 'daughter')
        self.assert_names('descendant-or-self::grandson', 'grandson')
        self.assert_names('descendant-or-self::*',
                          'foo', 'daughter', 'grandson')
        self.assert_count('descendant-or-self::node()', text=4, element=3)
        self.assert_count('descendant-or-self::text()', text=4)

    def test_select_ancestor_or_self(self):
        self.assert_names('ancestor-or-self::foo', 'foo')
        self.assert_names('ancestor-or-self::mother', 'mother')
        self.assert_names('ancestor-or-self::grandfather', 'grandfather')
        self.assert_names('ancestor-or-self::*',
                          'foo', 'mother', 'grandfather', 'carrot')
        self.assert_count('ancestor-or-self::node()', root=1, element=4)
        self.assert_count('ancestor-or-self::text()', 0)

    def test_select_attribute(self):
        self.assert_attrs('attribute::*', att1='bar', att2='baz')
        self.assert_attrs('attribute::node()', att1='bar', att2='baz')
        self.assert_attrs('attribute::att1', att1='bar')
        self.assert_attrs('attribute::att2', att2='baz')
        self.assert_attrs('.//attribute::*',
                          att1='bar', att2='baz', datt='quux')


class TestPredicates(XPathExpressionTestCase):
    def test_forward_postition(self):
        self.assert_names('/carrot/grandfather/*[1]', 'aunt')
        self.assert_names('/carrot/grandfather/*[2]', 'mother')
        self.assert_names('/carrot/grandfather/*[3]', 'uncle')

    def test_backward_postition(self):
        self.assert_names('preceding::*[1]', 'sister')
        self.assert_names('preceding::*[2]', 'mother')
        self.assert_names('preceding::*[3]', 'aunt')

    def test_position_variable(self):
        self.engine.variables.update({
                'one': XPathNumber(1.0),
                'two': XPathNumber(2.0),
                'three': XPathNumber(3.0),
                })
        self.assert_names('preceding::*[$one]', 'sister')
        self.assert_names('preceding::*[$two]', 'mother')
        self.assert_names('preceding::*[$three]', 'aunt')

    def test_position_function(self):
        self.assert_names('../*[last()]', 'brother')
        self.assert_names('../*[string-length("12")]', 'foo')


class TestExpressions(XPathExpressionTestCase):
    def test_equality_numbers(self):
        self.assertEqual(True, self.eval_xpath('1 = 1').value)
        self.assertEqual(False, self.eval_xpath('1 = 2').value)
        self.assertEqual(False, self.eval_xpath('1 != 1').value)
        self.assertEqual(True, self.eval_xpath('1 != 2').value)

    def test_comparison_numbers(self):
        self.assertEqual(True, self.eval_xpath('1 <= 1').value)
        self.assertEqual(False, self.eval_xpath('1 < 1').value)
        self.assertEqual(True, self.eval_xpath('1 <= 2').value)
        self.assertEqual(True, self.eval_xpath('1 < 2').value)

        self.assertEqual(True, self.eval_xpath('1 >= 1').value)
        self.assertEqual(False, self.eval_xpath('1 > 1').value)
        self.assertEqual(True, self.eval_xpath('2 >= 1').value)
        self.assertEqual(True, self.eval_xpath('2 > 1').value)
