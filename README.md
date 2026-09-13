# Bootstrap Shorts Project

CLI that starts a new After Effects short-form project from two templates:

- `portrait-short-form`
- `portrait-short-form-pre-process`

Python (managed with [uv](https://docs.astral.sh/uv/)) prepares the project folder and copies footage. ExtendScript then drives After Effects: save both projects, import clips into the expected Project panel folders, and relink any existing template footage into `(Footage)/`.

Native **File → Dependencies → Collect Files** is not scriptable. This tool copies and relinks footage directly into the new project root instead of creating a temporary `<name>-deps` folder.

The CLI is styled with [Rich](https://github.com/Textualize/rich): a folder table for footage selection, a progress bar while copying clips, and a spinner while waiting for After Effects. It is still a command-line app, not a GUI.

**NOTE:** This bootstrapping CLI is very specific to my own content pipeline. It solves a repetitive issue for how I start short-form content projects and how I manage my footage.

## Resulting layout

```text
<projects>/<name>/
  <name>.aep
  <name>-pre-process.aep
  (Footage)/
    01-footage/
      clip-a.mov
      clip-b.mov
  .bootstrap/
    job.json
    result.json
```

## Requirements

Shared (source or compiled exe):

- Windows 10
- Adobe After Effects with both template `.aep` files
- In After Effects: **Preferences → Scripting & Expressions → Allow Scripts to Write Files and Access Network**

To run from source, also install:

- [uv](https://docs.astral.sh/uv/)
- Python 3.11+ (uv will install it if needed)

The compiled exe does **not** need uv or Python. After Effects stays a separate install; it is not inside the executable.

## Install

### Compiled executable

Download `bsp-<version>-windows.exe` from the repository [Releases](https://github.com/wemakeart-dev/bootstrap-shorts-project/releases) page, rename it to `bsp.exe` if you like, and put it in its own folder. Copy [config.example.yaml](config.example.yaml) to `config.yaml` in that same folder and fill in local paths. For `--match-tally`, also copy [example-timestamps.txt](example-timestamps.txt) to `timestamps.txt` next to the exe.

Those two files are the only extras that belong next to the executable:

```text
bsp.exe
config.yaml
timestamps.txt
```

Releases are published when a pull request is merged into `master`. The version and tag come from `[project].version` in [pyproject.toml](pyproject.toml) (`0.1.0` → `v0.1.0`). Bump that field to open a new release; merging again at the same version updates the existing release asset.

### From source

From the repository root:

```powershell
uv sync --group dev
```

This creates `.venv`, installs runtime and test dependencies, and writes `uv.lock` as needed. Add `--group build` if you also want PyInstaller for a local exe build.

## Config

Copy [config.example.yaml](config.example.yaml) to `config.yaml` (gitignored) and fill in local paths. When you run the compiled exe, place `config.yaml` next to it. When you run from source, the default is `config.yaml` in the current directory:

```yaml
templates:
  main: "E:/path/to/portrait-short-form"
  pre_process: "E:/path/to/portrait-short-form-pre-process"
raw_footage: "E:/path/to/raw-footage"
projects: "E:/path/to/projects"

after_effects_exe: null

templates_map:
  main: "portrait-short-form.aep"
  pre_process: "portrait-short-form-pre-process.aep"

project_folders:
  main_import: "01-footage"
  preprocess_import: "footage"
```

| Key | Required | Meaning |
|---|---|---|
| `templates.main` | yes | Directory or `.aep` file for `portrait-short-form` |
| `templates.pre_process` | yes | Directory or `.aep` file for `portrait-short-form-pre-process` |
| `raw_footage` | yes | Root folder for source clips. Interactive browse cannot leave this directory. Only `.mov` files in the current folder can be selected (not recursive) |
| `projects` | yes | Parent directory where the new project folder is created |
| `after_effects_exe` | no | Full path to `AfterFX.exe`. If `null`, the newest install under Program Files is used |
| `templates_map` | no | `.aep` filenames used when a `templates.*` path is a directory |
| `project_folders` | no | After Effects Project panel folder names for imports |

Relative paths are resolved against the config file's directory.

### Template folder contract

The templates must already contain (or will get) these Project panel folders:

- `01-footage` in `portrait-short-form` — raw clips are imported here
- `footage` in `portrait-short-form-pre-process` — the same clips are imported here

On disk, raw clips always land in `(Footage)/<main_import>/`, which defaults to `(Footage)/01-footage/`.

To use different template folders or panel names later, change `templates`, `templates_map`, and `project_folders`. No code change is required. Each `templates.*` value may be a directory (joined with `templates_map`) or a direct path to an `.aep` file.

## Run

From a compiled exe (run it from the folder that contains `config.yaml`):

```powershell
.\bsp.exe
.\bsp.exe --config config.yaml
.\bsp.exe --name other-short --raw-footage E:\clips
.\bsp.exe --force
.\bsp.exe --yes
.\bsp.exe --match-tally
```

From source:

```powershell
uv run bootstrap-shorts
uv run bootstrap-shorts --config config.yaml
uv run bootstrap-shorts --name other-short --raw-footage E:\clips
uv run bootstrap-shorts --force
uv run bootstrap-shorts --yes
uv run bootstrap-shorts --match-tally
```

The CLI lists child folders and `.mov` files in the current directory (directories first). Enter a folder number to drill in, `..` to go up (blocked at the footage root), then select files from that folder:

```text
Footage root: E:\clips
Current:      E:\clips\session-01

  #  Name              Size
  1  [dir] takes-a
  2  clip-a.mov        1.2 GB
  3  clip-b.mov        800.0 MB

Enter file numbers (1,3), ranges (1-3), a folder number to open, all, .. to go up, or q to cancel.
Select files or open a folder [all]: 2,3
Process these files? [Y/n]: y
Project name: Client Short 01
Using project name: client-short-01
```

Accepted values: a folder number to open, `..` to go up, `all`, `1,3`, `1-3`, or `q` to cancel. You can only select `.mov` files from the directory you have navigated to (not mixed with folders, and not from multiple folders). `--yes` skips browsing and processes every `.mov` file in the footage **root** directory (not recursive). It does **not** skip the project name prompt.

After footage is confirmed, the CLI asks for the new project name. The value is lowercased and spaces become hyphens (`Client Short 01` → `client-short-01`). Only ASCII letters, digits, spaces, and hyphens are allowed. Pass `--name` to skip that prompt (same rules). A `name` key in `config.yaml` is rejected as deprecated.

CLI flags override the config file:

| Flag | Purpose |
|---|---|
| `--config` / `-c` | YAML config path. Defaults to `config.yaml` next to the exe, or in the current directory when running from source |
| `--name` | Project name; skips the name prompt. Lowercased; spaces become hyphens |
| `--raw-footage` | Override the `raw_footage` root directory |
| `--force` | Delete and replace an existing `projects/<name>` folder |
| `--yes` / `-y` | Process every `.mov` file in the footage root directory without prompting (still asks for the project name unless `--name` is set) |
| `--timeout` | Seconds to wait for After Effects (default `600`) |
| `--match-tally` | Apply `timestamps.txt` to the currently open After Effects project instead of bootstrapping a new one |

## What happens

1. Validate the config. Fail if templates, the raw footage root directory, or the projects parent directory are missing. The root may contain only child folders; clips are not required at the top level. Fail if the config still has a `name` key.
2. Browse the footage root (or, with `--yes`, take every `.mov` file in the root). `.mp4` and other types are ignored. Fail if you confirm a folder that has no `.mov` files, or if `--yes` finds none in the root.
3. List folders and clips in the current directory, let you navigate or select files, and confirm that set (unless `--yes`).
4. Prompt for the project name (or use `--name`). Normalize to a lowercase hyphenated slug.
5. Refuse to continue if `projects/<name>` already exists, unless `--force`.
6. Create `projects/<name>/(Footage)/01-footage/` and copy the selected `.mov` files there (progress bar).
7. Write `.bootstrap/job.json` with absolute paths.
8. Launch `AfterFX.exe -s` once (spinner while waiting). The script:
   - opens the main template and saves it as `<name>.aep`
   - imports the copied files into `01-footage`
   - copies any other template `FileSource` footage into `(Footage)/<panel-folder>/` and relinks it
   - opens the pre-process template and saves it as `<name>-pre-process.aep`
   - imports the same files into `footage`
9. Python reads `.bootstrap/result.json` and exits non-zero if After Effects reported errors.

After Effects is left running. The launcher does not pass `-project` together with the script (that combination is unreliable).

## Match tally

`--match-tally` is a separate mode. It does **not** copy footage or create a new project. After Effects must already be open with a `portrait-short-form`-based project that contains `05-text-assets` / `match-tally` (and the nested `air-tally`, `ground-tally`, and `naval-tally` comps).

Place a `timestamps.txt` file next to the executable, or in the directory you run the CLI from when working from source (the repo root). Copy [example-timestamps.txt](example-timestamps.txt) and edit it. `timestamps.txt` is gitignored, like `config.yaml`.

```text
0:00:02:32
0:01:06:11 - Naval
0:01:20:37 - Ground
0:01:29:51 - Air
```

Each line is After Effects timecode (`H:MM:SS:FF`). An optional identifier after ` - ` selects the nested tally composition:

- no identifier → `ground-tally`
- `Air` / `Ground` / `Naval` (case-insensitive) → the matching composition

Blank lines are ignored. Unknown identifiers or malformed timecode fail in Python before After Effects is launched.

The script keyframes **Effects → Slider Control** on the source text layer in each tally composition: value `0` at `0:00:00:00`, then `1`, `2`, … at each timestamp for that type. The existing source-text expression `Math.trunc(effect("Slider Control")("Slider"));` is left untouched. Re-running `--match-tally` replaces previous slider keys.

`config.yaml` is still required so AfterFX can be resolved. Footage browsing and the project-name prompt are skipped.

## Failures

| Situation | Result |
|---|---|
| Missing `config.yaml` or invalid YAML | CLI error |
| Unknown config key | CLI error (`extra: forbid`) |
| Deprecated `name` key in config | CLI error; prompt for the name or pass `--name` |
| Missing template `.aep` | CLI error |
| Missing raw footage directory | CLI error |
| No `.mov` files in the current folder (or in the root with `--yes`) | CLI error |
| Footage selection cancelled | CLI error |
| Invalid project name | CLI error (`--name`) or re-prompt |
| Duplicate footage filenames | CLI error |
| `projects/<name>` already exists | CLI error; pass `--force` to replace |
| `AfterFX.exe` not found | CLI error; set `after_effects_exe` |
| After Effects never writes `result.json` | Timeout; enable script file access in Preferences |
| Import or save error inside AE | `result.json` `ok: false` and a CLI error |
| Missing `timestamps.txt` with `--match-tally` | CLI error; After Effects is not launched |
| Invalid line in `timestamps.txt` | CLI error (unknown identifier or bad timecode) |
| No AE project open, or tally comps missing | `result.json` `ok: false` and a CLI error |

Navigation cannot leave the `raw_footage` root. `..` at the root is refused; the browse loop continues.

## Known limits

- Fonts are not collected. Install required fonts on the machine.
- Layered Photoshop / Illustrator sources may not relink per layer. Those items are skipped with a warning.
- Cinema 4D and some plugin-owned files are not collected.
- Image sequences are imported as single files unless you add sequence handling later.
- After Effects is not bundled inside the exe.
- One-file PyInstaller builds may be flagged by SmartScreen or antivirus until you allow the file.

## Development

```powershell
uv sync --group dev
uv run pytest
uv run ruff check src tests
```

Unit tests cover config validation, footage browsing / copy / `job.json` shape, timestamp parsing, `--match-tally` CLI wiring, AfterFX discovery, frozen path resolution, and packaging invariants. They do not launch After Effects.

### Build a Windows exe locally

```powershell
uv sync --group dev --group build
uv run pyinstaller --noconfirm bootstrap-shorts.spec
```

The onefile console build is written to `dist/bsp.exe` and uses [bootstrap-shorts-project-icon.ico](bootstrap-shorts-project-icon.ico). Copy `config.yaml` (and `timestamps.txt` if you use `--match-tally`) next to that exe before running it.

### Continuous integration

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs pytest and ruff on every pull request and every push to `master`. The Windows onefile build and GitHub Release run only on pushes to `master` (including merged pull requests). Pull requests do not compile or publish.

The release tag and asset name use `[project].version` from [pyproject.toml](pyproject.toml), for example `v0.1.0` and `bsp-0.1.0-windows.exe`.

## Project layout

```text
src/bootstrap_shorts/    Python CLI, config, filesystem, AE launcher
scripts/ae/              ExtendScript helpers, bootstrap runner, match-tally runner
bootstrap-shorts.spec    PyInstaller onefile spec
bootstrap-shorts-project-icon.ico  Embedded Windows exe icon
.github/workflows/       Test CI and master-only Windows release
config.example.yaml      Documented config template
example-timestamps.txt   Sample timestamps.txt for --match-tally
tests/                   Unit tests (no live After Effects)
```
