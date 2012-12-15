from xpathlet.data_model import (
    XPathRootNode, XPathTextNode, XPathElementNode, XPathAttributeNode,
    XPathNodeSet)


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
        # return []
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
