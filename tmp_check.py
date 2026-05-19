import ast
import sys
import os

os.chdir(r"C:\Users\Eiboer\PycharmProjects\dakinspecties")

with open("app_flet.py", "r", encoding="utf-8") as f:
    src = f.read()

try:
    tree = ast.parse(src)
    print("SYNTAX_OK")
except SyntaxError as e:
    print(f"SYNTAX_ERROR: {e}")

# Check for common issues
lines = src.splitlines()
for i, line in enumerate(lines, 1):
    if "await " in line and "async " not in src.splitlines()[max(0,i-20):i-1] and "async def" not in "\n".join(src.splitlines()[max(0,i-10):i]):
        print(f"WARNING line {i}: 'await' outside async context: {line.strip()}")

