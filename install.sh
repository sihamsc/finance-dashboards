#!/bin/bash
# ============================================================
# install.sh — run from ~/Desktop/Projects/finance-dashboards
# Backs up old view files, installs new ones
# ============================================================

VIEWS_DIR="src/views"
ARCHIVE_DIR="src/views/archive/$(date +%Y%m%d_%H%M%S)"

echo "Creating archive at $ARCHIVE_DIR..."
mkdir -p "$ARCHIVE_DIR"

# Archive all existing view files
for f in overview.py revenue.py cogs.py fixed_cost.py margin.py \
          labor.py contribution.py pipeline.py targets.py; do
    if [ -f "$VIEWS_DIR/$f" ]; then
        cp "$VIEWS_DIR/$f" "$ARCHIVE_DIR/$f"
        echo "  Archived: $f"
    fi
done

echo ""
echo "Installing new view files..."

# Copy new files in (assumes they are in the same directory as this script)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

for f in overview.py revenue.py cogs.py fixed_cost.py margin.py \
          labor.py contribution.py pipeline.py targets.py; do
    if [ -f "$SCRIPT_DIR/$f" ]; then
        cp "$SCRIPT_DIR/$f" "$VIEWS_DIR/$f"
        echo "  Installed: $f"
    else
        echo "  MISSING: $f (not found in $SCRIPT_DIR)"
    fi
done

echo ""
echo "Done. Old files archived to: $ARCHIVE_DIR"
echo "Run: streamlit run app.py"
