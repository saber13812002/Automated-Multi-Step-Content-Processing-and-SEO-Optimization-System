#!/bin/bash

INPUT_DIR="/mnt/data/saberprojects/iranseda-crawler-golang-/downloads"
OUTPUT_DIR="/mnt/data/saberprojects/iranseda-crawler-golang-/downloads/cleaned"

mkdir -p "$OUTPUT_DIR"

for file in "$INPUT_DIR"/*.srt; do
  echo "Cleaning $file ..."
  python3 srt_cleaner.py "$file" --output "$OUTPUT_DIR/$(basename "$file")"
done
