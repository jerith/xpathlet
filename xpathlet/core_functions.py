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
        raise NotImplementedError()

    @xpath_function('node-set?', rtype='string')
    def local_name(ctx, node_set=None):
        raise NotImplementedError()

    @xpath_function('node-set?', rtype='string')
    def namespace_uri(ctx, node_set=None):
        raise NotImplementedError()

    @xpath_function('node-set?', rtype='string')
    def name(ctx, node_set=None):
        raise NotImplementedError()

    # String Functions

    @xpath_function('object?', rtype='string')
    def string(ctx, obj=None):
        if obj is None:
            obj = XPathNodeSet([ctx.node])
        return obj.to_string()

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
        return len(text.value)

    @xpath_function('string?', rtype='string')
    def normalize_space(ctx, text=None):
        if text is None:
            text = XPathString(ctx.node.string_value())
        return u' '.join(text.value.strip().split())

    @xpath_function('string', 'string', 'string', rtype='string')
    def translate(ctx, text, from_chars, to_chars):
        raise NotImplementedError()

    # Boolean Functions

    # TODO: These.

    # Number Functions

    # TODO: These.
