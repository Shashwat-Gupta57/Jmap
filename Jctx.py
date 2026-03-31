"""
Jctx.py  -  Java & Kotlin Context Extractor
============================================

USAGE
  python Jctx.py <project_folder> [flags]
  Jctx.bat       <project_folder> [flags]

FLAGS
  --no-tree     Skip the file-tree section from the output.
  --print       Also print the full report to this console window.
  --md          Output in Markdown format (context.md instead of context.txt).
  --slim        Slim mode: output only class names + method signatures.
  --clipboard   Copy the output to your clipboard after saving.
  --version     Show version information and exit.
  --help  -h    Show this help page and exit.

JCTXIGNORE
  Place a .jctxignore file in the project root to exclude additional
  directories or files from context extraction. Supports:
    dirname/          Skip directories named 'dirname'
    *.test.java       Skip files matching the glob pattern
    **/test/**        Skip any directory named 'test'
    # comment         Lines starting with # are ignored

FLAGS CAN BE COMBINED
  --no-tree --print       Both at once, no problem.
  --md --print            Markdown report, also printed.
  --slim --clipboard      Slim report, copied to clipboard.

EXAMPLES
  Jctx.bat "Tic Tac Toe"
      Full report saved to:  Tic Tac Toe\\context.txt

  Jctx.bat "Tic Tac Toe" --no-tree
      Same report but without the file-tree section.

  Jctx.bat "Tic Tac Toe" --print
      Full report printed to the console AND saved to file.

  Jctx.bat "Tic Tac Toe" --md
      Markdown report saved to:  Tic Tac Toe\\context.md

  Jctx.bat "Tic Tac Toe" --slim
      Slim report: only class names and method signatures.

  Jctx.bat "Tic Tac Toe" --clipboard
      Full report saved AND copied to clipboard.

  Jctx.bat "Tic Tac Toe" --no-tree --print
      No file tree, printed to console AND saved to file.

  Jctx.bat --help
      Show this help page.

  Jctx.bat --version
      Show version information.

OUTPUT FILE
  context.txt   placed inside the project folder  (default)
  context.md    placed inside the project folder  (with --md)

WHAT IS EXTRACTED PER CLASS
  - Class name and its Javadoc/KDoc (if present)
  - Data members  (fields/properties): access modifier, type, name, inline comment
  - Methods/Functions: numbered list with return type, name, parameters, documentation
"""

import sys
import os
import re
import fnmatch
import platform
import subprocess
from datetime import datetime

# ── Ensure UTF-8 console output on Windows ────────────────────
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ===================================================
# VERSION
# ===================================================

VERSION = '1.5.0'

# ===================================================
# CONSTANTS
# ===================================================

SKIP_DIRS = {
    'build', 'target', 'out', 'bin', 'dist', 'output',
    '.gradle', '.mvn', '.idea', '.vscode', '.settings',
    '__pycache__', 'node_modules',
    '.git', '.svn', '.hg',
    'lib', 'libs', 'vendor',
    'generated-sources', 'generated',
    'test-classes', 'classes',
}

SKIP_EXTENSIONS = {
    '.class', '.jar', '.war', '.ear', '.zip', '.tar', '.gz',
    '.iml', '.ipr', '.iws', '.DS_Store',
}

SKIP_WORDS = {
    'if', 'while', 'for', 'switch', 'catch', 'try', 'else', 'do',
    'return', 'new', 'throw', 'assert', 'case', 'synchronized',
    'finally', 'break', 'continue', 'import', 'package', 'super',
    'this', 'instanceof', 'null', 'true', 'false',
}

MODIFIERS = {
    'public', 'private', 'protected', 'static', 'final',
    'synchronized', 'abstract', 'native', 'default', 'transient',
    'volatile', 'strictfp',
}

ACCESS_MODS = {'public', 'private', 'protected'}

CLASS_RE = re.compile(
    r'(?:public|protected|private|abstract|final|\s)*'
    r'(?:class|interface|enum)\s+(\w+)'
)

FIELD_RE = re.compile(
    r'^([\w<>\[\].,\s?]+?)\s+(\w+)\s*(?:=.*)?;\s*$'
)

TEE   = '\u251C\u2500\u2500 '
LAST  = '\u2514\u2500\u2500 '
PIPE  = '\u2502   '
BLANK = '    '

DIVIDER = '=' * 64
SUBDIV  = '-' * 64

# ── Kotlin-specific constants ────────────────────────────────

KT_MODIFIERS = {
    'public', 'private', 'protected', 'internal',
    'open', 'final', 'abstract', 'sealed',
    'override', 'inline', 'noinline', 'crossinline',
    'suspend', 'tailrec', 'operator', 'infix', 'external',
    'const', 'lateinit', 'actual', 'expect', 'annotation',
    'inner', 'companion',
}

KT_ACCESS_MODS = {'public', 'private', 'protected', 'internal'}

KT_CLASS_RE = re.compile(
    r'\b(?:data\s+|sealed\s+|enum\s+|abstract\s+|open\s+|inner\s+|annotation\s+)*'
    r'(?:class|interface|object)\s+(\w+)'
)

KT_FUNC_RE = re.compile(
    r'\bfun\s+(?:<[^>]+>\s+)?(\w+)\s*\('
)

KT_PROP_RE = re.compile(
    r'\b(val|var)\s+(\w+)\s*(?::\s*([\w<>\[\].,\s?]+?))?(?:\s*=.*)?$'
)

KT_SKIP_WORDS = {
    'if', 'when', 'for', 'while', 'try', 'catch', 'finally',
    'return', 'throw', 'break', 'continue', 'import', 'package',
    'is', 'as', 'in', 'null', 'true', 'false', 'this', 'super',
}


# ===================================================
# .jctxignore SUPPORT
# ===================================================

EXTRA_SKIP_DIRS = set()
EXTRA_SKIP_PATTERNS = []


