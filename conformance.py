import sys
import json
import os.path
from StringIO import StringIO
from xml.etree import ElementTree as ET

from xpathlet.engine import build_xpath_tree, ExpressionEngine


STORED_DATA_FILE_TEMPL = 'test_data%s.json'

SKIP_TESTS = (
    # Very slow
    'match_match12',
    'match_match13',

    # Need XPath features
    'axes_axes62',  # namespace axis
    'math_math111',  # correct float formatting
    'namespace_namespace25',  # redefined namespaces
    'namespace_namespace28',  # namespace axis
    'namespace_namespace33',  # namespace axis
    'namespace_namespace142',  # namespace axis

    # Unexplained Failures
    'attribset_attribset20',
    'axes_axes129',
    'axes_axes130',
    'dflt_dflt02',
    'dflt_dflt04',
    'idkey_idkey09',
    'idkey_idkey22',
    'idkey_idkey55',
    'idkey_idkey56',
    'match_match01',
    'mdocs_mdocs07',
    'mdocs_mdocs09',
    'mdocs_mdocs10',
    'mdocs_mdocs12',
    'mdocs_mdocs13',
    'mdocs_mdocs17',
    'namespace_namespace05',
    'namespace_namespace21',
    'namespace_namespace22',
    'namespace_namespace25',
    'namespace_namespace29',
    'namespace_namespace30',
    'namespace_namespace31',
    'namespace_namespace32',
    'namespace_namespace34',
    'node_node15',
    'node_node18',
    'node_node20',
    'node_node21',

    # Need XSLT features
    'axes_axes14',  # variables
    'axes_axes15',  # variables
    'boolean_boolean42',  # variables
    'boolean_boolean43',  # variables
    'boolean_boolean58',  # variables
    'boolean_boolean59',  # variables
    'boolean_boolean84',  # variables
    'boolean_boolean85',  # variables
    'boolean_boolean86',  # variables
    'idkey_idkey58',  # variables
    'math_math08',  # variables
    'math_math17',  # variables
    'math_math18',  # variables
    'math_math84',  # variables
    'math_math97',  # variables
    'math_math98',  # variables
    'math_math99',  # variables
    'math_math100',  # variables
    'math_math101',  # variables
    'namespace_namespace14',  # variables
    'namespace_namespace15',  # variables
    'namespace_namespace16',  # variables
    'axes_axes68',  # element
    'axes_axes120',  # element
    'namespace_namespace48',  # element
    'namespace_namespace110',  # element
    'node_node17',  # element
    'axes_axes109',  # param
    'axes_axes113',  # param
    'node_node07',  # param
    'impincl_impincl16',  # include
    'impincl_impincl17',  # include
    'axes_axes85',  # current()
    'axes_axes86',  # current()
    'copy_copy24',  # copy-of
    'math_math103',  # copy-of
    'copy_copy16',  # copy
    'axes_axes59',  # number
    'axes_axes131',  # attribute
    'expression_expression03',  # if
    'expression_expression06',  # if

    # Unsupported by ElementTree
    'axes_axes104',  # comment/PI nodes
    'axes_axes105',  # comment/PI nodes
    'axes_axes106',  # comment/PI nodes
    'axes_axes107',  # comment/PI nodes
    'axes_axes108',  # comment/PI nodes
    'axes_axes110',  # comment/PI nodes
    'axes_axes111',  # comment/PI nodes
    'axes_axes112',  # comment/PI nodes
    'axes_axes126',  # comment/PI nodes
    'axes_axes128',  # comment/PI nodes
    'node_node02',  # comment/PI nodes
    'node_node03',  # comment/PI nodes
    'node_node09',  # comment/PI nodes
    'node_node10',  # comment/PI nodes
    'node_node11',  # comment/PI nodes
    'node_node12',  # comment/PI nodes
    'node_node13',  # comment/PI nodes
    'node_node14',  # comment/PI nodes
    )


class ConformanceTestCatalog(object):
    def __init__(self, base_path, catalog=1):
        self.base_path = base_path
        self.catalog = catalog

    def find(self, expr, node=None):
        if node is None:
            node = self.cat_node
        return self.engine.evaluate(expr, node).value

    def _stored_data_file(self):
        return STORED_DATA_FILE_TEMPL % (self.catalog,)

    def find_tests(self):
        try:
            tests = json.load(open(self._stored_data_file()))
        except IOError:
            tests = list(self.find_tests_full())
            json.dump(tests, open(self._stored_data_file(), 'w'))

        for test in tests:
            test = dict((str(k), v) for k, v in test.items())
            if test['name'] not in SKIP_TESTS:
                yield ConformanceTestCase(self.base_path, **test)

    def find_tests_full(self):
        tree = build_xpath_tree(
            open(os.path.join(self.base_path, 'catalog.xml')))
        self.engine = ExpressionEngine(tree)
        self.cat_node = self.engine.evaluate(
            '//test-catalog[%s]' % self.catalog).only()
        catpath = self.find('string(major-path)')

        test_nodes = self.find('test-case[spec-citation/@spec="xpath"]')
        for node in test_nodes:
            nfind = lambda e: self.find(e, node)
            name = nfind('string(@id)')
            filepath = nfind('string(file-path)')
            inputs = [
                (self.find('string(@role)', n), self.find('string(.)', n))
                for n in nfind('scenario/input-file')]
            datas = [i for i in inputs if i[0].endswith('data')]
            xsls = [i for i in inputs if i[0].endswith('stylesheet')]
            outputs = [n.string_value() for n in nfind('scenario/output-file')]
            yield dict(catpath=catpath, name=name, filepath=filepath,
                       datas=datas, xsls=xsls, outputs=outputs)


