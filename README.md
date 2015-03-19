xpathlet
========

A pure Python XPath implementation that operates on ElementTree objects.

The only external dependency is [PLY][1], which is a pure Python lex/yacc
implementation. (There is also a alternate parser which uses [parsley][2], but
that's currently much slower and is therefore not the default.)

xpathlet is covered by the MIT license. See the LICENSE file for details.

Features
--------

At the moment, xpathlet consists of:

* A probably-buggy parser that builds a probably-broken AST.

* A definitely-incomplete expression engine that understands:
    * Basic location paths and node tests.
    * Positional predicate expressions.
    * Comparison and arithmetic operators.
    * Functions calls.

* A definitely-incomplete core function library.

In the future, it will hopefully be a fully standards-compliant [XPath 1.0][3]
implementation that operates on ElementTree objects. Except maybe not around
namespaces.

Issues
------

There are a few things that are somewhat hard to implement completely, so they
have "good enough" implementations. These might be fixed later.

* Namespace handling is a bit weird. This is mostly a consequence of how
  ElementTree handles namespaces.

* Element IDs are assumed to be in the `id` attribute.

Testing
-------

There aren't very many unit tests around the actual implementation (yet), but
there is a test harness (`conformance.py`) to run the subset of the
[OASIS XSLT test suite v0.4][4] (not included) that relates to XPath.

The harness includes a half-hearted partial implementation of some of XSLT.
This should not be considered an actual XSLT implementation.

Why? WHY!?
----------

I've been asking myself that a lot. I need an XPath implementation that doesn't
pull in non-Python dependencies for my XForms implementation that isn't Java.
The expected benefits outweigh the pain for now, but that may not last forever.


[1]: http://www.dabeaz.com/ply/
[2]: http://pypi.python.org/pypi/Parsley
[3]: http://www.w3.org/TR/xpath/
[4]: https://www.oasis-open.org/committees/documents.php?wg_abbrev=xslt
