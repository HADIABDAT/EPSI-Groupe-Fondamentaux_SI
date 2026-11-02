#!/usr/bin/env bash
# Déploiement sur la VM de préproduction, avec retour arrière automatique.
#
# Usage :
#   ./deploy.sh IMAGE@DIGEST COMMIT_ATTENDU   déploie une image validée
#   ./deploy.sh --rollback                    redéploie la dernière version fonctionnelle
#
# Variables optionnelles :
#   APP_PORT=8080          port publié sur la VM
#   SIMULATE_FAILURE=1     démarre le conteneur avec /health en erreur (étape 13)
set -euo pipefail

CONTAINER=novaservices-tickets
APP_PORT=${APP_PORT:-8080}
STATE_DIR=${STATE_DIR:-$HOME/novaservices}
CURRENT_FILE=$STATE_DIR/current_image      # dernière image déployée avec succès
PREVIOUS_FILE=$STATE_DIR/previous_image    # celle d'avant, pour --rollback
TIMEOUT=60

mkdir -p "$STATE_DIR"

start_container() {
    local image=$1; shift
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    docker run -d --name "$CONTAINER" --restart unless-stopped \
        -p "$APP_PORT:8000" "$@" "$image" >/dev/null
}

# Attend que /health réponde 200 (durée maximale TIMEOUT), puis vérifie le commit sur /version.
check_service() {
    local expected_commit=$1
    local deadline=$((SECONDS + TIMEOUT))
    until curl -fsS "http://localhost:$APP_PORT/health" >/dev/null 2>&1; do
        if (( SECONDS >= deadline )); then
            echo "ÉCHEC : /health ne répond pas après ${TIMEOUT}s" >&2
            return 1
        fi
        sleep 2
    done
    local version
    version=$(curl -fsS "http://localhost:$APP_PORT/version")
    echo "/version : $version"
    if [[ -n $expected_commit && $version != *"\"$expected_commit\""* ]]; then
        echo "ÉCHEC : le commit attendu ($expected_commit) n'est pas celui servi" >&2
        return 1
    fi
}

if [[ ${1:-} == --rollback ]]; then
    [[ -s $PREVIOUS_FILE ]] || { echo "Aucune version précédente connue" >&2; exit 1; }
    image=$(cat "$PREVIOUS_FILE")
    replaced=$(cat "$CURRENT_FILE" 2>/dev/null || true)
    echo "Retour arrière vers $image"
    start_container "$image"
    check_service ""
    # On échange les deux versions : un second --rollback annule le premier.
    echo "$image" > "$CURRENT_FILE"
    echo "$replaced" > "$PREVIOUS_FILE"
    exit 0
fi

image=${1:?Usage: deploy.sh IMAGE@DIGEST COMMIT_ATTENDU}
expected_commit=${2:?Usage: deploy.sh IMAGE@DIGEST COMMIT_ATTENDU}
last_good=$(cat "$CURRENT_FILE" 2>/dev/null || true)

extra_args=()
[[ ${SIMULATE_FAILURE:-0} == 1 ]] && extra_args+=(-e FAIL_HEALTH=1)

echo "Récupération de $image"
docker pull "$image"

echo "Démarrage de la nouvelle version (port $APP_PORT)"
start_container "$image" "${extra_args[@]}"

if check_service "$expected_commit"; then
    if [[ -n $last_good && $last_good != "$image" ]]; then
        echo "$last_good" > "$PREVIOUS_FILE"
    fi
    echo "$image" > "$CURRENT_FILE"
    echo "Déploiement réussi : $image"
    exit 0
fi

echo "----- Journaux du conteneur en échec -----" >&2
docker logs --tail 50 "$CONTAINER" >&2 || true

if [[ -n $last_good ]]; then
    echo "Retour arrière automatique vers $last_good" >&2
    start_container "$last_good"
    check_service "" && echo "Service rétabli sur la version précédente" >&2
else
    echo "Aucune version précédente : pas de retour arrière possible" >&2
fi
# Le job reste en échec pour conserver le diagnostic, même si le rollback a rétabli le service.
exit 1
