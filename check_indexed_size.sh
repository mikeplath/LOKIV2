#!/bin/bash

# LOKI Indexed Data Size Checker
# This script will check the size of the indexed data and provide detailed information

# Define color codes for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Define paths
INDEXED_DIR="/home/mike/LOKI/indexed_data"
DATABASE_DIR="/home/mike/LOKI/DATABASE/survivorlibrary"

# Print header
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}LOKI Indexed Data Size Report${NC}"
echo -e "${BLUE}============================================${NC}"
echo "Date & Time: $(date)"
echo ""

# Check if indexed data directory exists
if [ ! -d "$INDEXED_DIR" ]; then
    echo -e "${RED}ERROR: Indexed data directory not found at:${NC}"
    echo "$INDEXED_DIR"
    echo "The indexing process may not have started yet."
    exit 1
fi

# Calculate sizes
INDEXED_SIZE=$(du -sh "$INDEXED_DIR" 2>/dev/null | cut -f1)
INDEXED_BYTES=$(du -s "$INDEXED_DIR" 2>/dev/null | cut -f1)
DATABASE_SIZE=$(du -sh "$DATABASE_DIR" 2>/dev/null | cut -f1)
DATABASE_BYTES=$(du -s "$DATABASE_DIR" 2>/dev/null | cut -f1)

# Calculate percentage
if [ -n "$DATABASE_BYTES" ] && [ -n "$INDEXED_BYTES" ] && [ "$DATABASE_BYTES" -gt 0 ]; then
    PERCENTAGE=$(echo "scale=2; ($INDEXED_BYTES * 100) / $DATABASE_BYTES" | bc)
else
    PERCENTAGE="unknown"
fi

# Count files
PDF_COUNT=$(find "$DATABASE_DIR" -name "*.pdf" 2>/dev/null | wc -l)
INDEXED_COUNT=$(find "$INDEXED_DIR" -name "*.json" 2>/dev/null | wc -l)

# Calculate percentage of files indexed
if [ "$PDF_COUNT" -gt 0 ]; then
    FILES_PERCENTAGE=$(echo "scale=2; ($INDEXED_COUNT * 100) / $PDF_COUNT" | bc)
else
    FILES_PERCENTAGE="unknown"
fi

# Print results
echo -e "${YELLOW}Size Information:${NC}"
echo "- Indexed data size: $INDEXED_SIZE"
echo "- Original database size: $DATABASE_SIZE"
echo "- Percentage of original size: $PERCENTAGE%"
echo ""
echo -e "${YELLOW}File Counts:${NC}"
echo "- PDF files in database: $PDF_COUNT"
echo "- Indexed JSON files: $INDEXED_COUNT"
echo "- Percentage of files indexed: $FILES_PERCENTAGE%"
echo ""

# Check for specific categories
echo -e "${YELLOW}Category Breakdown:${NC}"
for category in $(find "$DATABASE_DIR" -mindepth 1 -maxdepth 1 -type d -printf "%f\n" | sort); do
    CATEGORY_PDFS=$(find "$DATABASE_DIR/$category" -name "*.pdf" 2>/dev/null | wc -l)
    if [ "$CATEGORY_PDFS" -gt 0 ]; then
        echo "- $category: $CATEGORY_PDFS PDFs"
    fi
done

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}Report Complete${NC}"
echo -e "${BLUE}============================================${NC}"
