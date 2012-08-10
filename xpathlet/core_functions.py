from math import floor, ceil

from xpathlet.data_model import (
    XPathNodeSet, XPathBoolean, XPathNumber, XPathString,
    FunctionLibrary, xpath_function)


class CoreFunctionLibrary(FunctionLibrary):

    # Node Set Functions

    @xpath_function(rtype='number')
    def last(ctx):
        return XPathNumber(ctx.size)

    @xpath_function(rtype='number')
    def position(ctx):
        return XPathBoolean(ctx.position)

    @xpath_function('node-set', rtype='number')
    def count(ctx, node_set):
        return XPathNumber(len(node_set.value))

    @xpath_function('object', rtype='node-set')
    def id(ctx, obj):
        if obj.object_type == 'node-set':
            ids_str = ' '.join(n.string_value() for n in obj.value)
        else:
            ids_str = obj.coerce('string').value
        id_nodes = ctx.node.get_root()._xml_ids
        nodes = set()
        for id_str in ids_str.split():
            node = id_nodes.get(id_str)
            if node is not None:
                nodes.add(node)
        return XPathNodeSet(nodes)

    @xpath_function('node-set?', rtype='string')
    def local_name(ctx, node_set=None):
        if node_set is None:
            return XPathString(ctx.node.name)

        return XPathString(node_set.value[0].name)

    @xpath_function('node-set?', rtype='string')
    def namespace_uri(ctx, node_set=None):
        if node_set is None:
            return XPathString(ctx.node.prefix)

        return XPathString(node_set.value[0].prefix)

    @xpath_function('node-set?', rtype='string')
    def name(ctx, node_set=None):
        # TODO: Fix!
        if node_set is None:
            node_set = XPathNodeSet([ctx.node])

        node = node_set.value[0]
        return XPathString(node.name)
        raise NotImplementedError()

    # String Functions

    @xpath_function('object?', rtype='string')
    def string(ctx, obj=None):
        if obj is None:
            obj = XPathNodeSet([ctx.node])
        return obj.coerce('string')

    @xpath_function('string', 'string', 'string*', rtype='string')
    def concat(ctx, strings):
        return XPathString(u''.join(s.value for s in strings))

    @xpath_function('string', 'string', rtype='boolean')
    def starts_with(ctx, haystack, needle):
        return XPathBoolean(haystack.value.starts_with(needle.value))

    @xpath_function('string', 'string', rtype='boolean')
    def contains(ctx, haystack, needle):
        return XPathBoolean(needle.value in haystack.value)

    @xpath_function('string', 'string', rtype='string')
    def substring_before(ctx, haystack, needle):
        return XPathString(([''] + haystack.value.split(needle.value, 1))[-2])

    @xpath_function('string', 'string', rtype='string')
    def substring_after(ctx, haystack, needle):
        return XPathString((haystack.value.split(needle.value, 1) + [''])[1])

    @xpath_function('string', 'number', 'number?', rtype='string')
    def substring(ctx, haystack, start, length=None):
        start = max(1, int(round(start.value))) - 1
        end = len(haystack)
        if length is not None:
            end = start + int(round(length))
        return XPathString(haystack[start:end])

    @xpath_function('string?', rtype='number')
    def string_length(ctx, text=None):
        if text is None:
            text = XPathString(ctx.node.string_value())
        return XPathNumber(len(text.value))

    @xpath_function('string?', rtype='string')
    def normalize_space(ctx, text=None):
        if text is None:
            text = XPathString(ctx.node.string_value())
        return XPathString(u' '.join(text.value.strip().split()))

    @xpath_function('string', 'string', 'string', rtype='string')
    def translate(ctx, text, from_chars, to_chars):
        # TODO: Implement
        raise NotImplementedError()

    # Boolean Functions

    @xpath_function('object', rtype='boolean')
    def boolean(ctx, obj):
        return obj.coerce('boolean')

    @xpath_function('boolean', rtype='boolean', name='not')
    def xpath_not(ctx, obj):
        return XPathBoolean(not obj.value)

    @xpath_function(rtype='boolean')
    def true(ctx):
        return XPathBoolean(True)

    @xpath_function(rtype='boolean')
    def false(ctx):
        return XPathBoolean(False)

    @xpath_function('string', rtype='boolean')
    def lang(ctx, obj):
        # TODO: Implement
        raise NotImplementedError()

    # Number Functions

    @xpath_function('object?', rtype='number')
    def number(ctx, obj=None):
        if obj is None:
            obj = XPathNodeSet([ctx.node])
        return obj.coerce('number')

    @xpath_function('node-set', rtype='number')
    def sum(ctx, node_set):
        return XPathNumber(sum(n.to_number().value for n in node_set.value))

    @xpath_function('number', rtype='number')
    def floor(ctx, number):
        return XPathNumber(floor(number.value))

    @xpath_function('number', rtype='number')
    def ceil(ctx, number):
        return XPathNumber(ceil(number.value))

    @xpath_function('number', rtype='number')
    def round(ctx, number):
        return XPathNumber(round(number.value))
