import sys
import uuid
import os.path
from StringIO import StringIO
from xml.etree import ElementTree as ET

from xpathlet.engine import build_xpath_tree, ExpressionEngine
from xpathlet.data_model import (
    XPathRootNode, XPathTextNode, XPathElementNode, XPathNodeSet,
    FunctionLibrary, xpath_function, XPathString)
from xpathlet.trace_collector import TraceCollector


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


def xslt_xpath_engine(root_node, variables=None):
    return ExpressionEngine(root_node, variables=variables,
                            function_libraries=[XSLTFunctionLibrary()])


class HackyMinimalXSLTEngine(object):
    def __init__(self, base_path, xsl, trace=False):
        self.base_path = base_path
        self.xsl = xsl
        self.should_trace = trace
        self._variables = {}
        self._keys = {}
        self._xev_cache = {}

        self.xsl_tree = self._get_stripped(open(self._path(self.xsl)))
        self.xsl_engine = xslt_xpath_engine(self.xsl_tree)
        self.templates = [
            HackyMinimalXSLTTemplate(self, node)
            for node in self.xev('//xsl:template')]

        dt_engine = xslt_xpath_engine(
            self._get_stripped(StringIO(DEFAULT_TEMPLATE_DOC)))
        self.built_in_templates = [
            HackyMinimalXSLTTemplate(self, n, True)
            for n in dt_engine.evaluate('//xsl:template').value]

    def xev(self, expr, node=None, pos=1, size=1):
        ckey = (expr, node, pos, size)
        if ckey not in self._xev_cache:
            ns_prefix = 'xsl'
            for prefix, val in self.xsl_tree._namespaces.items():
                if val == XSL_NAMESPACE:
                    ns_prefix = prefix
            expr = expr.replace('xsl:', '%s:' % (ns_prefix))
            self._xev_cache[ckey] = self.xsl_engine.evaluate(
                expr, node, context_position=pos, context_size=size).value
        return self._xev_cache[ckey]

    def attr_str(self, attr_name, node):
        return self.xev('string(@%s)' % (attr_name,), node)

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
        self.data_engine = xslt_xpath_engine(self.data_tree)

        self.output_indent = False
        if self.xev('string(/xsl:stylesheet/xsl:output/@indent)') == 'yes':
            self.output_indent = True

        for node in self.xev('/xsl:stylesheet/xsl:key'):
            # TODO: Expand qname?
            name = self.attr_str('name', node)
            self._keys[name] = {
                'match': self.attr_str('match', node),
                'use': self.attr_str('use', node),
            }

        for node in self.xev('/xsl:stylesheet/xsl:variable'):
            ctx = HackyTemplateContext('', None, 1, 1)
            HackyMinimalXSLTTemplate(self, node).apply_node(node, ctx)

        for node in self.xev('/xsl:stylesheet/xsl:param'):
            ctx = HackyTemplateContext('', None, 1, 1)
            HackyMinimalXSLTTemplate(self, node)._apply_variable(node, ctx)

        for node in self.xev('/xsl:stylesheet/xsl:strip-space'):
            elems = self.attr_str('elements', node).split()
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
        return self.find_template(ctx).apply(ctx, {})

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
        self._find_cache = {}
        self.engine = engine
        self.template_node = template_node
        self.pattern = self.attr_str('match', template_node)
        self.name = self.attr_str('name', template_node)
        self.mode = self.attr_str('mode', template_node)
        self.priority = self._calc_priority()
        self.params = {}
        for child in template_node.get_children():
            if child.node_type != 'element' or child.name != 'param':
                # param elements are only allowed at the top of templates
                break
            self.params[self.attr_str('name', child)] = []

    def _calc_priority(self):
        priority = self.attr_str('priority', self.template_node)
        if priority:
            return float(priority)

        # :-(
        priority = 0.5
        if '/' not in self.pattern and '[' not in self.pattern:
            rpat = self.pattern.split('::')[-1]
            if rpat.endswith(':*'):
                priority = -0.25
            elif rpat.endswith('()'):
                priority = -0.5
            elif '(' not in rpat and '[' not in rpat:
                priority = 0

        return priority

    def __repr__(self):
        return "<Template: match=%r priority=%s>" % (
            self.pattern, self.priority)

    def attr_str(self, attr_name, node):
        return self.engine.attr_str(attr_name, node)

    def find_raw(self, expr, ctx):
        ckey = (expr, ctx.node, ctx.pos, ctx.size,
                tuple(sorted(self.engine.get_variables().items())))
        if ckey not in self._find_cache:
            tc = TraceCollector() if self.engine.should_trace else None
            metadata = {'current_node': ctx.node, 'engine': self.engine}
            result = self.engine.data_engine.evaluate(
                expr, ctx.node, self.engine.get_variables(),
                context_position=ctx.pos, context_size=ctx.size,
                metadata=metadata, trace_collector=tc)
            if tc is not None:
                tc.dump_html()
            self._find_cache[ckey] = result
        return self._find_cache[ckey]

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

    def apply(self, ctx, params):
        for name, vals in self.params.items():
            vals.append(params.get(name, None))
        result = self._apply_children(self.template_node, ctx)
        for name, vals in self.params.items():
            vals[-1:] = []
            self.engine.unset_variable(name)
        return result

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
            'param': self._apply_param,
            'text': self._apply_text,
            'if': self._apply_if,
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

    def _apply_if(self, templ_node, ctx):
        test = self.attr_str('test', templ_node)
        if self.find("boolean(%s)" % test, ctx):
            return self._apply_children(templ_node, ctx)
        return []

    def _apply_call_template(self, templ_node, ctx):
        # TODO: mode?
        name = self.attr_str('name', templ_node)
        assert name
        params = {}
        for child in templ_node.get_children():
            if child.node_type == 'text':
                continue
            assert child.name == 'with-param'
            param_name = self.attr_str('name', child)
            params[param_name] = self._get_binding_value(child, ctx)

        for template in self.engine.templates:
            if template.name == name:
                return template.apply(ctx, params)

    def _get_binding_value(self, templ_node, ctx):
        select = self.attr_str('select', templ_node)
        if select:
            return self.find_raw(select, ctx)
        if not templ_node.get_children():
            return XPathString('')

        return XPathNodeSet([ResultTreeFragment(
            self._apply_children(templ_node, ctx),
            self.engine.data_tree._namespaces)])

    def _apply_variable(self, templ_node, ctx):
        name = self.attr_str('name', templ_node)
        value = self._get_binding_value(templ_node, ctx)
        self.engine.set_variable(name, value)
        return []

    def _apply_param(self, templ_node, ctx):
        name = self.attr_str('name', templ_node)
        if self.params[name][-1] is None:
            self.params[name][-1] = self._get_binding_value(templ_node, ctx)
        self.engine.set_variable(name, self.params[name][-1])
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


