---
description: Check that an FCPXML's baked-in media paths resolve on this machine
argument-hint: [path to an .fcpxml]
allowed-tools: Bash(python3:*), Read, Glob
---

Verify `$ARGUMENTS` with `python3 ${CLAUDE_PLUGIN_ROOT}/tools/make_fcpxml.py --verify`.

An FCPXML references media by absolute `file://` URL, baked in at write time
from the writer's working directory. The XML is valid either way, so this is the
only check that catches it before the editor does.

Report:

- how many references the timeline holds, and how many resolve;
- **every** reference that does not, with the path it expects;
- whether the unresolved paths share a common prefix that is not present on this
  machine — that means the timeline was written somewhere else (a container, CI,
  a VM with the folder mounted elsewhere), and the fix is to rewrite it beside
  the media rather than to move files.

A verifier run in the same place the file was written reports zero missing media
even when every clip will open red elsewhere, so state plainly which machine
this check ran on.
