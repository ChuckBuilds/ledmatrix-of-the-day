#!/usr/bin/env python3
"""
List all JSON data files in the of_the_day directory.
Returns file metadata including entry count, size, and modification time.
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime

# Get plugin directory
LEDMATRIX_ROOT = os.environ.get('LEDMATRIX_ROOT', os.getcwd())
plugin_dir = Path(LEDMATRIX_ROOT) / 'plugins' / 'ledmatrix-of-the-day'
data_dir = plugin_dir / 'of_the_day'

# Read params from stdin if provided (optional for this script)
try:
    stdin_input = sys.stdin.read().strip()
    if stdin_input:
        params = json.loads(stdin_input)
except (json.JSONDecodeError, ValueError):
    # No params or invalid JSON, continue without params
    params = {}

if not data_dir.exists():
    print(json.dumps({
        'status': 'success',
        'files': []
    }))
    sys.exit(0)

files = []
for file_path in data_dir.glob('*.json'):
    try:
        # Get file stats
        stat = file_path.stat()
        
        # Read and parse JSON to count entries
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            entry_count = len(data) if isinstance(data, dict) else 0
        
        # Extract category name from filename
        category_name = file_path.stem
        
        files.append({
            'filename': file_path.name,
            'category_name': category_name,
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'entry_count': entry_count
        })
    except Exception as e:
        # Skip files that can't be read
        continue

# Sort by filename
files.sort(key=lambda x: x['filename'])

print(json.dumps({
    'status': 'success',
    'files': files
}))

