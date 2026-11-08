"""Hace que pytest encuentre el paquete src desde la raíz del proyecto."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
