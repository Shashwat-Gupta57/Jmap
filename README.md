# Jmap — Java Project Context Mapper

> Generate a clean, structured snapshot of any Java project — classes, fields, methods, and Javadoc — in one `context.txt` file ready to drop straight into an AI chat.

---

## What it does

When you're building something in Java and need planning help from an AI (ChatGPT, Claude, Gemini, etc.), you first need to give the AI context about your codebase. Doing that by hand — copying files, explaining structure — wastes time and eats your token budget.

**Jmap** solves that. Point it at your project folder and it produces a single `context.txt` containing:

- A visual **file tree** of your entire project
- Every **class / interface / enum** found
- All **data members** (fields) with their access modifiers and inline comments
- All **methods**, numbered, with their full signature and attached **Javadoc**
- Your **pom.xml** content (if present)

Paste `context.txt` into your AI chat and start asking questions — the AI will have everything it needs.

---

## Example output

```
================================================================
 JMAP - Java Project Context Mapper
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
         DOC: Returns a user by their unique database ID @param id the user ID @return the User object or null

    [2] void save(User user)
         DOC: (no documentation)

    [3] List<User> findAll()
         DOC: Fetches all active users from the repository
```

---

## Requirements

- **Windows** (the `.bat` launcher is Windows-only; `Jmap.py` runs anywhere Python does)
- **Python 3.8+** — [download here](https://python.org)

---

## Installation (Windows)

1. Download or clone this repo
2. Right-click `Setup.bat` → **Run as administrator**
3. Follow the prompts — Jmap is copied to `%ProgramFiles%\Jmap` and added to your system PATH
4. Open a **new** terminal and you're ready:

```
Jmap "C:\path\to\your\project"
```

### Manual installation (no admin rights)

Copy `Jmap.py` and `Jmap.bat` to any folder, then either:
- Add that folder to your PATH manually, or
- Run directly: `Jmap.bat "My Project"`

---

## Usage

```
Jmap <project_folder> [flags]
```

| Flag | Description |
|---|---|
| *(none)* | Full report saved to `context.txt` inside the project folder |
| `--no-tree` | Omit the file-tree section |
| `--print` | Also print the full report to the console |
| `--help` | Show help and exit |

### Examples

```bat
:: Basic usage — produces context.txt inside the project folder
Jmap "C:\projects\MyApp"

:: Skip the file tree (shorter output for large projects)
Jmap "C:\projects\MyApp" --no-tree

:: Print to console AND save to file
Jmap "C:\projects\MyApp" --print

:: Combine flags
Jmap "C:\projects\MyApp" --no-tree --print
```

---

## What gets skipped

Jmap automatically ignores build artifacts, IDE folders, and dependency caches so you only see your source code:

**Directories:** `build`, `target`, `out`, `bin`, `.gradle`, `.idea`, `.git`, `node_modules`, `lib`, `libs`, `generated`, `classes`, and more.

**File types:** `.class`, `.jar`, `.war`, `.ear`, `.zip`, `.iml`, and other binary/compiled formats.

---

## How to use the output with AI

1. Run Jmap on your project
2. Open `context.txt` from your project folder
3. Copy its contents
4. Paste into your AI chat before asking your question

**Suggested prompt:**
> *"Here is the structure of my Java project. [paste context.txt]. I need help with [your question]."*

---

## Limitations

- **Java only** (more languages planned)
- Method detection works on standard single-line signatures. Multi-line signatures (parameter list split across lines) are not yet captured
- Anonymous inner classes and lambda bodies are intentionally excluded — only top-level class members are listed

---

## Files

| File | Purpose |
|---|---|
| `Jmap.py` | The extractor — run directly with Python on any OS |
| `Jmap.bat` | Windows launcher — calls `Jmap.py` with the same arguments |
| `Setup.bat` | Windows installer — copies to Program Files and adds to PATH |

---

## License

MIT