class HackyMinimalXSLTKey(object):
    def __init__(self, engine, name):
        self._find_cache = {}
        self.engine = engine
        self.name = name
        self.pattern = engine._keys[name]['match']
        self.value_expr = engine._keys[name]['use']

    def __repr__(self):
        return "<Key: match=%r use=%r>" % (self.pattern, self.value_expr)

    def find_raw(self, expr, ctx):
        ckey = (expr, ctx.node, ctx.pos, ctx.size,
                tuple(sorted(self.engine.get_variables().items())))
        if ckey not in self._find_cache:
            tc = TraceCollector() if self.engine.should_trace else None
            metadata = {'current_node': ctx.node}
            result = self.engine.data_engine.evaluate(
                expr, ctx.node, self.engine.get_variables(),
                context_position=ctx.pos, context_size=ctx.size,
                metadata=metadata, trace_collector=tc)
            if tc is not None:
                tc.dump_html()
            self._find_cache[ckey] = result
        return self._find_cache[ckey]

    def find(self, expr, ctx):
        return self.find_raw(expr, ctx).value

    def match(self, ctx):
        if not self.pattern:
            return False

        for node in self.find('ancestor-or-self::node()', ctx):
            pnodes = self.find(self.pattern, ctx.copy(node=node))
            if ctx.node in pnodes:
                return True

        return False

    def apply(self, root_node, values):
        matching_nodes = set()
        all_nodes = self.find(
            '//*', HackyTemplateContext('', root_node, 1, 1))
        for node in all_nodes:
            ctx = HackyTemplateContext('', node, 1, 1)
            if self.match(ctx) and self.match_values(ctx, values):
                matching_nodes.add(node)

        return matching_nodes

    def match_values(self, ctx, values):
        node_values = self.find_raw(self.value_expr, ctx)
        if node_values.object_type == 'node-set':
            node_values = [node.string_value() for node in node_values.value]
        else:
            node_values = [node_values.coerce('string').value]
        return set(values).intersection(node_values)


class XSLTFunctionLibrary(FunctionLibrary):
    generated_ids = {}  # TODO: Something better than this?

    @xpath_function('object', 'node-set?', rtype='node-set')
    def document(ctx, obj, node_set=None):
        raise NotImplementedError()

    @xpath_function('string', 'object', rtype='node-set')
    def key(ctx, name, obj):
        # TODO: Expand qname?
        key_processor = HackyMinimalXSLTKey(ctx.metadata['engine'], name.value)

        if obj.object_type == 'node-set':
            values = set(node.string_value() for node in obj.value)
        else:
            values = set([obj.coerce('string').value])

        return XPathNodeSet(key_processor.apply(ctx.root_node, values))

    @xpath_function('number', 'string', 'string?', rtype='string')
    def format_number(ctx, num, formatstr, decimalstr):
        raise NotImplementedError()

    @xpath_function(rtype='node-set')
    def current(ctx):
        return XPathNodeSet([ctx.metadata['current_node']])

    @xpath_function('string', rtype='string')
    def unparsed_entity_uri(ctx, name):
        raise NotImplementedError()

    @xpath_function('node-set?', rtype='string')
    def generate_id(ctx, node_set=None):
        if node_set is None:
            node_set = XPathNodeSet([ctx.node])
        if not node_set.value:
            return XPathString('')
        node = node_set.value[0]
        if node not in XSLTFunctionLibrary.generated_ids:
            XSLTFunctionLibrary.generated_ids[node] = uuid.uuid4().hex
        return XPathString('id%s' % (XSLTFunctionLibrary.generated_ids[node],))

    @xpath_function('string', rtype='object')
    def system_property(ctx):
        raise NotImplementedError()
