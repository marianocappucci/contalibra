#!/bin/bash
# Uso: ./scripts/deploy-prod.sh [nueva_version]
# Ejemplo: ./scripts/deploy-prod.sh 1.3.0
#          ./scripts/deploy-prod.sh          <- usa la version actual en version.py
set -euo pipefail

cd "$(dirname "$0")/.."

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}→${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC}  $*"; }
error() { echo -e "${RED}✗${NC}  $*"; exit 1; }

# 0. Verificar rama
BRANCH=$(git rev-parse --abbrev-ref HEAD)
[ "$BRANCH" = "develop" ] || error "Ejecutar desde la rama 'develop' (actualmente en '$BRANCH')"

# 1. Verificar estado limpio (ignorar archivos WAL de SQLite)
DIRTY=$(git status --porcelain | grep -v '\.db-shm\|\.db-wal' || true)
[ -z "$DIRTY" ] || error "Hay cambios sin commitear. Hacé commit o stash antes de deployar."

# 2. Bump de versión (opcional)
NEW_VERSION="${1:-}"
if [ -n "$NEW_VERSION" ]; then
    info "Actualizando versión a v$NEW_VERSION..."
    sed -i "s/^VERSION = .*/VERSION = \"$NEW_VERSION\"/" version.py
    git add version.py
    git commit -m "Bump version to v$NEW_VERSION"
fi

# 3. Leer versión actual
VERSION=$(python3 -c "import sys; sys.path.insert(0,'.');from version import VERSION;print(VERSION)")
info "Deployando v$VERSION a producción (puerto 8070)..."

# 4. Merge develop → main + tag
git checkout main
git merge develop --no-ff -m "Release v$VERSION"
git tag -a "v$VERSION" -m "Release v$VERSION" 2>/dev/null || {
    warn "Tag v$VERSION ya existe, sobreescribiendo..."
    git tag -f -a "v$VERSION" -m "Release v$VERSION"
}

# 5. Build y arranque del contenedor de producción
info "Construyendo imagen de producción..."
docker compose -f docker-compose.prod.yml up -d --build

# 6. Volver a develop y pushear todo
git checkout develop
info "Pusheando a origin..."
git push origin develop main
git push origin "v$VERSION" --force

echo ""
echo -e "${GREEN}✓ v$VERSION deployado exitosamente en puerto 8070${NC}"
echo ""
