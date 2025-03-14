#!/bin/bash

# Colors for better readability
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Output file
OUTPUT_FILE="project_map.txt"

echo -e "${BLUE}Mapping project structure...${NC}"
echo "Project Map generated on $(date)" > "$OUTPUT_FILE"
echo "----------------------------------------" >> "$OUTPUT_FILE"

# Function to count files of each type
count_files() {
    local pattern=$1
    local count=$(find . -type f -name "$pattern" ! -path "*/node_modules/*" ! -path "*/.git/*" ! -path "*/dist/*" ! -path "*/build/*" ! -path "*/coverage/*" ! -path "*/.next/*" | wc -l)
    echo "$count"
}

# Count different file types
JS_COUNT=$(count_files "*.js")
JSX_COUNT=$(count_files "*.jsx")
TS_COUNT=$(count_files "*.ts")
TSX_COUNT=$(count_files "*.tsx")
CSS_COUNT=$(count_files "*.css")
SCSS_COUNT=$(count_files "*.scss")
HTML_COUNT=$(count_files "*.html")
SQL_COUNT=$(count_files "*.sql")

# Print statistics
echo -e "\n${GREEN}File Statistics:${NC}" >> "$OUTPUT_FILE"
echo "JavaScript files (*.js): $JS_COUNT" >> "$OUTPUT_FILE"
echo "React files (*.jsx): $JSX_COUNT" >> "$OUTPUT_FILE"
echo "TypeScript files (*.ts): $TS_COUNT" >> "$OUTPUT_FILE"
echo "TypeScript React files (*.tsx): $TSX_COUNT" >> "$OUTPUT_FILE"
echo "CSS files: $CSS_COUNT" >> "$OUTPUT_FILE"
echo "SCSS files: $SCSS_COUNT" >> "$OUTPUT_FILE"
echo "HTML files: $HTML_COUNT" >> "$OUTPUT_FILE"
echo "SQL files: $SQL_COUNT" >> "$OUTPUT_FILE"
echo "----------------------------------------" >> "$OUTPUT_FILE"

# Main file listing
echo -e "\n${GREEN}File Listing:${NC}" >> "$OUTPUT_FILE"
find . -type f \
    ! -path "*/node_modules/*" \
    ! -path "*/.git/*" \
    ! -path "*/dist/*" \
    ! -path "*/build/*" \
    ! -path "*/coverage/*" \
    ! -path "*/.next/*" \
    ! -path "*/package-lock.json" \
    ! -path "*/yarn.lock" \
    \( -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" \
       -o -name "*.css" -o -name "*.scss" -o -name "*.html" -o -name "*.sql" \) \
    | sort >> "$OUTPUT_FILE"

# Group files by directory
echo -e "\n${GREEN}Directory Structure:${NC}" >> "$OUTPUT_FILE"
find . -type f \
    ! -path "*/node_modules/*" \
    ! -path "*/.git/*" \
    ! -path "*/dist/*" \
    ! -path "*/build/*" \
    ! -path "*/coverage/*" \
    ! -path "*/.next/*" \
    ! -path "*/package-lock.json" \
    ! -path "*/yarn.lock" \
    \( -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" \
       -o -name "*.css" -o -name "*.scss" -o -name "*.html" -o -name "*.sql" \) \
    | sed 's/[^/]*$//' | sort | uniq -c | sort -nr >> "$OUTPUT_FILE"

echo -e "${BLUE}Project map has been generated in ${YELLOW}$OUTPUT_FILE${NC}"
echo -e "${GREEN}Summary:${NC}"
echo "Total files found: $((JS_COUNT + JSX_COUNT + TS_COUNT + TSX_COUNT + CSS_COUNT + SCSS_COUNT + HTML_COUNT + SQL_COUNT))"
