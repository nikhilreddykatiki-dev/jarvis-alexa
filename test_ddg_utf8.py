import httpx
import re
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

r = httpx.post("https://html.duckduckgo.com/html/", data={"q": "Juventus top scorer this season"}, headers=headers, timeout=8.0)
titles = re.findall(r'<h2 class="result__title">\s*<a[^>]*class="result__a"[^>]*>(.*?)</a>', r.text, re.DOTALL)
snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', r.text, re.DOTALL)
print("Titles found:", len(titles))
for i in range(min(len(titles), len(snippets), 5)):
    t = re.sub(r'<[^>]+>', '', titles[i]).strip()
    s = re.sub(r'<[^>]+>', '', snippets[i]).strip()
    print(f"[{i+1}] {t}\n    {s}\n")
