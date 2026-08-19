"""The ordered Founder Economy manifest loader, bound to a contract table.

Version two and version three of the manifest differ by one channel identifier
and by their own schema string, domain label, and digest. Every acceptance
stage, every failure code, and every checked derivation is the same. Copying
the loader for the rename would create a second place for it to drift, and the
drift would be silent because each copy would agree with itself.

So the loader lives here once and each accepted version binds it to its own
contract table. The version packages keep their own module names and public
functions, so a caller still asks version two's loader for version two.
"""
