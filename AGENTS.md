# AGENTS.md — working in ofLibs

Prebuilt static libraries for [ofWorks](https://github.com/dimitre/ofworks). Each library is
built in CI by [Chalet](https://www.chalet-work.space) and uploaded as
`ofLibs_<lib>_<platform>.zip` to a GitHub release. Nothing gets compiled into this repo; it
only holds build recipes.

## Layout

- `<lib>/chalet.yaml` is the recipe: upstream repo and commit (`externalDependencies`), how to
  build it (`targets`, usually `cmakeProject`), and what goes into the zip (`distribution`).
  Some libs also have a helper script (`glm_folders.sh`, `build_rplidar.sh`, `build_syphon.sh`).
- `.github/workflows/<lib>.yml` is a thin caller. It runs on pushes that touch `<lib>/**` or
  the workflow file itself, and calls a shared build workflow:
  - `_build.yml`: full matrix (linux64, macos, vs, rpi-aarch64, emscripten).
  - `_buildnoemscripten.yml`: the same matrix without emscripten.
  - `_buildwin.yml`: Windows only.
- Inputs: `lib`, `version` (one or more release tags separated by spaces, see
  *Releases* below), and optionally `platforms` (a JSON subset), `linux_apt`, `brew` and
  `meson`.
- `.github/workflows/_disabled/`: workflows for libs nobody downloads right now. GitHub
  doesn't run workflows in subfolders, so moving one back up re-enables it.
- `update_libs.py`: bumps each `externalDependencies` commit to the remote default branch tip.
- `clean_libs.py`: deletes local build artifacts. It only reports unless `--yes` is passed.

## Releases

Each lib's workflow uploads `ofLibs_<lib>_<platform>.zip` to the releases named in its
`version` input:

| Release | Who downloads it | Libs |
|---|---|---|
| `v2.0` | ofWorks (`ofworks/libs/libs.sh`) | freetype, glew, glfw, json, pugixml, rtAudio, tess2, uriparser, utfcpp, kissfft, videoInput, assimp, opencv, cairo |
| `braid` | Braid (`braid/libs/libs.sh`) | dawn, box2d, jolt, libremidi, miniaudio, rplidar, syphon |
| both (`"v2.0 braid"`) | both | fmt, glm, mango, zlib-ng, libusb, yaml-cpp |

`v1.0` and `add` are frozen: no workflow uploads to them anymore, but old installs still
download from them, so don't delete them. Braid finds its addon libs from `// libs:` comments
in `braid/addons/*/braid_*.cpp`; if a new tag appears there, that lib needs `braid` in its
`version`.

## Common tasks

**Bump upstream commits**
```sh
uv run update_libs.py --check     # report what is outdated
uv run update_libs.py --dry-run   # preview edits
uv run update_libs.py             # write them
```
Any dependency whose `commit:` line ends in `# pinned` is skipped. Don't remove that marker
just to make a bump go through.

**Rebuild a lib without changing its recipe:** commit a dated comment at the end of its
workflow (e.g. `# bump YYYY-MM-DD: <reason>`). The push triggers CI.

**Build locally:** `cd <lib> && chalet configure --toolchain <toolchain> && chalet bundle`.
This produces `dist/*.zip`. Toolchains: `apple-llvm` (macOS), `llvm` (Linux), `vs-stable`
(Windows).

**Add a lib:** copy the closest existing `<lib>/chalet.yaml` and `<lib>.yml`, pass a
`platforms` subset if the lib doesn't support every platform, and add a badge plus a table row
to `readme.md`.

## Rules

### Runner pins: build on the oldest toolchain consumers use

- **linux64 / rpi-aarch64 stay on `ubuntu-22.04` (glibc 2.35).** A static `.a` carries
  versioned glibc symbol references, so building on a newer runner makes the lib unusable on
  older distros. Don't change this to `ubuntu-latest`.
  - A lib that needs a newer compiler (C++20 features that need Clang ≥ 16) moves only its own
    workflow to `ubuntu-24.04` through `platforms`, and the workflow says why. Examples:
    `dawn.yml`, `blend2d.yml`. That lib then needs glibc 2.39 at runtime.
- **vs stays on `windows-2022` (MSVC 14.4x).** Libraries built with a newer MSVC reference
  `libcpmt.lib` helpers that older consumers lack (unresolved `__std_*` externals).
  `windows-latest` already switched to VS 2026 and broke consumers this way.
- **emscripten stays on `ubuntu-latest`.** Its output is wasm, so the host glibc doesn't matter.
- The default matrix is repeated in `_build.yml`, `_buildnoemscripten.yml` and
  `_buildwin.yml`. Keep all three in sync.

### Upstream regressions

When a new upstream commit breaks the build:
1. Report it upstream.
2. Keep (or restore) the last working commit and add `# pinned`, with a comment saying why
   and linking the upstream issue.
3. Once upstream is fixed, unpin and delete the comment. Don't leave stale pin comments.

Don't patch upstream sources here to work around a regression unless asked.

### Per-lib notes

- **dawn**: macOS libs are arm64-only (Intel Macs won't link). If `third_party/*/src` is empty
  at configure time, a googlesource fetch failed without an error. Rerun the job; don't pin
  because of it.
- **dawnDynamic**: a macOS-only shared-library experiment built from the same commit as
  `dawn`. Disabled (in `_disabled/`).
- **rplidar**: intentionally follows the Braid tip through `# pinned`. Update it by hand.
- **jolt**: x64 builds use baseline SIMD on purpose. Read the note in `jolt/chalet.yaml`
  before changing any arch or SIMD flags.
- **mango**: ofWorks forks are pulled by hand, so they aren't pinned.

## Don'ts

- Don't commit build output (`build/`, `chalet_external/`, `dist/`, `install/`, `Release/`, `clone/`).
  `.gitignore` already covers these.
- Don't run `clean_libs.py --yes` without asking first.
- Don't move runner pins to `-latest` (see above).
- Don't change a lib's `version` tags without asking. They decide which release ofWorks and
  Braid download it from.
