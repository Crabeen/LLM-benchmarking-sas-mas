from pathlib import Path
import re


root = Path(__file__).resolve().parent
main_files = [root / "chapters" / "abstract.tex"] + sorted((root / "chapters").glob("[0-9][0-9]_*.tex"))
all_text = "\n".join(path.read_text(encoding="utf-8") for path in main_files)
plain = re.sub(r"(?m)^%.*$", " ", all_text)
plain = re.sub(r"\\cite\w*\{[^}]*\}", " ", plain)
plain = re.sub(r"\\(?:chapter|section|subsection|caption)\{([^}]*)\}", r" \1 ", plain)
plain = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^]]*\])?(?:\{[^}]*\})?", " ", plain)
plain = re.sub(r"\\.|[{}$&_^~]", " ", plain)
words = re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)*|[0-9]+(?:[.,][0-9]+)*", plain)

bib_text = (root / "references.bib").read_text(encoding="utf-8")
bib_keys = set(re.findall(r"@[A-Za-z]+\{([^,]+),", bib_text))
citation_keys = set()
for path in root.rglob("*.tex"):
    for group in re.findall(r"\\cite\w*\{([^}]+)\}", path.read_text(encoding="utf-8")):
        citation_keys.update(key.strip() for key in group.split(","))

markers = []
pattern = re.compile(r"TODO|PLACEHOLDER|TO BE UPDATED|STUDENT NAME|SUPERVISOR NAME|DEGREE PROGRAMME|\[insert|XXX|TBD", re.I)
for path in root.rglob("*.tex"):
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if pattern.search(line):
            markers.append(f"{path.relative_to(root)}:{number}: {line.strip()}")

print(f"Approximate main-text words: {len(words)}")
print(f"Main-text files: {len(main_files)}")
print(f"Missing citation keys: {sorted(citation_keys - bib_keys)}")
print(f"Unused bibliography keys: {sorted(bib_keys - citation_keys)}")
print("Metadata markers:")
print("\n".join(markers) if markers else "none")