class ConformanceTestCase(object):
    def __init__(self, base_path, catpath, name,
                 filepath, datas, xsls, outputs):
        self.catalog_path = os.path.join(base_path, catpath)
        self.name = name
        self.filepath = filepath
        self.datas = datas
        self.xsls = xsls
        self.outputs = outputs

    def get_input(self, name):
        return os.path.join(self.catalog_path, self.filepath, name)

    def get_output(self, name):
        return os.path.join(self.catalog_path, 'REF_OUT', self.filepath, name)

    def ev(self, expr, node=None):
        return self.data_engine.evaluate(expr, node).value

    def process(self):
        assert len(self.outputs) == 1
        xsls = [name for _role, name in sorted(self.xsls)]
        datas = [name for _role, name in sorted(self.datas)]

        engine = HackyMinimalXSLTEngine(
            os.path.join(self.catalog_path, self.filepath), xsls[0])

        try:
            out_parts = engine.process_file(datas[0])
            out = ET.tostring(ET.fromstring(''.join(
                        ET.tostring(a) if ET.iselement(a) else a
                        for a in out_parts)))
        except:
            engine.dump_templates()
            raise

        ref_out = ET.parse(self.get_output(self.outputs[0])).getroot()
        expected = ET.tostring(ref_out)
        actual = ET.tostring(ET.fromstring(out))

        if expected == actual:
            print "[OK]", self.name
        else:
            print "[FAIL]", self.name
            print "  expected:"
            for line in expected.split('\n'):
                print '   ', line
            print "  actual:"
            for line in actual.split('\n'):
                print '   ', line


XSL_NAMESPACE = 'http://www.w3.org/1999/XSL/Transform'
DEFAULT_TEMPLATE_DOC = '\n'.join([
        '<?xml version="1.0"?>',
        '<xsl:stylesheet xmlns:xsl="%s" version="1.0">' % XSL_NAMESPACE,

        '<xsl:template match="*|/">',
        '  <xsl:apply-templates/>',
        '</xsl:template>',

        '<xsl:template match="text()|@*">',
        '  <xsl:value-of select="."/>',
        '</xsl:template>',

        '</xsl:stylesheet>',
        ])


class HackyMinimalXSLTEngine(object):
    def __init__(self, base_path, xsl):
        self.base_path = base_path
        self.xsl = xsl

        self.xsl_tree = self._get_stripped(open(self._path(self.xsl)))
        self.xsl_engine = ExpressionEngine(self.xsl_tree)
        self.templates = [
            HackyMinimalXSLTTemplate(self, node)
            for node in self.xev('//xsl:template')]

        dt_engine = ExpressionEngine(
            self._get_stripped(StringIO(DEFAULT_TEMPLATE_DOC)))
        self.built_in_templates = [
            HackyMinimalXSLTTemplate(self, n)
            for n in dt_engine.evaluate('//xsl:template').value]

    def xev(self, expr, node=None):
        return self.xsl_engine.evaluate(expr, node).value

    def _get_stripped(self, xsl_file):
        xtree = build_xpath_tree(xsl_file)
        self._strip_whitespace(xtree)
        return xtree

    def _path(self, path):
        return os.path.join(self.base_path, path)

    def _strip_whitespace(self, node, space='default'):
        for child in node.get_children():
            if child.node_type == 'text':
                if space == 'default' and child.text.strip() == '':
                    node.remove_child(child)
            elif child.node_type == 'element':
                # TODO: Unstrip xsl:text elements?
                if child.expanded_name() == (XSL_NAMESPACE, 'text'):
                    continue
                cspace = space
                for attr in child.get_attributes():
                    if attr.name == 'space':
                        cspace = attr.value
                self._strip_whitespace(child, cspace)

    def dump_templates(self):
        print "\n===== %s =====" % self.xsl
        for template in self.templates:
            template.dump_orig()
        print "===== %s =====" % ('=' * len(self.xsl))

    def process_file(self, path):
        self.data_tree = build_xpath_tree(open(self._path(path)))
        # TODO: Should we be replacing namespaces here?
        self.data_tree._namespaces = self.xsl_tree._namespaces
        self.data_engine = ExpressionEngine(self.data_tree)

        return self.apply_templates(self.data_tree)

    def find_template(self, node):
        matches = [t for t in self.templates if t.match(node)]
        if not matches:
            matches = [t for t in self.built_in_templates if t.match(node)]

        max_priority = max(t.priority for t in matches)
        matches = [t for t in matches if t.priority == max_priority]

        assert len(matches) == 1
        return matches[0]

    def apply_templates(self, node):
        template = self.find_template(node)

        return template.apply(node)


