import sys
import json
import os.path
from StringIO import StringIO
from xml.etree import ElementTree as ET

from xpathlet.engine import build_xpath_tree, ExpressionEngine
from xpathlet.data_model import (
    XPathRootNode, XPathTextNode, XPathElementNode, XPathAttributeNode,
    XPathNodeSet)


STORED_DATA_FILE_TEMPL = 'test_data%s.json'

SKIP_TESTS = (
    # Very slow
    'match_match12',
    'match_match13',
    'position_position09',

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
    'string_string133',  # Syntax error in PLY parser
    'string_string134',
    'string_string135',  # Syntax error in PLY parser
    # other
    'namespace_namespace25',  # redefined namespaces
    'output_output70',  # entity handling?

    # Unexplained Failures
    'predicate_predicate38',

    # Need XSLT features
    # key()
    'position_position05',
    'position_position42',
    'position_position43',
    'position_position44',
    'position_position45',
    'position_position46',
    'position_position47',
    'position_position49',
    'position_position50',
    'position_position51',
    'position_position56',
    'position_position57',
    # if
    'expression_expression03',
    'expression_expression06',
    'position_position11',
    'position_position41',
    'position_position68',
    'position_position78',
    'position_position106',
    'predicate_predicate37',
    'predicate_predicate57',
    # param
    'axes_axes109',
    'axes_axes113',
    'namespace_namespace05',
    'namespace_namespace14',
    'namespace_namespace15',
    'namespace_namespace16',
    'node_node07',
    # import/include
    'impincl_impincl16',
    'impincl_impincl17',
    'mdocs_mdocs12',
    'mdocs_mdocs13',
    # attribute
    'axes_axes131',
    'namespace_namespace30',
    'position_position80',
    'position_position83',
    'position_position97',  # ?
    'string_string140',
    # current()
    'axes_axes85',
    'axes_axes86',
    'select_select03',
    # sort
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


class HackyTemplateContext(object):
    def __init__(self, mode, node, pos, size):
        self.mode = mode
        self.node = node
        self.pos = pos
        self.size = size

    def copy(self, **kw):
        kw.setdefault('mode', self.mode)
        kw.setdefault('node', self.node)
        kw.setdefault('pos', self.pos)
        kw.setdefault('size', self.size)
        return type(self)(**kw)


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


class TraceCollector(object):
    def __init__(self):
        self.steps = []
        self.step_data = {}
        self.depth = 0

    def _escape(self, text):
        for s, r in [('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;')]:
            text = text.replace(s, r)
        return text

    def _expr_to_html(self, expr, expr_node):
        from xpathlet.ast import _to_html
        old_attrs = getattr(expr_node, '_html_attrs', {})
        expr_node._html_attrs = {'col': 'blue'}
        expr_html = _to_html(expr)
        expr_node._html_attrs = old_attrs
        return expr_html

    def _node_to_html(self, node, result, ctx_node):
        bits = []
        col = None
        if ctx_node is node:
            col = 'pink'
        elif ctx_node in node.get_ancestors():
            col = 'red'
        if isinstance(result, XPathNodeSet):
            for ns_node in result.value:
                if ns_node is node:
                    col = 'lightgreen'
                elif ns_node in node.get_ancestors():
                    if col != 'lightgreen':
                        col = 'green'
        if col:
            bits.append('<span style="color: %s">' % (col,))
        if isinstance(node, XPathRootNode):
            [child] = node._children
            bits.extend(self._node_to_html(child, result, ctx_node))
        elif isinstance(node, XPathElementNode):
            bits.append(self._escape("<%s" % (node.name,)))
            for attr in node._attributes:
                bits.extend(self._node_to_html(attr, result, ctx_node))
            bits.append(self._escape(">"))
            for child in node._children:
                bits.extend(self._node_to_html(child, result, ctx_node))
            bits.append(self._escape("</%s>" % (node.name,)))
        elif isinstance(node, XPathAttributeNode):
            bits.append(self._escape(" %s=%r" % (node.name, node.value)))
        elif isinstance(node, XPathTextNode):
            bits.append(self._escape(node.text))
        else:
            raise NotImplementedError()
        if col:
            bits.append('</span>')
        return bits

    def start_step(self, expr, expr_node, root_node, node, position, size):
        from uuid import uuid4
        step_id = str(uuid4())
        self.steps.append(step_id)
        self.step_data[step_id] = {
            'depth': self.depth,
            'expression_html': self._expr_to_html(expr, expr_node),
            'root_node': root_node,
            'ctx_node': node,
            'ctx_position': position,
            'ctx_size': size,
            }
        self.depth += 1
        return step_id

    def finish_step(self, step_id, result):
        step_data = self.step_data[step_id]
        step_data.update({
            'result_html': self._escape(repr(result)),
            'doc_html': ''.join(
                self._node_to_html(step_data['root_node'], result,
                                   step_data['ctx_node'])),
            })
        self.depth -= 1

    def dump_html(self):
        return
        import sys
        for step_id in self.steps:
            step = self.step_data[step_id]
            sys.stderr.write("<pre>expr: (")
            sys.stderr.write(str(step['depth']))
            sys.stderr.write(") ")
            sys.stderr.write(step['expression_html'])
            sys.stderr.write("\nrslt: ")
            sys.stderr.write(step['result_html'])
            sys.stderr.write("\n")
            sys.stderr.write(step['doc_html'])
            sys.stderr.write("</pre>\n")


class HackyMinimalXSLTEngine(object):
    def __init__(self, base_path, xsl):
        self.base_path = base_path
        self.xsl = xsl
        self._variables = {}

        self.xsl_tree = self._get_stripped(open(self._path(self.xsl)))
        self.xsl_engine = ExpressionEngine(self.xsl_tree)
        self.templates = [
            HackyMinimalXSLTTemplate(self, node)
            for node in self.xev('//xsl:template')]

        dt_engine = ExpressionEngine(
            self._get_stripped(StringIO(DEFAULT_TEMPLATE_DOC)))
        self.built_in_templates = [
            HackyMinimalXSLTTemplate(self, n, True)
            for n in dt_engine.evaluate('//xsl:template').value]

    def xev(self, expr, node=None, pos=1, size=1):
        ns_prefix = 'xsl'
        for prefix, val in self.xsl_tree._namespaces.items():
            if val == XSL_NAMESPACE:
                ns_prefix = prefix
        expr = expr.replace('xsl:', '%s:' % (ns_prefix))
        return self.xsl_engine.evaluate(
            expr, node, context_position=pos, context_size=size).value

    def _get_stripped(self, xsl_file):
        xtree = build_xpath_tree(xsl_file)
        self._strip_whitespace(xtree)
        return xtree

    def _path(self, path):
        return os.path.join(self.base_path, path)

    def _strip_whitespace(self, node, space='default', to_strip=None):
        for child in node.get_children():
            if child.node_type == 'text':
                if to_strip is not None and child.parent.name not in to_strip:
                    continue
                if space == 'default' and child.text.strip() == '':
                    node.remove_child(child)
            elif child.node_type == 'element':
                if child.expanded_name() == (XSL_NAMESPACE, 'text'):
                    continue
                cspace = space
                for attr in child.get_attributes():
                    if attr.name == 'space':
                        cspace = attr.value
                self._strip_whitespace(child, cspace, to_strip=to_strip)

    def dump_templates(self):
        print "\n===== %s =====" % self.xsl
        for template in self.templates:
            template.dump_orig()
        print "===== %s =====" % ('=' * len(self.xsl))

    def _add_default_namespace(self, results, uri):
        # Hackily put a default namespace in our results if we have one.
        if uri is None:
            return
        for node in results:
            if ET.iselement(node) and '{' not in node.tag:
                node.tag = '{%s}%s' % (uri, node.tag)
                self._add_default_namespace(node, uri)

    def process_file(self, path):
        self.data_tree = build_xpath_tree(open(self._path(path)))
        # TODO: Should we be replacing namespaces here?
        self.data_tree._namespaces = self.xsl_tree._namespaces
        self.data_engine = ExpressionEngine(self.data_tree)

        self.output_indent = False
        if self.xev('string(/xsl:stylesheet/xsl:output/@indent)') == 'yes':
            self.output_indent = True

        for node in self.xev('/xsl:stylesheet/xsl:variable'):
            ctx = HackyTemplateContext('', None, 1, 1)
            HackyMinimalXSLTTemplate(self, node).apply_node(node, ctx)

        for node in self.xev('/xsl:stylesheet/xsl:param'):
            ctx = HackyTemplateContext('', None, 1, 1)
            HackyMinimalXSLTTemplate(self, node).apply_node(node, ctx)

        for node in self.xev('/xsl:stylesheet/xsl:strip-space'):
            elems = self.xev('string(@elements)', node).split()
            self._strip_whitespace(self.data_tree, to_strip=elems)

        ctx = HackyTemplateContext('', self.data_tree, 1, 1)
        results = self.apply_templates(ctx)

        self._add_default_namespace(results, self.xsl_tree._namespaces.get(''))

        if self.output_indent:
            for node in results:
                if ET.iselement(node) and len(node) > 0:
                    _add_text_child(node, '\n')
        return results

    def find_template(self, ctx):
        matches = [t for t in self.templates if t.match(ctx)]
        if not matches:
            matches = [t for t in self.built_in_templates
                       if t.match(ctx.copy(mode=''))]

        max_priority = max(t.priority for t in matches)
        matches = [t for t in matches if t.priority == max_priority]

        # print ""
        # print ctx.pos, ctx.node
        # print matches
        # print ""

        if len(matches) > 1:
            sys.exit(1)

        assert len(matches) == 1
        return matches[0]

    def apply_templates(self, ctx):
        return self.find_template(ctx).apply(ctx)

    def set_variable(self, name, value):
        self._variables.setdefault(name, []).append(value)

    def unset_variable(self, name):
        self._variables[name][-1:] = []

    def get_variables(self):
        return dict((k, v[-1]) for k, v in self._variables.items() if v)


def _add_text_child(elem, text):
    children = list(elem)
    if not children:
        elem.text = "%s%s" % ((elem.text or ''), text)
    else:
        children[-1].tail = "%s%s" % ((children[-1].tail or ''), text)


class HackyMinimalXSLTTemplate(object):
    def __init__(self, engine, template_node, built_in=False):
        self._built_in = built_in
        self.engine = engine
        self.template_node = template_node
        self.pattern = self.attr_str('match', template_node)
        self.name = self.attr_str('name', template_node)
        self.mode = self.attr_str('mode', template_node)
        priority = self.attr_str('priority', template_node)
        if priority:
            self.priority = int(priority)
            return

        # :-(
        self.priority = 0.5
        if '/' not in self.pattern and '[' not in self.pattern:
            rpat = self.pattern.split('::')[-1]
            if rpat.endswith(':*'):
                self.priority = -0.25
            elif rpat.endswith('()'):
                self.priority = -0.5
            elif '(' not in rpat and '[' not in rpat:
                self.priority = 0

    def __repr__(self):
        return "<Template: match=%r priority=%s>" % (
            self.pattern, self.priority)

    def attr_str(self, attr_name, node):
        return self.engine.xev('string(@%s)' % (attr_name,), node)

    def find_raw(self, expr, ctx):
        tc = TraceCollector()
        result = self.engine.data_engine.evaluate(
            expr, ctx.node, self.engine.get_variables(),
            context_position=ctx.pos, context_size=ctx.size,
            trace_collector=tc)
        tc.dump_html()
        return result

    def find(self, expr, ctx):
        return self.find_raw(expr, ctx).value

    def match(self, ctx):
        if not self.pattern:
            return False

        if self.mode != ctx.mode:
            return False

        for node in self.find('ancestor-or-self::node()', ctx):
            pnodes = self.find(self.pattern, ctx.copy(node=node))
            if ctx.node in pnodes:
                return True

        return False

    def apply(self, ctx):
        return self._apply_children(self.template_node, ctx)

    def apply_node(self, templ_node, ctx):
        if templ_node.node_type == 'text':
            return [templ_node.text]

        assert templ_node.node_type == 'element'

        if templ_node.prefix != XSL_NAMESPACE:
            return self._apply_literal(templ_node, ctx)

        func = {
            'apply-templates': self._apply_templates,
            'call-template': self._apply_call_template,
            'for-each': self._apply_for_each,
            'value-of': self._apply_value_of,
            'variable': self._apply_variable,
            'copy-of': self._apply_copy_of,
            'element': self._apply_element,
            'choose': self._apply_choose,
            'param': self._apply_variable,
            'text': self._apply_text,
            }.get(templ_node.name, self._apply_bad)

        return func(templ_node, ctx)

    def _apply_bad(self, templ_node, ctx):
        raise NotImplementedError(templ_node.name)

    def _eval_avt(self, expr, ctx):
        import re
        expr_re = re.compile(r'((?:{{|[^{]+)*)({.*?})?')
        parts = []
        while expr:
            match = expr_re.match(expr)
            parts.append(match.group(1))
            if match.group(2):
                parts.append(
                    self.find('string(%s)' % match.group(2)[1:-1], ctx))
            expr = expr[match.end():]
        return ''.join(parts)

    def _apply_children(self, templ_node, ctx):
        results = []
        for child in templ_node.get_children():
            results.extend(self.apply_node(child, ctx))
        return results

    def _apply_literal(self, templ_node, ctx):
        elem = ET.Element(templ_node.name)
        for attr in templ_node.get_attributes():
            elem.set(attr.name, self._eval_avt(attr.value, ctx))

        return self._populate_element(elem, templ_node, ctx)

    def _populate_element(self, elem, templ_node, ctx):
        for result in self._apply_children(templ_node, ctx):
            if ET.iselement(result):
                if self.engine.output_indent:
                    _add_text_child(elem, '\n')
                elem.append(result)
                continue

            _add_text_child(elem, result)

        return [elem]

    def _apply_templates(self, templ_node, ctx):
        pattern = self.attr_str('select', templ_node)
        if not pattern:
            pattern = 'child::node()'

        mode = self.attr_str('mode', templ_node)
        if self._built_in:
            mode = ctx.mode

        nodes = self.find(pattern, ctx)
        results = []
        for pos, node in enumerate(nodes, 1):
            nctx = ctx.copy(mode=mode, node=node, pos=pos, size=len(nodes))
            results.extend(self.engine.apply_templates(nctx))
        return results

    def _apply_for_each(self, templ_node, ctx):
        pattern = self.attr_str('select', templ_node)
        assert pattern

        nodes = self.find(pattern, ctx)
        results = []
        for pos, node in enumerate(nodes, 1):
            nctx = ctx.copy(node=node, pos=pos, size=len(nodes))
            results.extend(self._apply_children(templ_node, nctx))

        return results

    def _apply_value_of(self, templ_node, ctx):
        pattern = self.attr_str('select', templ_node)
        assert pattern
        return [self.find("string(%s)" % pattern, ctx)]

    def _copy_et(self, node):
        if node.node_type != 'root':
            return [node.to_et()]

        result = []
        for child in node.get_children():
            if child.node_type == 'text':
                result.append(child.text)
            elif child.node_type == 'element':
                result.append(child.to_et())
            else:
                raise NotImplementedError()

        return result

    def _apply_copy_of(self, templ_node, ctx):
        pattern = self.attr_str('select', templ_node)
        assert pattern

        found = self.find_raw(pattern, ctx)
        if found.object_type != 'node-set':
            return [found.coerce('string').value]

        result = []
        for rnode in found.value:
            result.extend(self._copy_et(rnode))
        return result

    def _apply_text(self, templ_node, ctx):
        return [self.engine.xev('string(.)', templ_node)]

    def _apply_choose(self, templ_node, ctx):
        for child in templ_node.get_children():
            assert child.name in ('when', 'otherwise')

            if child.name == 'when':
                test = self.attr_str('test', child)
                if self.find("boolean(%s)" % test, ctx):
                    return self._apply_children(child, ctx)
                else:
                    continue

            if child.name == 'otherwise':
                return self._apply_children(child, ctx)

            raise NotImplementedError()

    def _apply_call_template(self, templ_node, ctx):
        # TODO: mode?
        name = self.attr_str('name', templ_node)
        assert name
        for template in self.engine.templates:
            if template.name == name:
                return template.apply(ctx)

    def _apply_variable(self, templ_node, ctx):
        name = self.attr_str('name', templ_node)
        select = self.attr_str('select', templ_node)
        if select:
            value = self.find_raw(select, ctx)
        else:
            value = XPathNodeSet([ResultTreeFragment(
                        self._apply_children(templ_node, ctx),
                        self.engine.data_tree._namespaces)])
        self.engine.set_variable(name, value)
        return []

    def _apply_element(self, templ_node, ctx):
        name = self._eval_avt(self.attr_str('name', templ_node), ctx)
        elem = ET.Element(name)
        return self._populate_element(elem, templ_node, ctx)

    def dump(self):
        ET.dump(self.template_node.to_et())

    def dump_orig(self):
        ET.dump(self.template_node._enode)


class ResultTreeFragment(XPathRootNode):
    def _build_tree(self):
        self._children = []
        text = ''
        for thing in self._document:
            if ET.iselement(thing):
                if text:
                    self._children.append(XPathTextNode(self, text))
                    text = (thing.tail or '')
                self._children.append(XPathElementNode(self, thing))
            else:
                text += thing
        if text:
            self._children.append(XPathTextNode(self, text))
        for i, node in enumerate(self._walk_in_doc_order()):
            node._doc_position = i
            if isinstance(node, XPathElementNode) and node.xml_id is not None:
                self._xml_ids.setdefault(node.xml_id, node)


if __name__ == '__main__':
    args = sys.argv[1:]

    if len(args) not in (1, 2, 3):
        print "usage:\n  %s <path-to-XSLT-conformance-tests>" % (sys.argv[0],)
        print ""
        print "Run XPath subset of XSLT conformance test suite over xpathlet."
        print "The test suite can be found online at:"
        print ("  https://www.oasis-open.org/committees/documents.php?"
               "wg_abbrev=xslt")
        print "Specifically, 'XSLT-testsuite-04.ZIP'"
        print ""
        exit(1)

    fail_fast = False
    if '-x' in args:
        fail_fast = True
        args.remove('-x')

    test_prefix = None
    if len(args) > 1:
        test_prefix = args[1]

    errors = []
    total = 0
    failed = 0
    passed = 0
    for tc in list(ConformanceTestCatalog(args[0]).find_tests()):
        if test_prefix:
            if '_' in test_prefix:
                if test_prefix != tc.name:
                    continue
            elif test_prefix != tc.name.split('_')[0]:
                continue
        total += 1
        try:
            if tc.process():
                passed += 1
            else:
                failed += 1
                if fail_fast:
                    break
        except Exception, e:
            errors.append((tc.name, e))
            raise

    print "\nTotal: %s Passed: %s Failed: %s" % (total, passed, failed)
    print "ERRORS: %s" % (errors,)
