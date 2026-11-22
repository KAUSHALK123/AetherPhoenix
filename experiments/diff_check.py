import difflib

with open("main_before_final.tex", "r", encoding="utf-8") as f:
    before = f.readlines()
with open("main.tex", "r", encoding="utf-8") as f:
    after = f.readlines()

diff = list(difflib.unified_diff(before, after, fromfile="before", tofile="after"))
print(f"Total diff lines: {len(diff)}")
for line in diff[:50]:
    print(line.rstrip())
