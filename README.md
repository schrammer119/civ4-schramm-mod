# Civ4 Schramm Mod

This is a project attempting to recompile and modernize the Civilization 4: Beyond the Sword game library (CvGameCoreDLL.dll).

## Requirements

- git
- pixi
- Visual Studio .NET 2003 (for original toolchain)
- VSCode (optional, development is geared towards this IDE)

## Setup

1. Clone the repository:

```bash
git clone https://github.com/schrammer119/civ4-schramm-mod.git civ4-schramm-mod
cd civ4-schramm-mod
```

2. Install dependencies:

```bash
pixi install --frozen --all
```

3. Copy in toolchain:

See the toolchaine readme here: [toolchain README](toolchain/README.md)

4. Build the project:

```bash
pixi run build-vc7
```

## Development

### Branch names

Branch names should follow the convention:

```
<type>/<short-description>
```

Where `<type>` can be one of:
- `feat` for additions to the source code (`src/`)
- `fix` for bug fixes in the source code (`src/`)
- `tool` edits related to the build toolchain or development environment (including documentation)

And `<short-description>` is a brief, hyphen-separated description of the branch's purpose.

### Commit messages

Commit messages should follow the conventional commits format:

```
<type>: <short-title>

**Reasoning:**
<explanation of why this change is necessary or beneficial>

**Additions and Changes:**
<list of additions and changes made in this commit>

**Tests and Regression Protection:**
<tests or checks added to ensure future changes will not break this change>

**Verification:**
<tests, checks, or steps taken to verify this change>
```

Where `<type>` is one of the branch types (`feat`, `fix`, `tool`), and `<short-title>` is a brief summary of the change.
