import json
import os.path
from xml.etree import ElementTree as ET
from optparse import OptionParser

from xpathlet.engine import build_xpath_tree, ExpressionEngine

from minimal_xslt import HackyMinimalXSLTEngine


STORED_DATA_FILE_TEMPL = 'test_data%s.json'

SLOW_TESTS = (
    'match_match12',
    'match_match13',
    'position_position09',
    )

SKIP_TESTS = (
    # Need XPath features
    # namespace axis
    'axes_axes62',
    'axes_axes68',
    'axes_axes120',
    'axes_axes129',
    'namespace_namespace28',
    'namespace_namespace32',
    'namespace_namespace33',
    'namespace_namespace34',
    'namespace_namespace142',
    'node_node17',
    'position_position76',
    'position_position111',
    # float formatting
    'math_math111',
    'string_string133',
    'string_string134',
    'string_string135',
    # other
    'namespace_namespace25',  # redefined namespaces
    'output_output70',  # entity handling?

    # Need XSLT features
    # import/include
    'impincl_impincl16',
    'impincl_impincl17',
    'mdocs_mdocs12',
    'mdocs_mdocs13',
    # sort
    'axes_axes113',
    'position_position10',
    'position_position69',
    'position_position93',
    'select_select69',
    # copy
    'copy_copy16',
    'position_position86',
    # document
    'mdocs_mdocs07',
    'mdocs_mdocs09',
    'mdocs_mdocs10',
    'mdocs_mdocs17',
    'select_select67',
    'select_select68',
    'select_select71',
    # others
    'axes_axes59',  # number
    'boolean_boolean43',  # better result trees?
    'string_string13',  # format-number()
    'namespace_namespace48',  # error signalling?
    'namespace_namespace110',  # invalid namespace URI?

    # Unsupported by ElementTree
    # comment/PI nodes
    'axes_axes104',
    'axes_axes105',
    'axes_axes106',
    'axes_axes107',
    'axes_axes108',
    'axes_axes110',
    'axes_axes111',
    'axes_axes112',
    'axes_axes126',
    'axes_axes128',
    'namespace_namespace29',
    'namespace_namespace30',
    'node_node02',
    'node_node03',
    'node_node09',
    'node_node10',
    'node_node11',
    'node_node12',
    'node_node13',
    'node_node14',
    'node_node15',
    'node_node18',
    'position_position71',
    'position_position75',
    'position_position101',
    'select_select75',
    # others
    'idkey_idkey09',  # DTD stuff
    )


class ConformanceTestCatalog(object):
    def __init__(self, base_path, catalog=1, trace=False):
        self.base_path = base_path
        self.catalog = catalog
        self.trace = trace

    def find(self, expr, node=None):
        if node is None:
            node = self.cat_node
        return self.engine.evaluate(expr, node).value

    def _stored_data_file(self):
        return STORED_DATA_FILE_TEMPL % (self.catalog,)

    def find_tests(self, skip_slow=False):
        try:
            tests = json.load(open(self._stored_data_file()))
        except IOError:
            tests = list(self.find_tests_full())
            json.dump(tests, open(self._stored_data_file(), 'w'))

        for test in tests:
            test = dict((str(k), v) for k, v in test.items())
            if skip_slow and test['name'] in SLOW_TESTS:
                continue
            if test['name'] not in SKIP_TESTS:
                yield ConformanceTestCase(self.base_path, self.trace, **test)

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
    def __init__(self, base_path, trace,
                 catpath, name, filepath, datas, xsls, outputs):
        self.catalog_path = os.path.join(base_path, catpath)
        self.name = name
        self.filepath = filepath
        self.datas = datas
        self.xsls = xsls
        self.outputs = outputs
        self.trace = trace

    def get_input(self, name):
        return os.path.join(self.catalog_path, self.filepath, name)

    def get_output(self, name):
        return os.path.join(self.catalog_path, 'REF_OUT', self.filepath, name)

    def process(self):
        assert len(self.outputs) == 1
        xsls = [name for _role, name in sorted(self.xsls)]
        datas = [name for _role, name in sorted(self.datas)]

        engine = HackyMinimalXSLTEngine(
            os.path.join(self.catalog_path, self.filepath), xsls[0],
            self.trace)

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
            return True
        else:
            print "[FAIL]", self.name
            print "  expected:"
            for line in expected.split('\n'):
                print '   ', line
            print "  actual:"
            for line in actual.split('\n'):
                print '   ', line
            return False


if __name__ == '__main__':
    usage = '\n'.join([
        "usage: %prog [options] [<test name> [...]]",
        "",
        "Run XPath subset of XSLT conformance test suite over xpathlet."
        "The test suite can be found online at:"
        "  https://www.oasis-open.org/committees/documents.php?wg_abbrev=xslt",
        "Specifically, 'XSLT-testsuite-04.ZIP'",
        "",
        "Individual tests may be specified by full name ('string_string01')",
        "and sets of tests may be specified by prefix ('string')."])
    parser = OptionParser(usage=usage)
    parser.add_option('-s', '--suite-path', metavar='PATH', action='store',
                      dest='suite_path', default='TESTS',
                      help='path to conformance test suite [%default]')
    parser.add_option('-x', '--fail-fast', action='store_true',
                      dest='fail_fast', default=False,
                      help='stop on first failure')
    parser.add_option('--trace', action='store_true', dest='trace',
                      default=False, help='trace XPath execution flow')
    parser.add_option('--skip-slow', action='store_true', dest='skip_slow',
                      default=False, help='skip some slow tests')

    (opts, test_names) = parser.parse_args()

    test_catalog = ConformanceTestCatalog(opts.suite_path, trace=opts.trace)
    tests_to_run = []

    for tc in test_catalog.find_tests(skip_slow=opts.skip_slow):
        if not test_names:
            # Special case. If no tests are specified, run them all.
            tests_to_run.append(tc)
            continue

        for test_name in test_names:
            if test_name == tc.name or test_name == tc.name.split('_')[0]:
                tests_to_run.append(tc)
                break

    errors = []
    total = 0
    failed = 0
    passed = 0
    for tc in tests_to_run:
        total += 1
        try:
            if tc.process():
                passed += 1
            else:
                failed += 1
                if opts.fail_fast:
                    break
        except Exception, e:
            errors.append((tc.name, e))
            raise

    print "\nTotal: %s Passed: %s Failed: %s" % (total, passed, failed)
    print "ERRORS: %s" % (errors,)