class HackyMinimalXSLTTemplate(object):
    def __init__(self, engine, template_node):
        self.engine = engine
        self.template_node = template_node
        self.pattern = self.engine.xev('string(@match)', template_node)
        self.name = self.engine.xev('string(@name)', template_node)

        # :-(
        self.priority = 0
        if '/' in self.pattern:
            self.priority = 0.5

    def find(self, expr, cnode):
        return self.engine.data_engine.evaluate(expr, cnode).value

    def match(self, node):
        if not self.pattern:
            return False

        for cnode in self.find('ancestor-or-self::node()', node):
            pnodes = self.find(self.pattern, cnode)
            if node in pnodes:
                return True

        return False

    def apply(self, node):
        return self._apply_children(self.template_node, node)

    def apply_node(self, templ_node, node):

        if templ_node.node_type == 'text':
            return [templ_node.text]

        assert templ_node.node_type == 'element'

        if templ_node.prefix != XSL_NAMESPACE:
            return self._apply_literal(templ_node, node)

        return {
            'apply-templates': self._apply_templates,
            'call-template': self._apply_call_template,
            'for-each': self._apply_for_each,
            'value-of': self._apply_value_of,
            'choose': self._apply_choose,
            'text': self._apply_text,
            }.get(templ_node.name, self._apply_bad)(templ_node, node)

    def _apply_bad(self, templ_node, node):
        raise NotImplementedError(templ_node.name)

    def _apply_children(self, templ_node, node):
        results = []
        for child in templ_node.get_children():
            results.extend(self.apply_node(child, node))
        return results

    def _apply_literal(self, templ_node, node):
        elem = ET.Element(templ_node.name)
        for attr in templ_node.get_attributes():
            # TODO: better attrs?
            elem.set(attr.name, attr.value)

        for result in self._apply_children(templ_node, node):
            if ET.iselement(result):
                elem.append(result)
                continue

            children = list(elem)
            if not children:
                elem.text = "%s%s" % ((elem.text or ''), result)
            else:
                children[-1].tail = "%s%s" % ((children[-1].text or ''),
                                               result)

        return [elem]

    def _apply_templates(self, templ_node, node):
        pattern = self.engine.xev('string(@select)', templ_node)
        if not pattern:
            pattern = 'child::node()'

        nodes = self.find(pattern, node)
        results = []
        for n in nodes:
            results.extend(self.engine.apply_templates(n))
        return results

    def _apply_for_each(self, templ_node, node):
        pattern = self.engine.xev('string(@select)', templ_node)
        assert pattern

        nodes = self.find(pattern, node)
        results = []
        for n in nodes:
            results.extend(self._apply_children(templ_node, n))

        return results

    def _apply_value_of(self, templ_node, node):
        pattern = self.engine.xev('string(@select)', templ_node)
        assert pattern
        return [self.find("string(%s)" % pattern, node)]

    def _apply_text(self, templ_node, node):
        return [self.engine.xev('string(.)', templ_node)]

    def _apply_choose(self, templ_node, node):
        for child in templ_node.get_children():
            assert child.name in ('when', 'otherwise')

            if child.name == 'when':
                test = self.engine.xev('string(@test)', child)
                if self.find("boolean(%s)" % test, node):
                    return self._apply_children(child, node)
                else:
                    continue

            if child.name == 'otherwise':
                return self._apply_children(child, node)

            raise NotImplementedError()

    def _apply_call_template(self, templ_node, node):
        name = self.engine.xev('string(@name)', templ_node)
        assert name
        for template in self.engine.templates:
            if template.name == name:
                return template.apply(node)

    def dump(self):
        ET.dump(self.template_node.to_et())

    def dump_orig(self):
        ET.dump(self.template_node._enode)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "usage:\n  %s <path-to-XSLT-conformance-tests>" % (sys.argv[0],)
        print ""
        print "Run XPath subset of XSLT conformance test suite over xpathlet."
        print "The test suite can be found online at:"
        print ("  https://www.oasis-open.org/committees/documents.php?"
               "wg_abbrev=xslt")
        print "Specifically, 'XSLT-testsuite-04.ZIP'"
        print ""
        exit(1)

    errors = []
    for tc in list(ConformanceTestCatalog(sys.argv[1]).find_tests()):
        try:
            tc.process()
        except Exception, e:
            errors.append((tc.name, e))
            raise

    print "\nERRORS: %s" % (errors,)
