#!/bin/bash
# Installe les hooks Git pour Scapin

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "Installing Git hooks..."

# Pre-commit hook
cat > "$HOOKS_DIR/pre-commit" << 'HOOK'
#!/bin/bash
# Scapin Pre-commit Hook
# Vérifie les points automatisables de la checklist CLAUDE.md

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Scapin Pre-commit Checks..."
echo ""

ERRORS=0

# ============================================
# 1. Ruff - Python Linting (fichiers staged uniquement)
# ============================================
echo -n "  □ Ruff (Python)... "
STAGED_PY=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.py$' || true)
if [ -n "$STAGED_PY" ] && command -v .venv/bin/ruff &> /dev/null; then
    if echo "$STAGED_PY" | xargs .venv/bin/ruff check --quiet 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Erreurs Ruff détectées${NC}"
        echo "    → Exécuter: .venv/bin/ruff check --fix <fichiers>"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${GREEN}✓ (aucun fichier Python staged)${NC}"
fi

# ============================================
# 2. TypeScript - Type Checking
# ============================================
echo -n "  □ TypeScript... "
STAGED_TS=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(ts|svelte)$' || true)
if [ -n "$STAGED_TS" ] && [ -f "web/package.json" ]; then
    cd web
    if npm run check --silent 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Erreurs TypeScript${NC}"
        echo "    → Exécuter: cd web && npm run check"
        ERRORS=$((ERRORS + 1))
    fi
    cd ..
else
    echo -e "${GREEN}✓ (aucun fichier TS/Svelte staged)${NC}"
fi

# ============================================
# 3. console.log dans fichiers staged
# ============================================
echo -n "  □ console.log... "
if [ -n "$STAGED_TS" ]; then
    CONSOLE_LOGS=$(echo "$STAGED_TS" | xargs grep -l 'console\.log' 2>/dev/null || true)
    if [ -n "$CONSOLE_LOGS" ]; then
        echo -e "${RED}✗ console.log trouvé dans:${NC}"
        echo "$CONSOLE_LOGS" | while read -r file; do
            echo "    - $file"
        done
        ERRORS=$((ERRORS + 1))
    else
        echo -e "${GREEN}✓${NC}"
    fi
else
    echo -e "${GREEN}✓ (aucun fichier TS/Svelte)${NC}"
fi

# ============================================
# 4. TODO dans fichiers staged
# ============================================
echo -n "  □ TODO/FIXME... "
STAGED_CODE=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|ts|svelte)$' || true)
if [ -n "$STAGED_CODE" ]; then
    TODOS=$(echo "$STAGED_CODE" | xargs grep -l -E '(TODO|FIXME):' 2>/dev/null || true)
    if [ -n "$TODOS" ]; then
        echo -e "${YELLOW}⚠ TODO/FIXME trouvé (warning)${NC}"
    else
        echo -e "${GREEN}✓${NC}"
    fi
else
    echo -e "${GREEN}✓${NC}"
fi

# ============================================
# 5. Rappels non-automatisables
# ============================================
echo ""
echo -e "${YELLOW}📋 Rappels (vérification manuelle):${NC}"
echo "  □ Documentation mise à jour?"
echo "  □ Tests écrits et passants?"
echo "  □ Test manuel effectué?"
echo ""

# ============================================
# Résultat final
# ============================================
if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ $ERRORS erreur(s) bloquante(s)${NC}"
    echo ""
    echo "Pour forcer: git commit --no-verify"
    exit 1
else
    echo -e "${GREEN}✅ Checks OK${NC}"
    exit 0
fi
HOOK

chmod +x "$HOOKS_DIR/pre-commit"

echo "✅ Pre-commit hook installed"
echo ""
echo "Hook vérifie:"
echo "  - Ruff (Python linting)"
echo "  - TypeScript (type checking)"
echo "  - console.log dans fichiers staged"
echo "  - TODO/FIXME (warning)"
