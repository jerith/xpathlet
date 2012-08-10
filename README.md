xpathlet
========

A pure Python XPath implementation that operates on ElementTree objects.

The only external dependency is [PLY][1], which is a pure Python lex/yacc
implementation.

Features
--------

At the moment, xpathlet consists of:

* A probably-buggy parser that builds a probably-broken AST.

* A definitely-incomplete expression engine that understands:
    * Basic location paths and node tests.
    * Positional predicate expressions.
    * Comparison operators.
    * Functions calls.

* A definitely-incomplete core function library.

In the future, it will hopefully be a fully standards-compliant [XPath 1.0][2]
implementation that operates on ElementTree objects. Except maybe not around
namespaces.

Issues
------

There are a few things that are somewhat hard to implement completely, so they
have "good enough" implementations. These might be fixed later.

* Namespace handling is a bit weird. This is mostly a consequence of how
  ElementTree handles namespaces.

* Element IDs are assumed to be in the `id` attribute.

Why? WHY!?
----------

I've been asking myself that a lot. I need an XPath implementation that doesn't
pull in non-Python dependencies for my XForms implementation that isn't Java.
The expected benefits outweigh the pain for now, but that may not last forever.


[1]: http://www.dabeaz.com/ply/
[2]: http://www.w3.org/TR/xpath/
