import sys
import os

# Add project root to Python path
# This allows imports like 'from shared.models import ...' to work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))