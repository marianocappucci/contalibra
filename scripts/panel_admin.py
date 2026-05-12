#!/usr/bin/env python3
"""
Panel de administración Contalibra.
Gestiona todos los contenedores de clientes desde un menú interactivo.
Uso: python3 scripts/panel_admin.py [comando] [slug]
     python3 scripts/panel_admin.py           → menú interactivo
     python3 scripts/panel_admin.py listar
     python3 scripts/panel_admin.py backup micomercio
"""
import os
import sys
import json
import subprocess
import tarfile
import shutil
from datetime import datetime
from pathlib import Path

REPO_ROOT    = Path(__file__).parent.parent.resolve()
CLIENTES_DIR = REPO_ROOT / "clientes"
IMAGE_NAME   = "contalibra:latest"


# ── helpers Docker ────────────────────────────────────────────────────────────

def docker(*args, capture=False, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args],
                          capture_output=capture, text=True, cwd=cwd)


def compose(slug: str, *args) -> subprocess.CompletedProcess:
    compose_file = CLIENTES_DIR / slug / "docker-compose.yml"
    return subprocess.run(
        ["docker", "compose", "-f", str(compose_file), *args],
        cwd=str(CLIENTES_DIR / slug),
    )


def container_status(container: str) -> dict:
    r = docker("inspect", container,
               "--format", "{{.State.Status}}|{{.State.StartedAt}}",
               capture=True)
    if r.returncode != 0:
        return {"status": "no encontrado", "started": ""}
    parts = r.stdout.strip().split("|")
    status  = parts[0] if parts else "?"
    started = parts[1][:19].replace("T", " ") if len(parts) > 1 else ""
    return {"status": status, "started": started}


# ── lectura de clientes ───────────────────────────────────────────────────────

