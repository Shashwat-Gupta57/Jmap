"""
Jmap.py  -  Java Project Context Mapper
=======================================

USAGE
  python Jmap.py  <project_folder> [flags]
  Jmap.bat        <project_folder> [flags]

FLAGS
  --no-tree   Skip the file-tree section from the output.
  --print     Also print the full report to this console window.
  --help  -h  Show this help page and exit.

FLAGS CAN BE COMBINED
  --no-tree --print     Both at once, no problem.

EXAMPLES
  Jmap.bat "Tic Tac Toe"
      Full report saved to:  Tic Tac Toe\\context.txt

  Jmap.bat "Tic Tac Toe" --no-tree
      Same report but without the file-tree section.

  Jmap.bat "Tic Tac Toe" --print
      Full report printed to the console AND saved to file.

  Jmap.bat "Tic Tac Toe" --no-tree --print
      No file tree, printed to console AND saved to file.

  Jmap.bat --help
      Show this help page.

OUTPUT FILE
  context.txt   placed inside the project folder.

WHAT IS EXTRACTED PER CLASS
  - Class name and its Javadoc (if present)
  - Data members  (fields): access modifier, type, name, inline comment
  - Methods: numbered list with return type, name, parameters, Javadoc
"""

import sys
import os
import re
from datetime import datetime

# ============================================================
# CONSTANTS
# ============================================================

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


# ============================================================
# HELP
# ============================================================

def print_help():
    print(__doc__)


# ============================================================
# FILE TREE
# ============================================================

def should_skip_dir(name):
    return name.startswith('.') or name.lower() in SKIP_DIRS


def should_skip_file(name):
    _, ext = os.path.splitext(name)
    return ext.lower() in SKIP_EXTENSIONS or name == 'context.txt'


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


# ============================================================
# JAVA PARSER
# ============================================================

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


# ============================================================
# FILE COLLECTORS
# ============================================================

def collect_java_files(project_dir):
    result = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = sorted([d for d in dirs if not should_skip_dir(d)])
        for fname in sorted(files):
            if fname.endswith('.java'):
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


# ============================================================
# TXT RENDERER
# ============================================================

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


def render_txt(project_dir, java_files, pom_files, show_tree):
    out = []
    w   = out.append

    active_flags = []
    if not show_tree:
        active_flags.append('--no-tree')

    w(DIVIDER)
    w(' JMAP - Java Project Context Mapper')
    w(f' Project : {project_dir}')
    w(f' Date    : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    w(f' Java    : {len(java_files)} file(s)   |   POM: {len(pom_files)} file(s)')
    if active_flags:
        w(f' Flags   : {" ".join(active_flags)}')
    w(DIVIDER)
    w('')

    section = 1

    if show_tree:
        w(DIVIDER)
        w(f' SECTION {section} - PROJECT FILE TREE')
        w(DIVIDER)
        w('')
        for line in build_tree_lines(project_dir):
            w('  ' + line)
        w('')
        section += 1

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
            w('')
            try:
                with open(pom_path, encoding='utf-8', errors='replace') as f:
                    for line in f:
                        w('  ' + line.rstrip())
            except Exception as e:
                w(f'  [ERROR: {e}]')
            w('')
        section += 1

    w('')
    w(DIVIDER)
    w(f' SECTION {section} - CLASS AND MEMBER DETAILS')
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

        for cls in result['classes']:
            w('')
            w(f'  CLASS: {cls["name"]}')
            if cls['doc']:
                w(f'  DOC  : {cls["doc"]}')
            w('')

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
                    sig = f'{m["return"]} {m["name"]}({m["params"]})'
                    w(f'    [{i}] {sig}')
                    doc = m['doc'] if m['doc'] else '(no documentation)'
                    w(f'         DOC: {doc}')
                    w('')

    w('')
    w(DIVIDER)
    w(' END OF REPORT')
    w(DIVIDER)

    return '\n'.join(out)


# ============================================================
# MAIN
# ============================================================

def main():
    args = sys.argv[1:]

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

    show_tree = '--no-tree' not in flags
    do_print  = '--print'   in flags

    known_flags = {'--no-tree', '--print', '--help', '-h'}
    unknown = flags - known_flags
    if unknown:
        print(f'[WARN] Unknown flag(s): {", ".join(sorted(unknown))}')
        print('       Run with --help to see available flags.')

    out_file = os.path.join(project, 'context.txt')

    print()
    print(DIVIDER)
    print(' Java Project Extractor')
    print(DIVIDER)
    print(f'  Project    : {project}')
    print(f'  Output     : {out_file}')
    print(f'  File tree  : {"yes" if show_tree else "no  (--no-tree)"}')
    print(f'  Console    : {"yes (--print)" if do_print else "no"}')
    print(DIVIDER)
    print()

    java_files = collect_java_files(project)
    pom_files  = find_pom_files(project)

    if not java_files:
        print(f'[ERROR] No .java files found in: {project}')
        sys.exit(1)

    print(f'  Java files : {len(java_files)}')
    if pom_files:
        print(f'  POM files  : {len(pom_files)}')
    print()

    report = render_txt(project, java_files, pom_files, show_tree)

    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(report)

    if do_print:
        print()
        print(report)

    print()
    print(f'  Saved to: {out_file}')
    print()


if __name__ == '__main__':
    main()