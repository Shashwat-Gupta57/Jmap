![Demo GIF](./JctxSample.gif)
# Jctx — Give AI full understanding of your Java & Kotlin codebase

**Stop pasting files. Get real architecture-aware answers.**

**Generate complete project context in seconds.**

**Turn any Java or Kotlin project into a single AI-ready `context.txt` (or `context.md`) in seconds.**

```
Jctx "C:\projects\MyApp"
→  context.txt written  (Java: 39 files | Kotlin: 12 files | POM: 1 file | Gradle: 1 file)
```

No config. No dependencies. Just Python and a folder.

---

## Why it exists

You're working on a Java or Kotlin project. You open an AI chat to get help. Before you can even ask your question, you spend 10 minutes copy-pasting files, explaining your class structure, summarising what each module does.

**Before:**
ChatGPT suggests random classes

**After:**
ChatGPT tells exactly which class to modify and why

**Jctx does all of that in one command.**

It scans your project and writes a clean, structured `context.txt` (or `context.md`) — every class, every field, every method signature, every Javadoc/KDoc comment, and your build files — formatted so an AI can immediately understand your entire codebase. 

It also provides **Token Count Estimation** and **Language Percentages** to help you stay within your AI's context limits.

Paste it. Ask your question. Get useful answers.

---

## Output (real example)

<details>
<summary>Click to expand sample context.md (Markdown Mode)</summary>

````markdown
# JCTX v1.6.1 — Context Report

- **Project:** `C:\projects\Talken`
- **Date:** 2026-03-30 14:22:01
- **Files:** **Java:** 39 file(s) · **Kotlin:** 5 file(s) · **POM:** 1 file(s) · **Gradle:** 1 file(s)

---

## 1. Project File Tree

```
Talken\
├── src\
│   └── main\
│       ├── java\
│       │   └── org\
│       │       └── flexstudios\
│       │           └── talken\
│       │               ├── Controls.java
│       │               └── TalkenClient.java
│       └── kotlin\
│           └── org\
│               └── flexstudios\
│                   └── talken\
│                       └── UserProfile.kt
├── build.gradle
└── pom.xml
```

## 2. POM.XML Content

#### `pom.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<project>
    <modelVersion>4.0.0</modelVersion>
    <groupId>org.flexstudios</groupId>
    <artifactId>talken</artifactId>
    <version>1.0.0</version>
</project>
```

## 3. Kotlin Class & Member Details

#### 📄 `src\main\kotlin\org\flexstudios\talken\UserProfile.kt`

### Class: `UserProfile`
> Represents the user's local profile settings.

**Data Members:**

| Access | Modifiers | Type | Name | Comment |
|--------|-----------|------|------|---------|
| private | val | `String` | `displayName` | |
| private | val | `String` | `email` | |

**Methods:**

1. `String getAboutSection()`
   - *(no documentation)*
````

</details>

---

## Install (Windows)

**Manual Download**
1. Download The Latest **Release** Zip.
2. Unzip it
3. Right-click `Setup.bat` → **Run as administrator**
4. Open a new terminal

```bat
Jctx "C:\path\to\your\java\project"
```

That's it. `context.txt` appears inside your project folder.

> **No admin rights?** Copy `Jctx.py` + `Jctx.bat` anywhere and run `Jctx.bat` directly.

> **Not on Windows?** Run `python Jctx.py "path/to/project"` on any OS with Python 3.8+.

---

## Usage

```
Jctx <project_folder> [--md] [--slim] [--no-tree] [--clipboard] [--print] [--version] [--help]
```

| Flag | Effect |
|---|---|
| *(none)* | Saves `context.txt` into your project folder and prints token estimates |
| `--md` | Outputs a cleanly formatted Markdown file (`context.md`) instead of plain text |
| `--slim` | Slim mode: output only class names and method signatures (omits fields and docs) to save tokens |
| `--no-tree` | Skips the file tree section (shorter output) |
| `--clipboard` | Copies the generated report directly to your clipboard |
| `--print` | Also prints to the console |
| `--version` | Shows the Jctx version |
| `--help` | Shows help |

---

## How to use the output

Paste `context.txt` (or the contents of `context.md`) into any AI chat and ask your question:

> *"Here's my Java/Kotlin project structure: [paste]. I want to refactor the messaging module to use WebSockets — where should I start?"*

Works great with **Claude**, **ChatGPT**, **Gemini**, and any other AI that accepts long text input.
Jctx automatically estimates the **Token Count** to help you determine which models will fit your context.

---

## What it extracts

| What | Detail |
|---|---|
| File tree | Full project structure, build folders excluded |
| Build Files | Full content of your `pom.xml`, `build.gradle`, and `build.gradle.kts` |
| Classes | Java classes/interfaces/enums and Kotlin classes/data classes/objects/interfaces + Javadoc/KDoc |
| Fields | Type, name, access modifier, val/var (Kotlin), inline comments |
| Methods | Numbered list — return type, name, params, Javadoc/KDoc and top-level Kotlin functions |

**Auto-ignored:** `build/`, `target/`, `.idea/`, `.git/`, `node_modules/`, `.gradle/`, `.class`, `.jar`, and all other build artifacts.

---

## Requirements

- Python 3.8 or newer — [python.org](https://python.org)
- Works on Windows, macOS, Linux

---

## Roadmap

- [x] Kotlin support
- [x] Markdown output mode (`context.md`)
- [x] Multi-language project estimations (mixed Java + Kotlin percentages)
- [x] Token count estimate alongside output
- [x] Clipboard support and Slim mode
- [ ] Cross-platform packaging (Homebrew / pip)

---

## License

MIT — free to use, modify, and share.
