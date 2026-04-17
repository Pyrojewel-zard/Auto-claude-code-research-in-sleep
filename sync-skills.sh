#!/usr/bin/env bash
# sync-skills.sh — Sync ARIS skills from project dir to global ~/.claude/skills/
# Usage: ./sync-skills.sh [--dry-run] [--delete]

set -euo pipefail

SOURCE="/home/DataTransfer/Pyrojewel/vscode/Auto-claude-code-research-in-sleep/skills"
TARGET="$HOME/.claude/skills"

if [ ! -d "$SOURCE" ]; then
    echo "ERROR: Source directory not found: $SOURCE"
    exit 1
fi

DRY_RUN=false
DELETE=false
for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
        --delete)  DELETE=true ;;
    esac
done

synced=0
skipped=0
deleted=0

# Sync skills from source to target
for skill_dir in "$SOURCE"/*/; do
    skill_name=$(basename "$skill_dir")
    target_path="$TARGET/$skill_name"

    if [ -d "$target_path" ]; then
        # Compare and update if different
        if diff -r "$skill_dir" "$target_path" --brief > /dev/null 2>&1; then
            skipped=$((skipped + 1))
        else
            if [ "$DRY_RUN" = true ]; then
                echo "[DRY-RUN] UPDATE: $skill_name"
            else
                rsync -a --delete "$skill_dir" "$target_path/"
                echo "[UPDATED] $skill_name"
            fi
            synced=$((synced + 1))
        fi
    else
        if [ "$DRY_RUN" = true ]; then
            echo "[DRY-RUN] ADD: $skill_name"
        else
            cp -r "$skill_dir" "$target_path"
            echo "[ADDED]   $skill_name"
        fi
        synced=$((synced + 1))
    fi
done

# Optionally delete skills in target that don't exist in source
if [ "$DELETE" = true ]; then
    for skill_dir in "$TARGET"/*/; do
        skill_name=$(basename "$skill_dir")
        source_path="$SOURCE/$skill_name"
        if [ ! -d "$source_path" ]; then
            if [ "$DRY_RUN" = true ]; then
                echo "[DRY-RUN] DELETE: $skill_name"
            else
                rm -rf "$skill_dir"
                echo "[DELETED] $skill_name"
            fi
            deleted=$((deleted + 1))
        fi
    done
fi

echo ""
echo "Summary: synced=$synced skipped=$skipped deleted=$deleted"
if [ "$DRY_RUN" = true ]; then
    echo "(dry run — no changes made)"
fi
