#!/bin/bash
# Script to add license headers to all Python files in the project

LICENSE_HEADER="$(cat LICENSE_HEADER.txt)"
TEMP_FILE=$(mktemp)

find src -name "*.py" -type f | while read -r file; do
    if ! grep -q "Copyright 2025 firefly" "$file"; then
        echo "Adding license header to $file"
        {
            echo "$LICENSE_HEADER"
            echo ""
            cat "$file"
        } > "$TEMP_FILE"
        mv "$TEMP_FILE" "$file"
    else
        echo "License header already exists in $file"
    fi
done

echo "License headers have been added to all Python files." 