def parse_jctxignore(project_dir):
    """
    Load .jctxignore from the project root and populate
    EXTRA_SKIP_DIRS and EXTRA_SKIP_PATTERNS.
    """
    global EXTRA_SKIP_DIRS, EXTRA_SKIP_PATTERNS
    EXTRA_SKIP_DIRS = set()
    EXTRA_SKIP_PATTERNS = []

    ignore_path = os.path.join(project_dir, '.jctxignore')
    if not os.path.isfile(ignore_path):
        return

    try:
        with open(ignore_path, encoding='utf-8', errors='replace') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue

                # **/dirname/** -> directory pattern
                if line.startswith('**/') and line.endswith('/**'):
                    dir_name = line[3:-3]
                    if dir_name:
                        EXTRA_SKIP_DIRS.add(dir_name)
                    continue

                # dirname/ -> directory pattern
                if line.endswith('/'):
                    dir_name = line.rstrip('/')
                    if '/' in dir_name:
                        dir_name = dir_name.rsplit('/', 1)[-1]
                    if dir_name:
                        EXTRA_SKIP_DIRS.add(dir_name)
                    continue

                # File glob pattern (e.g. *.test.java)
                EXTRA_SKIP_PATTERNS.append(line)
    except Exception:
        pass


# ===================================================
# TOKEN ESTIMATION
# ===================================================

# Approximate tokens per word for English/code text.
# Standard ratio is ~1.3 for most LLM tokenizers.
TOKENS_PER_WORD = 1.3

def estimate_tokens(text):
    """Estimate LLM token count from text using word-count heuristic."""
    word_count = len(text.split())
    return int(word_count * TOKENS_PER_WORD)


# AI model context windows (name, token_limit)
AI_MODELS = [
    ('Llama 4 Scout',  10_000_000),
    ('Gemini 3.1',      2_000_000),
    ('Grok',            2_000_000),
    ('GPT-5.4',         1_000_000),
    ('Claude 4.6',      1_000_000),
    ('Qwen 3',          1_000_000),
    ('Llama 4 Maverick',1_000_000),
    ('Kimi K2.5',         256_000),
    ('Mistral Large 3',   256_000),
    ('DeepSeek V3',       128_000),
]


def _format_limit(n):
    """Format a token limit like 1,000,000 → '1M', 256,000 → '256K'."""
    if n >= 1_000_000:
        val = n / 1_000_000
        return f'{val:g}M'
    elif n >= 1_000:
        val = n / 1_000
        return f'{val:g}K'
    return str(n)


def _count_source_tokens(file_list):
    """Read raw source files and return total estimated tokens."""
    total = 0
    for fp in file_list:
        try:
            with open(fp, encoding='utf-8', errors='replace') as f:
                total += estimate_tokens(f.read())
        except Exception:
            pass
    return total


def print_language_percentages(java_tokens, kotlin_tokens):
    """
    Print language composition percentages to the console.
    Shows what percentage of source code is Java vs Kotlin.
    """
    source_total = java_tokens + kotlin_tokens
    if source_total == 0:
        return

    print()
    print(DIVIDER)
    print(' LANGUAGE PERCENTAGES')
    print(DIVIDER)

    entries = []
    if java_tokens > 0:
        entries.append(('Java', java_tokens))
    if kotlin_tokens > 0:
        entries.append(('Kotlin', kotlin_tokens))

    for lang, tokens in entries:
        pct = tokens / source_total * 100
        bar_len = int(pct / 2)   # 50 chars = 100%
        bar = '█' * bar_len + '░' * (50 - bar_len)
        print(f'  {lang:8s}: {pct:5.1f}%  {bar}  (~{tokens:,} tokens)')

    print(DIVIDER)


def print_token_summary(total_tokens, section_tokens):
    """
    Print token estimate and language breakdown to the console.

    section_tokens: dict with keys like 'java', 'kotlin', 'build', 'tree'
                    and values being estimated token counts.
    """
    print()
    print(DIVIDER)
    print(' TOKEN ESTIMATE')
    print(DIVIDER)
    print(f'  Total tokens : ~{total_tokens:,}')
    print()

    # Language breakdown
    if total_tokens > 0:
        print('  Language Breakdown:')
        for label, key in [('Java', 'java'), ('Kotlin', 'kotlin'),
                           ('Build files', 'build'), ('File tree', 'tree')]:
            t = section_tokens.get(key, 0)
            if t > 0:
                pct = t / total_tokens * 100
                print(f'    {label:12s}: ~{t:>8,}  ({pct:5.1f}%)')
        print()

    # AI context window fit
    print('  Context Window Fit:')
    row = []
    for name, limit in AI_MODELS:
        mark = 'Y' if total_tokens <= limit else 'N'
        short = _format_limit(limit)
        entry = f'{mark} {name} ({short})'
        row.append(entry)

    # Print 3 per line
    for i in range(0, len(row), 3):
        chunk = row[i:i+3]
        print('    ' + '   '.join(f'{e:<24s}' for e in chunk))

    print(DIVIDER)
    print()


# ===================================================
# CLIPBOARD
# ===================================================

def copy_to_clipboard(text):
    """Copy text to the system clipboard. Zero dependencies, cross-platform."""
    system = platform.system()
    try:
        if system == 'Windows':
            process = subprocess.Popen(['clip'], stdin=subprocess.PIPE)
            process.communicate(text.encode('utf-16-le'))
        elif system == 'Darwin':
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            process.communicate(text.encode('utf-8'))
        else:
            # Linux — try xclip, then xsel
            try:
                process = subprocess.Popen(
                    ['xclip', '-selection', 'clipboard'],
                    stdin=subprocess.PIPE
                )
                process.communicate(text.encode('utf-8'))
            except FileNotFoundError:
                process = subprocess.Popen(
                    ['xsel', '--clipboard', '--input'],
                    stdin=subprocess.PIPE
                )
                process.communicate(text.encode('utf-8'))
        return True
    except Exception:
        return False


# ===================================================
# HELP
# ===================================================

def print_help():
    print(__doc__)


# ===================================================
# FILE TREE
# ===================================================

def should_skip_dir(name):
    low = name.lower()
    return (name.startswith('.')
            or low in SKIP_DIRS
            or name in EXTRA_SKIP_DIRS
            or low in EXTRA_SKIP_DIRS)


def should_skip_file(name):
    _, ext = os.path.splitext(name)
    if ext.lower() in SKIP_EXTENSIONS or name in ('context.txt', 'context.md'):
        return True
    for pattern in EXTRA_SKIP_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def build_tree_lines(root_dir):
    result = []
    result.append(os.path.basename(root_dir) + os.sep)
    _recurse_tree(root_dir, prefix='', result=result)
    return result


