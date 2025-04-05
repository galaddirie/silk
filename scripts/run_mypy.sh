#!/bin/bash
# Run mypy on the project

echo "Running mypy on silk package..."
mypy src/silk

# Exit with the same code as mypy
exit $? 