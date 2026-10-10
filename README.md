# PSP Buddy

PSP Buddy is a planned autonomous play assistant for **Super Robot Wars Z2 Rebirth (English v0.8)** running in **PPSSPP** on Windows. It aims to follow the user's natural-language tactical instructions and hand control back when help is needed.

## Planned capabilities

- Load and save progress using PPSSPP's existing save-state features, with support for starting from normal in-game saves.
- Read the current game state, including robot specifications, pilot statistics, map information, and battle status.
- Make tactical decisions, perform battle actions, skip dialogue, and progress to subsequent maps according to user instructions.
- Pause and request user assistance when an allied robot is defeated or another configured stop condition occurs.

## Current status

The project is in design and integration research. No autonomous runner has been implemented. Portable PPSSPP v1.20.4 has loaded the tested save state and normal in-game saves, and a direct API button press moved the cursor. Full game-state reading, reliable screen capture, and checkpoint automation still need validation.

The initial milestone is one autonomous battle from an existing save, with one working checkpoint slot, up to three retries, and automatic handover. See the [MVP design specification](docs/superpowers/specs/2026-10-10-autonomous-battle-mvp-design.md) and [integration research](docs/research/2026-10-10-hybrid-feasibility.md).

## Save protection

Before every emulator or game trial, back up both complete PPSSPP directories: `PSP/SAVEDATA` and `PSP/PPSSPP_STATE`. Verify all copied files using SHA-256 before proceeding. Preserve earlier backups and do not test while saves are being written.

Backups, game images, and emulator save data are excluded from Git. Supply your own game and saves; they are not distributed with this project.

## Development workflow

Use the global development workflow and this repository's `AGENTS.md`: check Git status, approve the design, write a spec and implementation plan, implement with tests, verify behavior, and review changes. Leave all changes uncommitted until the user explicitly requests a commit.