def _recurse_tree(directory, prefix, result):
    try:
        raw = os.listdir(directory)
    except PermissionError:
        return

    entries = sorted(raw, key=lambda x: (
        os.path.isfile(os.path.join(directory, x)), x.lower()
    ))

    filtered = []
    for entry in entries:
        full = os.path.join(directory, entry)
        if os.path.isdir(full):
            if not should_skip_dir(entry):
                filtered.append((entry, full, True))
        else:
            if not should_skip_file(entry):
                filtered.append((entry, full, False))

    for i, (name, full, is_dir) in enumerate(filtered):
        is_last   = (i == len(filtered) - 1)
        connector = LAST if is_last else TEE
        label     = name + (os.sep if is_dir else '')
        result.append(prefix + connector + label)
        if is_dir:
            _recurse_tree(full, prefix + (BLANK if is_last else PIPE), result)


# ===================================================
# JAVA PARSER
# ===================================================

def strip_modifiers(tokens):
    """
    Remove leading modifier keywords and annotations from a token list.
    Returns the remaining tokens as a list.
    """
    out = []
    skip = True
    for tok in tokens:
        if skip and (tok in MODIFIERS or tok.startswith('@')):
            continue
        skip = False
        out.append(tok)
    return out


def _get_access(raw_line):
    for word in raw_line.split():
        if word in ACCESS_MODS:
            return word
    return ''


def _get_extra_mods(raw_line):
    extras = []
    for word in raw_line.split():
        if word in MODIFIERS and word not in ACCESS_MODS:
            extras.append(word)
    return extras


def _inline_comment(raw_line):
    idx = raw_line.find('//')
    if idx != -1:
        return raw_line[idx + 2:].strip()
    return ''


def _net_braces(line):
    """
    Net brace change for a line, ignoring braces inside string/char literals.
    """
    opens = closes = 0
    in_str = in_char = esc = False
    for c in line:
        if esc:
            esc = False
            continue
        if c == '\\':
            esc = True
            continue
        if c == '"' and not in_char:
            in_str = not in_str
            continue
        if c == "'" and not in_str:
            in_char = not in_char
            continue
        if in_str or in_char:
            continue
        if c == '{':
            opens += 1
        elif c == '}':
            closes += 1
    return opens - closes


def _try_parse_method(line):
    """
    Given a line with modifiers already stripped and trailing {/; removed,
    try to parse it as a method declaration.

    Strategy:
      - Find the LAST ')' — that closes the parameter list.
      - Walk left to find the matching '(' — everything inside is params.
      - Everything before '(' is  <return_type>  <method_name>.

    Returns (return_type, method_name, params_str) or None.
    """
    rp = line.rfind(')')
    if rp == -1:
        return None

    # Walk left from rp to find matching (
    depth = 0
    lp = -1
    for i in range(rp, -1, -1):
        if line[i] == ')':
            depth += 1
        elif line[i] == '(':
            depth -= 1
            if depth == 0:
                lp = i
                break
    if lp == -1:
        return None

    params = line[lp + 1:rp].strip()
    before = line[:lp].strip()

    # Reject assignment expressions — real method declarations never have '=' before '('.
    # e.g. 'File x = new File(...)' or 'Image img = new Image(...)'
    if '=' in before:
        return None

    # 'before' must be  <return_type> <name>  (at least 2 tokens)
    # or just <name> for a constructor
    parts = before.split()
    if not parts:
        return None

    if len(parts) == 1:
        # Constructor (no return type)
        name = parts[0]
        ret  = ''
    else:
        name = parts[-1]
        ret  = ' '.join(parts[:-1])

    # Validate the method name
    if not re.match(r'^[A-Za-z_$][\w$]*$', name):
        return None
    if name in SKIP_WORDS:
        return None
    if ret in SKIP_WORDS:
        return None

    return ret, name, params


