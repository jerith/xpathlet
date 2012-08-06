xpathlet
========

A pure Python XPath implementation that operates on ElementTree objects.

The only external dependency is [PLY][1], which is a pure Python lex/yacc
implementation.

Features
--------

At the moment, xpathlet consists of a probably-buggy parser that builds a
probably-broken AST and a definitely-incomplete expression engine that
understands basic location paths and node test. In the future, it will
hopefully be a fully standards-compliant [XPath 1.0][2] implementation that
operates on ElementTree objects.

Why? WHY!?
----------

I've been asking myself that a lot. I need an XPath implementation that doesn't
pull in non-Python dependencies for my XForms implementation that isn't Java.
The expected benefits outweigh the pain, but that may not last forever.


[1]: http://www.dabeaz.com/ply/
[2]: http://www.w3.org/TR/xpath/
