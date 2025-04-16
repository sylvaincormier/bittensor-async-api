#!/usr/bin/env python3
"""
Sanity check script that parses a directory recursively and searches for potential errors.
"""

import os
import re
import sys
from typing import List, Tuple

def find_potential_errors(file_path: str) -> List[Tuple[int, str, str]]:
    """
    Parse a file and look for potential errors.
    
    Returns a list of tuples (line_number, line, error_type)
    """
    errors = []
    error_patterns = [
        (r'TODO', 'TODO item remaining'),
        (r'FIXME', 'FIXME item remaining'),
        (r'raise\s+NotImplemented', 'NotImplemented raised'),
        (r'print\(', 'Print statement found'),
        (r'pdb\.set_trace', 'Debugger breakpoint'),
        (r'import\s+ipdb', 'Debugger import'),
        (r'except\s*:', 'Bare except clause'),
        (r'except\s+Exception\s*:', 'Too broad exception handler'),
        (r'pass\s*$', 'Empty pass statement'),
        (r'\.\\|//|/\*|\*/', 'Suspicious comment pattern'),
        (r'hardcoded|hard-coded|hard coded', 'Possible hardcoded value'),
        (r'sleep\(', 'Sleep call may block async'),
        (r'time\.sleep', 'Time sleep call may block async'),
        (r'[^\w]token[^\w]|[^\w]secret[^\w]|[^\w]password[^\w]|[^\w]apikey[^\w]', 'Possible credential in code'),
    ]
    
    # Skip certain directories and files
    ignored_dirs = ['.git', '.venv', 'venv', '__pycache__', 'node_modules', '.pytest_cache']
    ignored_extensions = ['.pyc', '.pyo', '.so', '.o', '.a', '.c', '.dll', '.lib', '.egg', '.whl']
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines, 1):
            for pattern, error_type in error_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    errors.append((i, line.strip(), error_type))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return errors

def check_directory(directory: str) -> List[Tuple[str, List[Tuple[int, str, str]]]]:
    """
    Recursively check a directory for potential errors.
    
    Returns a list of tuples (file_path, errors)
    """
    results = []
    
    # Skip certain directories
    ignored_dirs = ['.git', '.venv', 'venv', '__pycache__', 'node_modules', '.pytest_cache']
    ignored_extensions = ['.pyc', '.pyo', '.so', '.o', '.a', '.c', '.dll', '.lib', '.egg', '.whl']
    
    for root, dirs, files in os.walk(directory):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        
        for file in files:
            # Skip files with ignored extensions
            if any(file.endswith(ext) for ext in ignored_extensions):
                continue
                
            file_path = os.path.join(root, file)
            errors = find_potential_errors(file_path)
            
            if errors:
                results.append((file_path, errors))
    
    return results

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <directory>")
        sys.exit(1)
    
    directory = sys.argv[1]
    
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a directory")
        sys.exit(1)
    
    print(f"Scanning directory: {directory}")
    results = check_directory(directory)
    
    if not results:
        print("No potential errors found. Great job!")
        return
    
    error_count = sum(len(errors) for _, errors in results)
    print(f"Found {error_count} potential issues in {len(results)} files:")
    
    for file_path, errors in results:
        print(f"\n{file_path}:")
        for line_num, line, error_type in errors:
            print(f"  Line {line_num}: {error_type}")
            print(f"    {line}")

if __name__ == "__main__":
    main()