def parse_java_file(path):
    """
    Parse a .java file and return a dict:
      {
        'classes': [
          {
            'name':    str,
            'doc':     str,
            'fields':  [ {'access': str, 'mods': [str], 'type': str,
                          'name': str, 'comment': str} ],
            'methods': [ {'return': str, 'name': str, 'params': str,
                          'doc': str} ]
          }
        ]
      }

    Brace-depth model
    -----------------
    We track brace_depth as the ABSOLUTE depth (0 = file top-level).

    When we see a class declaration we record class_depth = the depth
    AFTER counting all braces on that same line.  So the interior of
    the class body lives at brace_depth == class_depth.

    We are "at the class top level" (i.e. looking at direct members)
    when depth_before_line == class_depth - 1, which means the line
    we're examining opens (or is at) the first level inside the class.

    The key fix vs the previous version:
      OLD: checked brace_depth AFTER updating it for the current line
           → method lines that contain { were wrongly treated as
             being inside a nested block and skipped.
      NEW: check depth_before_line (the depth before we process the
           current line's braces) against class_depth - 1.
    """
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            raw_lines = f.readlines()
    except Exception as e:
        return {'error': str(e), 'classes': []}

    classes          = []
    current_class    = None
    in_doc           = False
    doc_lines        = []
    pending_doc      = ''
    in_block_comment = False
    brace_depth      = 0
    class_depth      = -1   # depth of the class body interior; -1 = no class yet

    for raw in raw_lines:
        t        = raw.strip()
        raw_full = raw.rstrip()

        # ── Non-Javadoc block comment  /* ... */  ────────────────────
        if not in_doc and not in_block_comment and '/*' in t and '/**' not in t:
            in_block_comment = True
        if in_block_comment:
            if '*/' in t:
                in_block_comment = False
            continue

        # ── Javadoc  /** ... */  ──────────────────────────────────────
        if '/**' in t:
            # Single-line Javadoc  /** text */  — open and close on the same line
            if '*/' in t:
                _js = t.index('/**') + 3
                _je = t.index('*/', _js)
                _jc = t[_js:_je].strip().lstrip('*').strip()
                if _jc:
                    pending_doc = _jc
                # in_doc stays False — the block is already closed
            else:
                in_doc    = True
                doc_lines = []
            continue

        if in_doc:
            if '*/' in t:
                in_doc      = False
                pending_doc = ' '.join(doc_lines).strip()
            else:
                cleaned = re.sub(r'^\*\s?', '', t).strip()
                if cleaned:
                    doc_lines.append(cleaned)
            continue

        # ── Skip blanks and single-line comments  ────────────────────
        if not t or t.startswith('//') or t.startswith('*'):
            continue

        # ── Capture depth BEFORE we account for this line's braces  ──
        depth_before = brace_depth
        brace_depth += _net_braces(t)

        # ── Class / Interface / Enum declaration  ────────────────────
        cm = CLASS_RE.search(t)
        if cm and re.search(r'\b(class|interface|enum)\b', t):
            # class_depth = the depth INSIDE the class body after this line.
            # brace_depth is already updated for this line, so:
            #   public class Foo {   → depth_before=0, brace_depth=1 → class_depth=1
            # Member lines will have depth_before == class_depth (== 1).
            class_depth   = brace_depth
            current_class = {
                'name':    cm.group(1),
                'doc':     pending_doc,
                'fields':  [],
                'methods': [],
            }
            classes.append(current_class)
            pending_doc = ''
            continue

        # ── No class open yet  ───────────────────────────────────────
        if current_class is None:
            pending_doc = ''
            continue

        # ── Gate: only process direct members of the class  ──────────
        # A direct member line sits at depth_before == class_depth.
        # (depth_before is the depth before we count the line's own braces,
        #  so a method opening its own { doesn't disqualify itself.)
        if depth_before != class_depth:
            pending_doc = ''
            continue

        # ── Prepare a modifier-stripped version of the line  ─────────
        tokens       = t.split()
        clean_tokens = strip_modifiers(tokens)
        clean        = ' '.join(clean_tokens)
        # Strip trailing // comment from clean.
        # We can't just find('//') because URLs like "https://..." contain // inside strings.
        # Safe approach: if the line contains ';', truncate clean at the last ';'.
        # That removes any trailing comment while preserving string-literal content.
        if ';' in clean:
            _lsc = clean.rfind(';')
            clean = clean[:_lsc + 1].strip()

        # Remove method body on same line: truncate at first '{'
        # Also strip trailing ';' for abstract/interface methods.
        _brace_idx = clean.find('{')
        clean_for_match = (clean[:_brace_idx] if _brace_idx != -1 else clean).rstrip(';').strip()

        # ── Method detection  ────────────────────────────────────────
        if '(' in clean_for_match:
            parsed = _try_parse_method(clean_for_match)
            if parsed:
                ret, mname, params = parsed
                current_class['methods'].append({
                    'return': ret,
                    'name':   mname,
                    'params': params,
                    'doc':    pending_doc,
                })
                pending_doc = ''
                continue

        # ── Field detection  ─────────────────────────────────────────
        # Also match field initialisers like  'File x = new File(...);'
        # that contain '(' but ARE assignments (not method calls).
        _is_field_init = ';' in t and '=' in clean and '(' in clean
        if (';' in t and '(' not in t) or _is_field_init:
            fm = FIELD_RE.match(clean)
            if fm:
                ftype = fm.group(1).strip()
                fname = fm.group(2).strip()

                if (ftype not in SKIP_WORDS
                        and fname not in SKIP_WORDS
                        and not fname[0].isdigit()
                        and ',' not in ftype          # reject enum constant lists
                        and ftype not in ('return', 'throw', 'import', 'package')):

                    access  = _get_access(t)
                    extras  = _get_extra_mods(t)
                    comment = _inline_comment(raw_full)

                    current_class['fields'].append({
                        'access':  access,
                        'mods':    extras,
                        'type':    ftype,
                        'name':    fname,
                        'comment': comment,
                    })
                    pending_doc = ''
                    continue

        pending_doc = ''

    return {'classes': classes}


# ===================================================
# KOTLIN PARSER
# ===================================================

def _kt_strip_modifiers(tokens):
    """
    Remove leading Kotlin modifier keywords and annotations from a token list.
    """
    out = []
    skip = True
    for tok in tokens:
        if skip and (tok in KT_MODIFIERS or tok.startswith('@')):
            continue
        skip = False
        out.append(tok)
    return out


def _kt_get_access(raw_line):
    for word in raw_line.split():
        if word in KT_ACCESS_MODS:
            return word
    return ''


def _kt_get_extra_mods(raw_line):
    extras = []
    for word in raw_line.split():
        if word in KT_MODIFIERS and word not in KT_ACCESS_MODS:
            extras.append(word)
    return extras


def _kt_try_parse_fun(clean_line):
    """
    Try to parse a Kotlin function declaration.

    Expects a line like:
      fun myFunc(param: Type, param2: Type): ReturnType
      fun <T> myFunc(param: T): List<T>

    Returns (return_type, func_name, params_str) or None.
    """
    m = KT_FUNC_RE.search(clean_line)
    if not m:
        return None

    func_name = m.group(1)
    if func_name in KT_SKIP_WORDS:
        return None

    # Extract params: everything between the matching ( and )
    start = clean_line.index('(', m.start())
    depth = 0
    end = -1
    for i in range(start, len(clean_line)):
        if clean_line[i] == '(':
            depth += 1
        elif clean_line[i] == ')':
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        return None

    params = clean_line[start + 1:end].strip()

    # Return type: everything after ): up to { or end
    after_paren = clean_line[end + 1:].strip()
    ret_type = ''
    if after_paren.startswith(':'):
        ret_part = after_paren[1:].strip()
        # Truncate at { or = (expression body)
        for ch in ('{', '='):
            idx = ret_part.find(ch)
            if idx != -1:
                ret_part = ret_part[:idx].strip()
        ret_type = ret_part

    return ret_type, func_name, params


