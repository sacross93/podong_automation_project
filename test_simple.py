#!/usr/bin/env python
print("Hello World!")
print("Python is working!")

try:
    import flet as ft
    print("✅ Flet imported successfully!")
    print(f"Flet version: {ft.__version__}")
except Exception as e:
    print(f"❌ Flet import failed: {e}")

input("Press Enter to continue...")