def load_clients() -> list[dict]:
    clients = []
    if not CLIENTES_DIR.exists():
        return clients
    for d in sorted(CLIENTES_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta_file = d / "cliente.json"
        if not meta_file.exists():
            continue
        meta = json.loads(meta_file.read_text())
        meta["slug"]      = d.name
        meta["container"] = meta.get("container", f"contalibra-{d.name}")
        meta["dir"]       = d
        clients.append(meta)
    return clients


def find_client(slug: str) -> dict | None:
    for c in load_clients():
        if c["slug"] == slug:
            return c
    return None


# ── display ───────────────────────────────────────────────────────────────────

STATUS_COLOR = {
    "running":      "\033[32m●\033[0m",   # verde
    "exited":       "\033[31m●\033[0m",   # rojo
    "paused":       "\033[33m●\033[0m",   # amarillo
    "no encontrado":"\033[90m○\033[0m",   # gris
}

def _col(status: str) -> str:
    return STATUS_COLOR.get(status, "○")


def cmd_listar():
    clients = load_clients()
    if not clients:
        print("No hay clientes. Creá uno con: python3 scripts/nuevo_cliente.py")
        return
    fmt = "{:<3}  {}  {:<18}  {:>5}  {:<12}  {}"
    print(fmt.format("#", " ", "SLUG", "PORT", "ESTADO", "NOMBRE"))
    print("-" * 68)
    for i, c in enumerate(clients, 1):
        info   = container_status(c["container"])
        status = info["status"]
        print(fmt.format(
            i,
            _col(status),
            c["slug"][:18],
            c.get("port", "—"),
            status[:12],
            c.get("nombre", "")[:30],
        ))
    print()


def cmd_info(slug: str):
    c = find_client(slug)
    if not c:
        print(f"[ERROR] Cliente '{slug}' no encontrado.")
        return
    info = container_status(c["container"])
    print(f"\n  Nombre:      {c.get('nombre','')}")
    print(f"  Slug:        {c['slug']}")
    print(f"  Contenedor:  {c['container']}  [{info['status']}]")
    print(f"  Puerto:      {c.get('port','')}")
    print(f"  Dominio:     {c.get('domain','—') or '—'}")
    print(f"  Admin:       {c.get('admin_user','')}  /  {c.get('admin_password','')}")
    print(f"  Iniciado:    {info['started'] or '—'}")
    print(f"  Datos:       {c['dir'] / 'data'}\n")


def cmd_start(slug: str):
    c = find_client(slug)
    if not c:
        print(f"[ERROR] Cliente '{slug}' no encontrado.")
        return
    print(f"[*] Iniciando {c['container']} ...")
    compose(slug, "up", "-d")


def cmd_stop(slug: str):
    c = find_client(slug)
    if not c:
        print(f"[ERROR] Cliente '{slug}' no encontrado.")
        return
    print(f"[*] Deteniendo {c['container']} ...")
    compose(slug, "stop")


def cmd_restart(slug: str):
    c = find_client(slug)
    if not c:
        print(f"[ERROR] Cliente '{slug}' no encontrado.")
        return
    print(f"[*] Reiniciando {c['container']} ...")
    compose(slug, "restart")


def cmd_logs(slug: str, lines: int = 50):
    c = find_client(slug)
    if not c:
        print(f"[ERROR] Cliente '{slug}' no encontrado.")
        return
    print(f"[*] Últimas {lines} líneas de {c['container']} (Ctrl+C para salir):\n")
    try:
        subprocess.run(["docker", "logs", "--tail", str(lines), "-f", c["container"]])
    except KeyboardInterrupt:
        pass


def cmd_backup(slug: str):
    c = find_client(slug)
    if not c:
        print(f"[ERROR] Cliente '{slug}' no encontrado.")
        return
    data_dir = c["dir"] / "data"
    if not data_dir.exists():
        print(f"[ERROR] No existe {data_dir}")
        return
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = CLIENTES_DIR / f"{slug}_backup_{ts}.tar.gz"
    print(f"[*] Creando backup de {slug} ...")
    with tarfile.open(out_file, "w:gz") as tar:
        tar.add(data_dir, arcname=f"{slug}/data")
    size_mb = out_file.stat().st_size / 1_048_576
    print(f"[OK] Backup guardado: {out_file}  ({size_mb:.1f} MB)")


def cmd_actualizar(slugs: list[str] | None = None):
    """Reconstruye la imagen y reinicia los contenedores indicados (o todos)."""
    print(f"[*] Reconstruyendo imagen {IMAGE_NAME} ...")
    r = subprocess.run(["docker", "build", "-t", IMAGE_NAME, "."], cwd=str(REPO_ROOT))
    if r.returncode != 0:
        print("[ERROR] Falló el build.")
        return

    clients = load_clients()
    targets = [c for c in clients if (not slugs or c["slug"] in slugs)]
    if not targets:
        print("[INFO] Sin contenedores que actualizar.")
        return

    for c in targets:
        info = container_status(c["container"])
        if info["status"] == "running":
            print(f"[*] Actualizando {c['container']} ...")
            compose(c["slug"], "up", "-d")
        else:
            print(f"[SKIP] {c['container']} no está en ejecución.")
    print("[OK] Actualización completa.")


def cmd_eliminar(slug: str):
    c = find_client(slug)
    if not c:
        print(f"[ERROR] Cliente '{slug}' no encontrado.")
        return
    confirm = input(f"¿Eliminar PERMANENTEMENTE al cliente '{slug}' y todos sus datos? [escribí el slug para confirmar]: ").strip()
    if confirm != slug:
        print("Cancelado.")
        return
    print(f"[*] Deteniendo y eliminando {c['container']} ...")
    compose(slug, "down", "-v")
    shutil.rmtree(c["dir"])
    print(f"[OK] Cliente '{slug}' eliminado.")


# ── menú interactivo ──────────────────────────────────────────────────────────

def pick_client(prompt: str) -> str | None:
    clients = load_clients()
    if not clients:
        print("No hay clientes registrados.")
        return None
    cmd_listar()
    val = input(f"{prompt} (número o slug): ").strip()
    if not val:
        return None
    if val.isdigit():
        idx = int(val) - 1
        if 0 <= idx < len(clients):
            return clients[idx]["slug"]
        print("[ERROR] Número fuera de rango.")
        return None
    if any(c["slug"] == val for c in clients):
        return val
    print(f"[ERROR] Slug '{val}' no encontrado.")
    return None


MENU = """
╔══════════════════════════════╗
║  CONTALIBRA — Panel Admin    ║
╠══════════════════════════════╣
║  1  Listar clientes          ║
║  2  Info de un cliente       ║
║  3  Iniciar contenedor       ║
║  4  Detener contenedor       ║
║  5  Reiniciar contenedor     ║
║  6  Ver logs                 ║
║  7  Backup de datos          ║
║  8  Actualizar imagen        ║
║  9  Eliminar cliente         ║
║  0  Salir                    ║
╚══════════════════════════════╝"""


def interactive():
    while True:
        print(MENU)
        opt = input("Opción: ").strip()
        print()

        if opt == "0":
            break
        elif opt == "1":
            cmd_listar()
        elif opt == "2":
            slug = pick_client("Cliente")
            if slug:
                cmd_info(slug)
        elif opt == "3":
            slug = pick_client("Iniciar cliente")
            if slug:
                cmd_start(slug)
        elif opt == "4":
            slug = pick_client("Detener cliente")
            if slug:
                cmd_stop(slug)
        elif opt == "5":
            slug = pick_client("Reiniciar cliente")
            if slug:
                cmd_restart(slug)
        elif opt == "6":
            slug = pick_client("Ver logs de")
            if slug:
                lines = input("Últimas N líneas [50]: ").strip()
                cmd_logs(slug, int(lines) if lines.isdigit() else 50)
        elif opt == "7":
            slug = pick_client("Backup de")
            if slug:
                cmd_backup(slug)
        elif opt == "8":
            slugs_input = input("Slugs a actualizar (Enter = todos): ").strip()
            slugs = slugs_input.split() if slugs_input else None
            cmd_actualizar(slugs)
        elif opt == "9":
            slug = pick_client("Eliminar cliente")
            if slug:
                cmd_eliminar(slug)
        else:
            print("Opción no válida.")

        input("\n[Enter para continuar]")


# ── CLI directo ───────────────────────────────────────────────────────────────

def cli():
    args = sys.argv[1:]
    if not args:
        interactive()
        return

    cmd  = args[0]
    slug = args[1] if len(args) > 1 else None

    dispatch = {
        "listar":     lambda: cmd_listar(),
        "info":       lambda: cmd_info(slug) if slug else print("Uso: panel_admin.py info <slug>"),
        "start":      lambda: cmd_start(slug) if slug else print("Uso: panel_admin.py start <slug>"),
        "stop":       lambda: cmd_stop(slug) if slug else print("Uso: panel_admin.py stop <slug>"),
        "restart":    lambda: cmd_restart(slug) if slug else print("Uso: panel_admin.py restart <slug>"),
        "logs":       lambda: cmd_logs(slug) if slug else print("Uso: panel_admin.py logs <slug>"),
        "backup":     lambda: cmd_backup(slug) if slug else print("Uso: panel_admin.py backup <slug>"),
        "actualizar": lambda: cmd_actualizar([slug] if slug else None),
        "eliminar":   lambda: cmd_eliminar(slug) if slug else print("Uso: panel_admin.py eliminar <slug>"),
    }

    fn = dispatch.get(cmd)
    if fn:
        fn()
    else:
        print(f"Comando desconocido: {cmd}")
        print("Comandos: listar | info | start | stop | restart | logs | backup | actualizar | eliminar")
        sys.exit(1)


if __name__ == "__main__":
    cli()