def parse_kotlin_file(path):
    """
    Parse a .kt file and return a dict with the same shape as parse_java_file:
      {
        'classes': [
          {
            'name':    str,
            'doc':     str,
            'fields':  [ {'access': str, 'mods': [str], 'type': str,
                          'name': str, 'comment': str} ],
            'methods': [ {'return': str, 'name': str, 'params': str,
                          'doc': str} ]
          }
        ]
      }

    Uses brace-depth tracking like the Java parser.
    Also captures top-level (file-scope) functions and properties
    under a synthetic "(top-level)" class.

    Kotlin class handling
    ---------------------
    A Kotlin class declaration may span multiple lines when it has a
    primary constructor:

        data class Product(
            val id: Long,
            val name: String
        ) {
            fun foo() { ... }
        }

    We handle this with two phases:
      1. When we see the class keyword, we record the class and set
         `awaiting_body = True` to indicate we haven't seen '{' yet.
         While awaiting, any `val`/`var` params are constructor properties.
      2. When we finally see '{' (possibly on a `) {` line), we set
         `class_depth = brace_depth` and `awaiting_body = False`.
    """
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            raw_lines = f.readlines()
    except Exception as e:
        return {'error': str(e), 'classes': []}

    classes          = []
    # Synthetic top-level container for file-scope declarations
    top_level        = {
        'name':    '(top-level)',
        'doc':     '',
        'fields':  [],
        'methods': [],
    }
    current_class    = None
    in_doc           = False
    doc_lines        = []
    pending_doc      = ''
    in_block_comment = False
    brace_depth      = 0
    class_depth      = -1
    awaiting_body    = False   # True when class declared but '{' not yet seen

    for raw in raw_lines:
        t        = raw.strip()
        raw_full = raw.rstrip()

        # ── Non-KDoc block comment  /* ... */  ───────────────────────
        if not in_doc and not in_block_comment and '/*' in t and '/**' not in t:
            in_block_comment = True
        if in_block_comment:
            if '*/' in t:
                in_block_comment = False
            continue

        # ── KDoc  /** ... */  ────────────────────────────────────────
        if '/**' in t:
            if '*/' in t:
                _js = t.index('/**') + 3
                _je = t.index('*/', _js)
                _jc = t[_js:_je].strip().lstrip('*').strip()
                if _jc:
                    pending_doc = _jc
            else:
                in_doc    = True
                doc_lines = []
            continue

        if in_doc:
            if '*/' in t:
                in_doc      = False
                pending_doc = ' '.join(doc_lines).strip()
            else:
                cleaned = re.sub(r'^\*\s?', '', t).strip()
                if cleaned:
                    doc_lines.append(cleaned)
            continue

        # ── Skip blanks and single-line comments  ────────────────────
        if not t or t.startswith('//') or t.startswith('*'):
            continue

        # ── Capture depth BEFORE this line's braces  ─────────────────
        depth_before = brace_depth
        brace_depth += _net_braces(t)

        # ── Class / Interface / Object declaration  ──────────────────
        cm = KT_CLASS_RE.search(t)
        if cm and re.search(r'\b(class|interface|object)\b', t):
            # Skip import/package lines that happen to contain these words
            if t.startswith('import ') or t.startswith('package '):
                pending_doc = ''
                continue

            current_class = {
                'name':    cm.group(1),
                'doc':     pending_doc,
                'fields':  [],
                'methods': [],
            }
            classes.append(current_class)
            pending_doc = ''

            # Check if the class body opens on this line
            if '{' in t:
                class_depth  = brace_depth
                awaiting_body = False
            else:
                # Body not opened yet (e.g. constructor params follow)
                class_depth   = -1
                awaiting_body = True
            continue

        # ── While awaiting class body '{' — capture constructor val/var
        if awaiting_body and current_class is not None:
            # Check if the opening brace appears on this line
            if '{' in t:
                class_depth   = brace_depth
                awaiting_body = False

            # Extract constructor val/var properties from these lines
            pm = KT_PROP_RE.search(t)
            if pm:
                kind  = pm.group(1)       # val or var
                pname = pm.group(2)
                ptype = (pm.group(3) or '').strip()
                # Clean trailing comma from type
                ptype = ptype.rstrip(',').strip()

                if pname not in KT_SKIP_WORDS and pname and not pname[0].isdigit():
                    access = _kt_get_access(t)
                    extras = _kt_get_extra_mods(t)
                    extras.insert(0, kind)

                    current_class['fields'].append({
                        'access':  access,
                        'mods':    extras,
                        'type':    ptype if ptype else '(inferred)',
                        'name':    pname,
                        'comment': _inline_comment(raw_full),
                    })

            # If line is just `) {` or `)` with no val/var, just continue
            pending_doc = ''
            continue

        # ── Determine target for this declaration  ───────────────────
        # Reset class tracking when we return to file top-level
        if depth_before == 0 and class_depth > 0:
            class_depth = -1

        # At class member level (depth_before == class_depth), use current_class.
        # At file top-level (depth_before == 0, no active class body), use top_level.
        target = None
        if current_class is not None and class_depth > 0 and depth_before == class_depth:
            target = current_class
        elif depth_before == 0 and class_depth <= 0:
            target = top_level

        if target is None:
            pending_doc = ''
            continue

        # ── Build a modifier-stripped version  ────────────────────────
        tokens       = t.split()
        clean_tokens = _kt_strip_modifiers(tokens)
        clean        = ' '.join(clean_tokens)

        # Remove trailing // comment
        comment_idx = clean.find('//')
        inline_comment = ''
        if comment_idx != -1:
            inline_comment = clean[comment_idx + 2:].strip()
            clean = clean[:comment_idx].strip()

        # Truncate at first '{'
        _brace_idx = clean.find('{')
        if _brace_idx != -1:
            clean = clean[:_brace_idx].strip()

        # ── Function detection  ──────────────────────────────────────
        if 'fun ' in clean or clean.startswith('fun '):
            parsed = _kt_try_parse_fun(clean)
            if parsed:
                ret, fname, params = parsed
                target['methods'].append({
                    'return': ret if ret else 'Unit',
                    'name':   fname,
                    'params': params,
                    'doc':    pending_doc,
                })
                pending_doc = ''
                continue

        # ── Property detection (val / var)  ──────────────────────────
        pm = KT_PROP_RE.search(clean)
        if pm:
            kind     = pm.group(1)       # val or var
            pname    = pm.group(2)
            ptype    = pm.group(3) or ''  # may be None if type is inferred
            ptype    = ptype.strip()

            if pname not in KT_SKIP_WORDS and pname and not pname[0].isdigit():
                access = _kt_get_access(t)
                extras = _kt_get_extra_mods(t)
                extras.insert(0, kind)    # prepend val/var as a modifier

                if not inline_comment:
                    inline_comment = _inline_comment(raw_full)

                target['fields'].append({
                    'access':  access,
                    'mods':    extras,
                    'type':    ptype if ptype else '(inferred)',
                    'name':    pname,
                    'comment': inline_comment,
                })
                pending_doc = ''
                continue

        pending_doc = ''

    # Only include top-level if it has content
    result_classes = []
    if top_level['fields'] or top_level['methods']:
        result_classes.append(top_level)
    result_classes.extend(classes)

    return {'classes': result_classes}


# ===================================================
# FILE COLLECTORS
# ===================================================

def collect_java_files(project_dir):
    result = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = sorted([d for d in dirs if not should_skip_dir(d)])
        for fname in sorted(files):
            if fname.endswith('.java') and not should_skip_file(fname):
                result.append(os.path.join(root, fname))
    return result


def collect_kotlin_files(project_dir):
    result = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = sorted([d for d in dirs if not should_skip_dir(d)])
        for fname in sorted(files):
            if fname.endswith('.kt') and not should_skip_file(fname):
                result.append(os.path.join(root, fname))
    return result


