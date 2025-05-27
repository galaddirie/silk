from typing import Any
from fp_ops.composition import (
    compose,
    fallback,
    parallel,
    pipe,
    sequence,

    transform,
    map,
    filter,
    reduce,
    zip,
    flat_map,
    group_by,
    partition,
    first,
    last,
    gather_operations,
)
from fp_ops.operator import constant, identity

Compose = compose
Fallback = fallback
Parallel = parallel
Pipe = pipe
Sequence = sequence
Identity = identity
Constant = constant

Transform = transform
Map = map
Filter = filter
Reduce = reduce
Zip = zip
FlatMap = flat_map
GroupBy = group_by
Partition = partition
First = first
Last = last
Gather = gather_operations




__all__ = [
    "Compose",
    "Fallback",
    "Parallel",
    "Pipe",
    "Sequence",
    "Identity",
    "Constant",
    "Map",
    "Filter",
    "Reduce",
    "Zip",
    "FlatMap",
    "GroupBy",
    "Partition",
    "First",
    "Last",
    "Gather",
]