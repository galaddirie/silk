from typing import Any
from fp_ops.composition import (
    compose,
    fallback,
    parallel,
    pipe,
    sequence,

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
from fp_ops.operator import constant, identity, Operation

Compose = compose
Fallback = fallback
Parallel = parallel
Pipe = pipe
Sequence = sequence
Identity: Operation[Any, Any, Any] = identity
Constant = constant

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
