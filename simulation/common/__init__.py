"""Shared deterministic primitives for the independent simulation models.

These utilities are infrastructure, not model logic. Both Founder models use
one implementation of checked arithmetic, RFC 8785 canonical bytes, and the
accepted `D(label)` domain separation so their digest rules cannot diverge.
"""