def find_pom_files(project_dir):
    result = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = sorted([d for d in dirs if not should_skip_dir(d)])
        for fname in sorted(files):
            if fname == 'pom.xml':
                result.append(os.path.join(root, fname))
    return result


def find_gradle_files(project_dir):
    result = []
    gradle_names = {'build.gradle', 'build.gradle.kts', 'settings.gradle', 'settings.gradle.kts'}
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = sorted([d for d in dirs if not should_skip_dir(d)])
        for fname in sorted(files):
            if fname in gradle_names:
                result.append(os.path.join(root, fname))
    return result


# ===================================================
# DEPENDENCY GRAPH
# ===================================================

IMPORT_RE = re.compile(r'^\s*import\s+(?:static\s+)?([\w.]+)\s*(?:as\s+\w+)?\s*;?\s*$')


def build_dependency_graph(java_files, kotlin_files):
    """
    Build a dependency graph of project-internal class references.
    Scans import statements and cross-references with known project classes.
    Returns dict: { 'ClassName': sorted(['DepA', 'DepB', ...]) }
    """
    # Step 1: Collect all class names from parsed files
    all_classes = set()
    file_classes = {}  # filepath -> list of class names in that file

    for fp in (java_files or []):
        result = parse_java_file(fp)
        names = [c['name'] for c in result.get('classes', [])]
        file_classes[fp] = names
        all_classes.update(names)

    for fp in (kotlin_files or []):
        result = parse_kotlin_file(fp)
        names = [c['name'] for c in result.get('classes', [])
                 if c['name'] != '(top-level)']
        file_classes[fp] = names
        all_classes.update(names)

    if not all_classes:
        return {}

    # Step 2: For each file, scan import statements for project-internal refs
    graph = {}

    for fp in list(java_files or []) + list(kotlin_files or []):
        classes_in_file = file_classes.get(fp, [])
        if not classes_in_file:
            continue

        deps = set()
        try:
            with open(fp, encoding='utf-8', errors='replace') as f:
                for line in f:
                    m = IMPORT_RE.match(line)
                    if m:
                        parts = m.group(1).split('.')
                        imported_name = parts[-1]
                        if imported_name == '*':
                            continue
                        if imported_name in all_classes:
                            deps.add(imported_name)
        except Exception:
            pass

        for cls_name in classes_in_file:
            existing = set(graph.get(cls_name, []))
            existing.update(deps)
            existing.discard(cls_name)  # remove self-references
            graph[cls_name] = sorted(existing)

    return graph


def print_dependency_graph(graph):
    """Print the project-internal dependency graph to the console."""
    if not graph:
        return

    print()
    print(DIVIDER)
    print(' DEPENDENCY GRAPH (project-internal)')
    print(DIVIDER)

    for cls_name in sorted(graph.keys()):
        deps = graph[cls_name]
        if deps:
            print(f'  {cls_name} \u2192 {", ".join(deps)}')
        else:
            print(f'  {cls_name} \u2192 (none)')

    print(DIVIDER)


# ===================================================
# TXT RENDERER
# ===================================================

def _format_field(f):
    parts = []
    if f['access']:
        parts.append(f['access'])
    parts.extend(f['mods'])
    parts.append(f['type'])
    parts.append(f['name'])
    line = ' '.join(parts)
    if f['comment']:
        line += f'   // {f["comment"]}'
    return line


def _render_classes_txt(w, classes, label, slim=False):
    """Render a list of parsed classes in TXT format."""
    for cls in classes:
        w('')
        w(f'  {label}: {cls["name"]}')
        if not slim and cls['doc']:
            w(f'  DOC  : {cls["doc"]}')
        w('')

        if not slim:
            if cls['fields']:
                w('  DATA MEMBERS:')
                for fld in cls['fields']:
                    w('    · ' + _format_field(fld))
                w('')
            else:
                w('  DATA MEMBERS: (none found)')
                w('')

        if not cls['methods']:
            w('  METHODS: (none found)')
            w('')
        else:
            w('  METHODS:')
            for i, m in enumerate(cls['methods'], 1):
                ret = m['return']
                sig = f'{ret} {m["name"]}({m["params"]})' if ret else f'{m["name"]}({m["params"]})'
                w(f'    [{i}] {sig}')
                if not slim:
                    doc = m['doc'] if m['doc'] else '(no documentation)'
                    w(f'         DOC: {doc}')
                    w('')


