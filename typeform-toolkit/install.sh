#!/bin/bash
# Typeform Toolkit Installer
# Run this on any machine to set up the Typeform MCP, converter, and skills.
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
#
# What it does:
#   1. Connects the Typeform MCP to Claude (user scope)
#   2. Installs converter toolkit to ~/typeform-toolkit/
#   3. Installs Claude skills to ~/.claude/skills/
#   4. Sets TYPEFORM_TOKEN in your shell profile (optional)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/typeform-toolkit"
SKILLS_DIR="$HOME/.claude/skills"

echo "╔══════════════════════════════════════╗"
echo "║   Typeform Toolkit Installer         ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Step 1: Typeform Token ──
if [ -z "${TYPEFORM_TOKEN:-}" ]; then
  echo "Enter your Typeform personal access token"
  echo "(starts with tfp_):"
  read -r TYPEFORM_TOKEN
  echo ""
fi

# ── Step 2: Connect MCP ──
echo "[1/4] Connecting Typeform MCP..."
if command -v claude &> /dev/null; then
  claude mcp add typeform https://api.typeform.com/mcp \
    --transport http \
    --scope user \
    --header "Authorization: Bearer ${TYPEFORM_TOKEN}" \
    && echo "  MCP connected." \
    || echo "  MCP connection failed — you may need to run this manually."
else
  echo "  'claude' CLI not found — skipping MCP setup."
  echo "  Run this manually after installing Claude Code:"
  echo "    claude mcp add typeform https://api.typeform.com/mcp \\"
  echo "      --transport http --scope user \\"
  echo "      --header \"Authorization: Bearer \$TYPEFORM_TOKEN\""
fi
echo ""

# ── Step 3: Install converter toolkit ──
echo "[2/4] Installing converter toolkit to ${INSTALL_DIR}..."
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/converter/md_to_typeform.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/converter/config_template.json" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/converter/push_to_typeform.sh" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/push_to_typeform.sh"
echo "  Installed 3 files."
echo ""

# ── Step 4: Install skills ──
echo "[3/4] Installing Claude skills to ${SKILLS_DIR}..."
mkdir -p "$SKILLS_DIR/typeform-survey-builder"
mkdir -p "$SKILLS_DIR/typeform-account-manager"
cp "$SCRIPT_DIR/skills/typeform-survey-builder/SKILL.md" "$SKILLS_DIR/typeform-survey-builder/"
cp "$SCRIPT_DIR/skills/typeform-account-manager/SKILL.md" "$SKILLS_DIR/typeform-account-manager/"
echo "  Installed 2 skills."
echo ""

# ── Step 5: Shell profile (optional) ──
echo "[4/4] Export TYPEFORM_TOKEN to shell profile?"
echo "  This adds: export TYPEFORM_TOKEN=tfp_... to your profile."
read -r -p "  Add to shell profile? [y/N] " response
if [[ "$response" =~ ^[Yy]$ ]]; then
  # Detect shell
  if [ -f "$HOME/.zshrc" ]; then
    PROFILE="$HOME/.zshrc"
  elif [ -f "$HOME/.bashrc" ]; then
    PROFILE="$HOME/.bashrc"
  elif [ -f "$HOME/.bash_profile" ]; then
    PROFILE="$HOME/.bash_profile"
  else
    PROFILE="$HOME/.profile"
  fi

  # Check if already set
  if grep -q "TYPEFORM_TOKEN" "$PROFILE" 2>/dev/null; then
    echo "  TYPEFORM_TOKEN already in $PROFILE — skipping."
  else
    echo "" >> "$PROFILE"
    echo "# Typeform API token (added by typeform-toolkit installer)" >> "$PROFILE"
    echo "export TYPEFORM_TOKEN=\"${TYPEFORM_TOKEN}\"" >> "$PROFILE"
    echo "  Added to $PROFILE"
  fi
fi

echo ""
echo "Done. Quick test:"
echo ""
echo "  # Verify MCP"
echo "  claude mcp list | grep typeform"
echo ""
echo "  # Verify converter"
echo "  cd $INSTALL_DIR"
echo "  python3 md_to_typeform.py --list-workspaces --token \$TYPEFORM_TOKEN"
echo ""
echo "  # Build a survey"
echo "  python3 md_to_typeform.py survey.md --config config_template.json \\"
echo "    --workspace \"Custom Curriculum\" --token \$TYPEFORM_TOKEN \\"
echo "    --output payload.json --push --form-id <FORM_ID>"
