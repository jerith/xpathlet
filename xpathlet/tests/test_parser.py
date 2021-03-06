from unittest import TestCase

from xpathlet.parser import parser


class TestParser(TestCase):
    def test_foo(self):
        print "\n-----"
        print parser.parse(u'/foo')
        print "-----"
        r = parser.parse("instance('cities')/root/item[state=/new_cascading_select/state and county=/new_cascading_select/county]", debug=0)
        print r
        print r.to_str()
        print "-----"
        r = parser.parse("//foo//bar")
        print r
        print r.to_str()
        print "-----"
