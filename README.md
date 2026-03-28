# Jctx — Java Context Extractor

> Scan any Java project and produce a single `context.txt` — classes, fields, methods, and Javadoc — ready to paste into an AI chat for planning and architecture help.

---

## The problem it solves

When you need planning help from an AI (Claude, ChatGPT, Gemini, etc.) on a Java project, you first have to explain your codebase. Copying files one by one, describing structure manually — it's slow and wastes your token budget before you even ask your real question.

**Jctx** fixes that. Point it at your project folder and it generates a single `context.txt` with everything structured and labelled, ready to paste.

---

## What gets extracted

- A visual **file tree** of your project
- Every **class**, **interface**, and **enum**
- All **data members** (fields) with access modifiers and inline comments
- All **methods**, numbered, with full signatures and attached **Javadoc**
- Your **pom.xml** content if present

---

## Example output

```
================================================================
 JCTX - Java Context Extractor
 Project : C:\projects\MyApp
 Date    : 2026-03-28 14:22:01
 Java    : 12 file(s)   |   POM: 1 file(s)
================================================================

================================================================
 SECTION 1 - PROJECT FILE TREE
================================================================

  MyApp\
  ├── src\
  │   └── main\
  │       └── java\
  │           └── com\
  │               └── example\
  │                   ├── App.java
  │                   ├── UserService.java
  │                   └── UserRepository.java
  └── pom.xml

================================================================
 SECTION 2 - CLASS AND MEMBER DETAILS
================================================================

----------------------------------------------------------------
  FILE: src\main\java\com\example\UserService.java
----------------------------------------------------------------

  CLASS: UserService
  DOC  : Handles all user-related business logic

  DATA MEMBERS:
    · private UserRepository repo
    · private static final int MAX_RETRIES

  METHODS:
    [1] User findById(int id)
         DOC: Returns a user by their unique database ID @param id the user ID

    [2] void save(User user)
         DOC: (no documentation)

    [3] List<User> findAll()
         DOC: Fetches all active users from the repository
```

---

## Requirements

- **Python 3.8+** — [download here](https://python.org)
- **Windows** for the `.bat` launcher and installer (`Jctx.py` runs on any OS with Python)

---

## Installation (Windows)

1. Download or clone this repo
2. Right-click `setup.bat` → **Run as administrator**
3. Follow the on-screen prompts
4. Open a **new** terminal — done:

```
Jctx "C:\path\to\your\project"
```

### No admin rights?

Copy `Jctx.py` and `Jctx.bat` to any folder and run directly:

```
Jctx.bat "My Project"
```

Or with Python directly (any OS):

```
python Jctx.py "My Project"
```

---

## Usage

```
Jctx <project_folder> [flags]
```

| Flag | What it does |
|---|---|
| *(none)* | Full report saved to `context.txt` inside the project folder |
| `--no-tree` | Omit the file tree (useful for very large projects) |
| `--print` | Also print the report to the console |
| `--help` | Show help and exit |

### Examples

```bat
Jctx "C:\projects\MyApp"
Jctx "C:\projects\MyApp" --no-tree
Jctx "C:\projects\MyApp" --print
Jctx "C:\projects\MyApp" --no-tree --print
```

---

## Using the output with AI

1. Run Jctx on your project
2. Open `context.txt` from your project folder
3. Copy and paste into your AI chat before your question

**Suggested opener:**
> *"Here is the structure of my Java project: [paste context.txt]. I need help with..."*

---

## What gets skipped automatically

**Directories:** `build`, `target`, `out`, `bin`, `.gradle`, `.idea`, `.git`, `node_modules`, `lib`, `libs`, `generated`, `classes`, and more.

**File types:** `.class`, `.jar`, `.war`, `.ear`, `.zip`, `.iml`, and other compiled/binary formats.

---

## Limitations

- **Java only** — more languages may be added in future
- Multi-line method signatures (parameters split across lines) are not yet captured
- Anonymous inner classes and lambda bodies are intentionally excluded — only direct class members are listed

---

## Files

| File | Purpose |
|---|---|
| `Jctx.py` | The extractor — works on any OS with Python 3.8+ |
| `Jctx.bat` | Windows launcher — wraps `Jctx.py` for command-line use |
| `setup.bat` | Windows installer — copies to `%ProgramFiles%\Jctx` and adds to PATH |

---

## License

MIT
