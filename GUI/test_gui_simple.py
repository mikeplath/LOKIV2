#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

print("Testing imports...")

try:
    from loki_config import get_config
    print("✓ loki_config imported")
    
    config = get_config()
    print("✓ config loaded")
    print(f"Config type: {type(config)}")
    
    test_value = config.get("paths.loki_dir")
    print(f"✓ config.get() works: {test_value}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("Test complete")
