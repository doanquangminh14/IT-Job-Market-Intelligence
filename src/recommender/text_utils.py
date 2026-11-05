"""Tiền xử lý văn bản cho TF-IDF: bảo tồn token IT đặc thù và chữ có dấu tiếng Việt."""
import re

# (regex, token thay thế) - áp dụng trên chuỗi đã lower-case, token thay thế chỉ gồm [a-z0-9]
_TECH_REPLACEMENTS = [
    (re.compile(r"(?<![\w+])c\+\+(?![\w+])"), " cpp "),
    (re.compile(r"(?<![\w#])c#(?![\w#])"), " csharp "),
    (re.compile(r"(?<![\w])(?:asp)?\.net(?:\s*core)?(?![\w])"), " dotnet "),
    (re.compile(r"(?<![\w])node\.?js(?![\w])"), " nodejs "),
    (re.compile(r"(?<![\w])react\.?js(?![\w])"), " reactjs "),
    (re.compile(r"(?<![\w])vue\.?js(?![\w])"), " vuejs "),
    (re.compile(r"(?<![\w])next\.?js(?![\w])"), " nextjs "),
    (re.compile(r"(?<![\w])ci\s*/\s*cd(?![\w])"), " cicd "),
    (re.compile(r"(?<![\w])a\s*/\s*b\s+test"), " abtest"),
    (re.compile(r"(?<![\w])pl\s*/\s*sql(?![\w])"), " plsql "),
    (re.compile(r"(?<![\w])ui\s*/\s*ux(?![\w])|(?<![\w])ux\s*/\s*ui(?![\w])"), " uiux "),
    (re.compile(r"(?<![\w])front[\s-]?end(?![\w])"), " frontend "),
    (re.compile(r"(?<![\w])back[\s-]?end(?![\w])"), " backend "),
    (re.compile(r"(?<![\w])full[\s-]?stack(?![\w])"), " fullstack "),
]


def normalize_tech_text(text: str) -> str:
    """Lower-case + thay C++/C#/.NET/CI-CD... bằng token ASCII để tokenizer không làm mất."""
    s = str(text).lower()
    for pat, rep in _TECH_REPLACEMENTS:
        s = pat.sub(rep, s)
    return s


# Token: chữ/số unicode (giữ nguyên tiếng Việt có dấu), tối thiểu 2 ký tự
TOKEN_PATTERN = r"(?u)\b\w\w+\b"