def render_txt(project_dir, java_files, kotlin_files, pom_files, gradle_files, show_tree, slim=False):
    out = []
    w   = out.append

    active_flags = []
    if not show_tree:
        active_flags.append('--no-tree')
    if slim:
        active_flags.append('--slim')

    # ── Stats line  ──────────────────────────────────────────────
    stats_parts = []
    if java_files:
        stats_parts.append(f'Java: {len(java_files)} file(s)')
    if kotlin_files:
        stats_parts.append(f'Kotlin: {len(kotlin_files)} file(s)')
    stats_parts.append(f'POM: {len(pom_files)} file(s)')
    if gradle_files:
        stats_parts.append(f'Gradle: {len(gradle_files)} file(s)')

    w(DIVIDER)
    w(f' JCTX v{VERSION} - Java & Kotlin Context Extractor')
    w(f' Project : {project_dir}')
    w(f' Date    : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    w(f' Files   : {" | ".join(stats_parts)}')
    if active_flags:
        w(f' Flags   : {" ".join(active_flags)}')
    w(DIVIDER)
    w('')

    section = 1

    # ── File Tree  ───────────────────────────────────────────────
    if show_tree:
        w(DIVIDER)
        w(f' SECTION {section} - PROJECT FILE TREE')
        w(DIVIDER)
        w('')
        for line in build_tree_lines(project_dir):
            w('  ' + line)
        w('')
        section += 1

    # ── POM.XML  ─────────────────────────────────────────────────
    if pom_files:
        w('')
        w(DIVIDER)
        w(f' SECTION {section} - POM.XML CONTENT')
        w(DIVIDER)
        for pom_path in pom_files:
            rel = pom_path[len(project_dir):].lstrip(os.sep)
            w('')
            w(SUBDIV)
            w(f'  FILE: {rel}')
            w(SUBDIV)
            if not slim:
                w('')
                try:
                    with open(pom_path, encoding='utf-8', errors='replace') as f:
                        for line in f:
                            w('  ' + line.rstrip())
                except Exception as e:
                    w(f'  [ERROR: {e}]')
            w('')
        section += 1

    # ── GRADLE FILES  ────────────────────────────────────────────
    if gradle_files:
        w('')
        w(DIVIDER)
        w(f' SECTION {section} - GRADLE BUILD FILES')
        w(DIVIDER)
        for gradle_path in gradle_files:
            rel = gradle_path[len(project_dir):].lstrip(os.sep)
            w('')
            w(SUBDIV)
            w(f'  FILE: {rel}')
            w(SUBDIV)
            if not slim:
                w('')
                try:
                    with open(gradle_path, encoding='utf-8', errors='replace') as f:
                        for line in f:
                            w('  ' + line.rstrip())
                except Exception as e:
                    w(f'  [ERROR: {e}]')
            w('')
        section += 1

    # ── Java Classes  ────────────────────────────────────────────
    if java_files:
        w('')
        w(DIVIDER)
        w(f' SECTION {section} - JAVA CLASS AND MEMBER DETAILS')
        w(DIVIDER)

        for fp in java_files:
            rel    = fp[len(project_dir):].lstrip(os.sep)
            result = parse_java_file(fp)

            w('')
            w(SUBDIV)
            w(f'  FILE: {rel}')
            w(SUBDIV)

            if 'error' in result:
                w(f'  [ERROR: {result["error"]}]')
                continue

            if not result['classes']:
                w('  (no classes found)')
                continue

            _render_classes_txt(w, result['classes'], 'CLASS', slim=slim)

        section += 1

    # ── Kotlin Classes  ──────────────────────────────────────────
    if kotlin_files:
        w('')
        w(DIVIDER)
        w(f' SECTION {section} - KOTLIN CLASS AND MEMBER DETAILS')
        w(DIVIDER)

        for fp in kotlin_files:
            rel    = fp[len(project_dir):].lstrip(os.sep)
            result = parse_kotlin_file(fp)

            w('')
            w(SUBDIV)
            w(f'  FILE: {rel}')
            w(SUBDIV)

            if 'error' in result:
                w(f'  [ERROR: {result["error"]}]')
                continue

            if not result['classes']:
                w('  (no classes/objects found)')
                continue

            _render_classes_txt(w, result['classes'], 'CLASS', slim=slim)

        section += 1

    w('')
    w(DIVIDER)
    w(' END OF REPORT')
    w(DIVIDER)

    return '\n'.join(out)


# ===================================================
# MARKDOWN RENDERER
# ===================================================

def _format_field_md(f):
    """Format a field for a Markdown table row."""
    access = f['access'] if f['access'] else '-'
    mods   = ' '.join(f['mods']) if f['mods'] else '-'
    ftype  = f['type']
    fname  = f['name']
    comment = f['comment'] if f['comment'] else ''
    # Escape pipes in table cells
    for val in (access, mods, ftype, fname, comment):
        val = val.replace('|', '\\|')
    return f'| {access} | {mods} | `{ftype}` | `{fname}` | {comment} |'


def _render_classes_md(w, classes, label, slim=False):
    """Render a list of parsed classes in Markdown format."""
    for cls in classes:
        w('')
        w(f'### {label}: `{cls["name"]}`')
        if not slim and cls['doc']:
            w(f'> {cls["doc"]}')
        w('')

        # Fields table (skip in slim mode)
        if not slim:
            if cls['fields']:
                w('**Data Members:**')
                w('')
                w('| Access | Modifiers | Type | Name | Comment |')
                w('|--------|-----------|------|------|---------|')
                for fld in cls['fields']:
                    w(_format_field_md(fld))
                w('')
            else:
                w('**Data Members:** *(none found)*')
                w('')

        # Methods list
        if not cls['methods']:
            w('**Methods:** *(none found)*')
            w('')
        else:
            w('**Methods:**')
            w('')
            for i, m in enumerate(cls['methods'], 1):
                ret = m['return']
                sig = f'{ret} {m["name"]}({m["params"]})' if ret else f'{m["name"]}({m["params"]})'
                w(f'{i}. `{sig}`')
                if not slim:
                    doc = m['doc'] if m['doc'] else '*(no documentation)*'
                    w(f'   - {doc}')
            w('')


def render_md(project_dir, java_files, kotlin_files, pom_files, gradle_files, show_tree, slim=False):
    out = []
    w   = out.append

    # ── Stats  ───────────────────────────────────────────────────
    stats_parts = []
    if java_files:
        stats_parts.append(f'**Java:** {len(java_files)} file(s)')
    if kotlin_files:
        stats_parts.append(f'**Kotlin:** {len(kotlin_files)} file(s)')
    stats_parts.append(f'**POM:** {len(pom_files)} file(s)')
    if gradle_files:
        stats_parts.append(f'**Gradle:** {len(gradle_files)} file(s)')

    w(f'# JCTX v{VERSION} — Context Report')
    w('')
    w(f'- **Project:** `{project_dir}`')
    w(f'- **Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    w(f'- **Files:** {" · ".join(stats_parts)}')
    w('')
    w('---')

    section = 1

    # ── File Tree  ───────────────────────────────────────────────
    if show_tree:
        w('')
        w(f'## {section}. Project File Tree')
        w('')
        w('```')
        for line in build_tree_lines(project_dir):
            w(line)
        w('```')
        w('')
        section += 1

    # ── POM.XML  ─────────────────────────────────────────────────
    if pom_files:
        w(f'## {section}. POM.XML Content')
        w('')
        for pom_path in pom_files:
            rel = pom_path[len(project_dir):].lstrip(os.sep)
            w(f'#### `{rel}`')
            if not slim:
                w('')
                w('```xml')
                try:
                    with open(pom_path, encoding='utf-8', errors='replace') as f:
                        w(f.read().rstrip())
                except Exception as e:
                    w(f'<!-- ERROR: {e} -->')
                w('```')
            w('')
        section += 1

    # ── GRADLE FILES  ────────────────────────────────────────────
    if gradle_files:
        w(f'## {section}. Gradle Build Files')
        w('')
        for gradle_path in gradle_files:
            rel  = gradle_path[len(project_dir):].lstrip(os.sep)
            w(f'#### `{rel}`')
            if not slim:
                lang = 'kotlin' if gradle_path.endswith('.kts') else 'groovy'
                w('')
                w(f'```{lang}')
                try:
                    with open(gradle_path, encoding='utf-8', errors='replace') as f:
                        w(f.read().rstrip())
                except Exception as e:
                    w(f'// ERROR: {e}')
                w('```')
            w('')
        section += 1

    # ── Java Classes  ────────────────────────────────────────────
    if java_files:
        w(f'## {section}. Java Class & Member Details')
        w('')
        for fp in java_files:
            rel    = fp[len(project_dir):].lstrip(os.sep)
            result = parse_java_file(fp)

            w(f'#### 📄 `{rel}`')

            if 'error' in result:
                w(f'> ⚠️ ERROR: {result["error"]}')
                w('')
                continue

            if not result['classes']:
                w('*(no classes found)*')
                w('')
                continue

            _render_classes_md(w, result['classes'], 'Class', slim=slim)

        w('---')
        w('')
        section += 1

    # ── Kotlin Classes  ──────────────────────────────────────────
    if kotlin_files:
        w(f'## {section}. Kotlin Class & Member Details')
        w('')
        for fp in kotlin_files:
            rel    = fp[len(project_dir):].lstrip(os.sep)
            result = parse_kotlin_file(fp)

            w(f'#### 📄 `{rel}`')

            if 'error' in result:
                w(f'> ⚠️ ERROR: {result["error"]}')
                w('')
                continue

            if not result['classes']:
                w('*(no classes/objects found)*')
                w('')
                continue

            _render_classes_md(w, result['classes'], 'Class', slim=slim)

        w('---')
        w('')
        section += 1

    w('---')
    w('*End of report.*')

    return '\n'.join(out)


# ===================================================
# MAIN
# ===================================================

def main():
    args = sys.argv[1:]

    if '--version' in args or '-v' in args:
        print(f'Jctx v{VERSION}')
        sys.exit(0)

    if not args or '--help' in args or '-h' in args:
        print_help()
        sys.exit(0)

    flags      = {a.lower() for a in args if a.startswith('-')}
    positional = [a for a in args if not a.startswith('-')]

    if not positional:
        print('[ERROR] No project folder provided.')
        print('Run with --help for usage information.')
        sys.exit(1)

    project = os.path.abspath(positional[0])
    if not os.path.isdir(project):
        print(f'[ERROR] Not a directory: {project}')
        sys.exit(1)

    # ── Load .jctxignore ──────────────────────────────────────────
    parse_jctxignore(project)
    has_jctxignore = bool(EXTRA_SKIP_DIRS or EXTRA_SKIP_PATTERNS)

    show_tree    = '--no-tree'   not in flags
    do_print     = '--print'     in flags
    do_md        = '--md'        in flags
    do_slim      = '--slim'      in flags
    do_clipboard = '--clipboard' in flags

    known_flags = {
        '--no-tree', '--print', '--help', '-h', '--version', '-v',
        '--md', '--slim', '--clipboard',
    }
    unknown = flags - known_flags
    if unknown:
        print(f'[WARN] Unknown flag(s): {", ".join(sorted(unknown))}')
        print('       Run with --help to see available flags.')

    ext      = '.md' if do_md else '.txt'
    out_file = os.path.join(project, 'context' + ext)

    print()
    print(DIVIDER)
    print(f' JCTX v{VERSION} - Java & Kotlin Context Extractor')
    print(DIVIDER)
    print(f'  Project    : {project}')
    print(f'  Output     : {out_file}')
    print(f'  Format     : {"Markdown" if do_md else "Plain text"}')
    print(f'  File tree  : {"yes" if show_tree else "no  (--no-tree)"}')
    print(f'  Slim mode  : {"yes (--slim)" if do_slim else "no"}')
    print(f'  Clipboard  : {"yes (--clipboard)" if do_clipboard else "no"}')
    print(f'  Console    : {"yes (--print)" if do_print else "no"}')
    if has_jctxignore:
        print(f'  .jctxignore: yes ({len(EXTRA_SKIP_DIRS)} dirs, {len(EXTRA_SKIP_PATTERNS)} patterns)')
    print(DIVIDER)
    print()

    java_files   = collect_java_files(project)
    kotlin_files = collect_kotlin_files(project)
    pom_files    = find_pom_files(project)
    gradle_files = find_gradle_files(project)

    if not java_files and not kotlin_files:
        print(f'[ERROR] No .java or .kt files found in: {project}')
        sys.exit(1)

    if java_files:
        print(f'  Java files   : {len(java_files)}')
    if kotlin_files:
        print(f'  Kotlin files : {len(kotlin_files)}')
    if pom_files:
        print(f'  POM files    : {len(pom_files)}')
    if gradle_files:
        print(f'  Gradle files : {len(gradle_files)}')
    print()

    # ── Generate report  ──────────────────────────────────────────
    if do_md:
        report = render_md(project, java_files, kotlin_files, pom_files,
                           gradle_files, show_tree, slim=do_slim)
    else:
        report = render_txt(project, java_files, kotlin_files, pom_files,
                            gradle_files, show_tree, slim=do_slim)

    # ── Save  ─────────────────────────────────────────────────────
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(report)

    if do_print:
        print()
        print(report)

    print()
    print(f'  Saved to: {out_file}')

    # ── Clipboard  ────────────────────────────────────────────────
    if do_clipboard:
        if copy_to_clipboard(report):
            print(f'  Copied to clipboard!')
        else:
            print(f'  [WARN] Could not copy to clipboard.')

    # ── Language percentages (always, console only)  ──────────────
    java_src_tokens   = _count_source_tokens(java_files)   if java_files   else 0
    kotlin_src_tokens = _count_source_tokens(kotlin_files) if kotlin_files else 0

    print_language_percentages(java_src_tokens, kotlin_src_tokens)

    # ── Dependency graph (always, console only)  ─────────────────
    dep_graph = build_dependency_graph(java_files, kotlin_files)
    print_dependency_graph(dep_graph)

    # ── Token summary (always, console only)  ────────────────────
    total_tokens = estimate_tokens(report)

    # Break down tokens by section from raw source content.
    section_tokens = {}

    if show_tree:
        tree_text = '\n'.join(build_tree_lines(project))
        section_tokens['tree'] = estimate_tokens(tree_text)

    if java_src_tokens > 0:
        section_tokens['java'] = java_src_tokens

    if kotlin_src_tokens > 0:
        section_tokens['kotlin'] = kotlin_src_tokens

    # Build file tokens (POM + Gradle)
    build_tokens = _count_source_tokens((pom_files or []) + (gradle_files or []))
    if build_tokens > 0:
        section_tokens['build'] = build_tokens

    print_token_summary(total_tokens, section_tokens)


if __name__ == '__main__':
    main()
