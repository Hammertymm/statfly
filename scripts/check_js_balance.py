"""Structural sanity check for inline <script> JS in index.html.

Tracks (), [], {} balance while skipping strings, template literals
(including ${} nesting), comments and regex literals. Not a full parser -
a cheap tripwire for unbalanced edits when Node is unavailable.
"""
import re
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else "scorefly/index.html"
html = open(PATH, encoding="utf-8").read()

blocks = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, re.S | re.I)

OPEN = {"(": ")", "[": "]", "{": "}"}
CLOSE = {v: k for k, v in OPEN.items()}


def prev_significant(src, i):
    j = i - 1
    while j >= 0 and src[j] in " \t\r\n":
        j -= 1
    return src[j] if j >= 0 else ""


fail = 0
for bi, src in enumerate(blocks, 1):
    if not src.strip():
        continue
    stack = []   # (char, line, is_interp_opener)
    tpl = []     # template-literal nesting: True while inside template TEXT
    line = 1
    i = 0
    n = len(src)
    err = None
    while i < n and not err:
        c = src[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        if tpl and tpl[-1]:
            # inside template text
            if c == "\\":
                i += 2
                continue
            if c == "`":
                tpl.pop()
                i += 1
                continue
            if c == "$" and i + 1 < n and src[i + 1] == "{":
                tpl[-1] = False           # paused for interpolation
                stack.append(("{", line, True))
                i += 2
                continue
            i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            nl = src.find("\n", i)
            i = n if nl < 0 else nl
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            end = src.find("*/", i + 2)
            stop = n if end < 0 else end + 2
            line += src.count("\n", i, stop)
            i = stop
            continue
        if c in ("'", '"'):
            q = c
            i += 1
            while i < n and src[i] != q:
                if src[i] == "\\":
                    i += 1
                elif src[i] == "\n":
                    line += 1
                i += 1
            i += 1
            continue
        if c == "`":
            tpl.append(True)
            i += 1
            continue
        if c == "/":
            p = prev_significant(src, i)
            tail = src[max(0, i - 7):i].rstrip()
            if p == "" or p in "=([{,;:!&|?+-*%<>~^" or tail.endswith(("return", "typeof", "case")):
                j = i + 1
                incls = False
                ok = False
                while j < n:
                    ch = src[j]
                    if ch == "\\":
                        j += 2
                        continue
                    if ch == "\n":
                        break
                    if ch == "[":
                        incls = True
                    elif ch == "]":
                        incls = False
                    elif ch == "/" and not incls:
                        ok = True
                        break
                    j += 1
                if ok:
                    i = j + 1
                    while i < n and src[i].isalpha():
                        i += 1
                    continue
        if c in OPEN:
            stack.append((c, line, False))
            i += 1
            continue
        if c in CLOSE:
            if not stack:
                err = f"block {bi} line {line}: unmatched '{c}'"
                break
            top, tl, interp = stack.pop()
            if OPEN[top] != c:
                err = f"block {bi} line {line}: expected '{OPEN[top]}' (opened line {tl}), got '{c}'"
                break
            if interp:
                tpl[-1] = True            # resume template text
            i += 1
            continue
        i += 1
    if err:
        print("FAIL:", err)
        fail += 1
    elif stack:
        top, tl, _ = stack[-1]
        print(f"FAIL: block {bi}: unclosed '{top}' opened at line {tl} (+{len(stack) - 1} more)")
        fail += 1
    elif tpl:
        print(f"FAIL: block {bi}: unterminated template literal")
        fail += 1
    else:
        print(f"OK: block {bi} balanced ({line} lines)")

print("FAILURES:", fail)
sys.exit(1 if fail else 0)
