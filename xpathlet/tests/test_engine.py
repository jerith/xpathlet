from unittest import TestCase
from xml.etree.ElementTree import parse, tostring, iterparse

from xpathlet.engine import ExpressionEngine, build_xpath_tree


class TestEngine(TestCase):
    def test_foo(self):
        print "\n-----"
        xpath_root = build_xpath_tree(
            open('/Users/jerith/code/vodka/new_cascading_select.xml'))
        elem = xpath_root.get_children()[0]
        print elem.get_children()
        print elem.get_children()[1].get_children()[0].get_attributes()
        print "-----"
