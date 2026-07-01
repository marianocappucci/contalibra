#!/usr/bin/env python3
"""
Onboarding de nuevo cliente Contalibra.
Uso: python3 scripts/nuevo_cliente.py

Crea el directorio del cliente, genera docker-compose.yml y levanta el contenedor.
"""
import os
import sys
import re
import secrets
import subprocess
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
try:
    from npm_api import client_from_config, forward_host_from_config, le_email_from_config, NPMError
    _NPM_AVAILABLE = True
except Exception:
    _NPM_AVAILABLE = False

REPO_ROOT    = Path(__file__).parent.parent.resolve()
CLIENTES_DIR = REPO_ROOT / "clientes"
IMAGE_NAME   = "contalibra:latest"
BASE_PORT    = 8071


def slugify(name: str) -> str:
    s = name.lower().strip()
    for src, dst in [("áàäâ","a"),("éèëê","e"),("íìïî","i"),("óòöô","o"),("úùüû","u"),("ñ","n")]:
        for c in src:
            s = s.replace(c, dst)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "cliente"


def used_ports() -> set:
    try:
        out = subprocess.run(["docker","ps","-a","--format","{{.Ports}}"],
                             capture_output=True, text=True).stdout
        return {int(m.group(1)) for m in re.finditer(r":(\d+)->8000", out)}
    except Exception:
        return set()


def next_port(used: set) -> int:
    p = BASE_PORT
    while p in used:
        p += 1
    return p


def ask(msg: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{msg}{suffix}: ").strip()
    return val if val else default


def build_image():
    print(f"\n[*] Construyendo imagen {IMAGE_NAME} ...")
    r = subprocess.run(["docker","build","-t",IMAGE_NAME,"."], cwd=str(REPO_ROOT))
    if r.returncode != 0:
        sys.exit("[ERROR] Falló el build de la imagen.")
    print(f"[OK] Imagen lista.")


def image_exists() -> bool:
    return subprocess.run(["docker","image","inspect",IMAGE_NAME],
                          capture_output=True).returncode == 0


def network_exists(name: str) -> bool:
    return subprocess.run(["docker","network","inspect",name],
                          capture_output=True).returncode == 0


def _setup_npm_proxy(npm, domain: str, port: int):
    fwd_host = forward_host_from_config()
    le_email = le_email_from_config()
    print(f"\n[*] Creando proxy en NPM: {domain} → {fwd_host}:{port} (SSL Let's Encrypt) ...")
    try:
        existing = npm.get_proxy_host_by_domain(domain)
        if existing:
            print(f"[WARN] Ya existe un proxy para {domain} (id={existing['id']}). Omitiendo.")
            return
        host = npm.create_proxy_host(
            domain=domain,
            forward_host=fwd_host,
            forward_port=port,
            ssl=True,
            le_email=le_email,
        )
        print(f"[OK]  Proxy creado en NPM (id={host['id']}) con certificado SSL.")
    except NPMError as e:
        print(f"[ERROR] NPM: {e}")
        print(f"[!]    Configurá el proxy manualmente: {domain} → {fwd_host}:{port}")


def main():
    print("=" * 60)
    print("  CONTALIBRA — Alta de nuevo cliente")
    print("=" * 60)

    # — datos del cliente —
    nombre = ask("Nombre del comercio / empresa")
    if not nombre:
        sys.exit("[ERROR] El nombre es obligatorio.")

    slug = slugify(ask("Identificador (slug)", slugify(nombre)))

    client_dir = CLIENTES_DIR / slug
    if client_dir.exists():
        sys.exit(f"[ERROR] Ya existe '{slug}' en {client_dir}")

    domain = ask("Dominio (ej: mitienda.com, Enter para omitir)", "")

    _used   = used_ports()
    port    = int(ask("Puerto HTTP", str(next_port(_used))))
    if port in _used:
        print(f"[WARN] El puerto {port} ya está en uso.")

    admin_user     = ask("Usuario admin", "admin")
    admin_password = ask("Contraseña admin (Enter = generar)", "")
    if not admin_password:
        admin_password = secrets.token_urlsafe(12)
        print(f"  → Contraseña generada: {admin_password}")
    admin_nombre = ask("Nombre completo del admin", nombre)
    secret_key   = secrets.token_hex(32)

    # — confirmar —
    print("\n" + "-" * 60)
    print(f"  Comercio:    {nombre}")
    print(f"  Slug:        {slug}")
    print(f"  Contenedor:  contalibra-{slug}")
    print(f"  Puerto:      {port}")
    if domain:
        print(f"  Dominio:     {domain}")
    print(f"  Admin:       {admin_user} / {admin_password}")
    print("-" * 60)
    if ask("¿Confirmar? [S/n]", "s").lower() == "n":
        sys.exit("Cancelado.")

    # — directorios —
    data_dir = client_dir / "data"
    for sub in ["logos","arca_certs","facturas_pdf","remitos_pdf","presupuestos_pdf"]:
        (data_dir / sub).mkdir(parents=True, exist_ok=True)
    print(f"[OK] Directorios en {client_dir}")

    # — config.json — (claves deben coincidir con _DEFAULTS en config_manager.py)
    config = {
        "empresa_nombre": nombre, "empresa_direccion": "", "empresa_telefono": "",
        "empresa_email": "", "empresa_cuit": "",
        "empresa_iva_condition": "Responsable Inscripto",
    }
    (data_dir / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("[OK] config.json creado")

    # — detectar red Docker —
    net_name    = "stack_stack-net"
    net_section = f"""
networks:
  stack-net:
    external: true
    name: {net_name}
"""
    net_ref = "\n    networks:\n      - stack-net"
    if not network_exists(net_name):
        print(f"[WARN] Red '{net_name}' no encontrada — el contenedor usará la red por defecto.")
        net_section = ""
        net_ref     = ""

    # — docker-compose.yml —
    compose = f"""\
services:
  contalibra:
    image: {IMAGE_NAME}
    container_name: contalibra-{slug}
    restart: unless-stopped
    ports:
      - "{port}:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATA_DIR=/app/data
      - SECRET_KEY={secret_key}
      - ADMIN_USER={admin_user}
      - ADMIN_PASSWORD={admin_password}
      - ADMIN_NOMBRE={admin_nombre}
{net_ref.lstrip()}
{net_section}"""
    (client_dir / "docker-compose.yml").write_text(compose)
    print("[OK] docker-compose.yml creado")

    # — resumen del cliente —
    (client_dir / "cliente.json").write_text(
        json.dumps({
            "nombre": nombre, "slug": slug, "domain": domain,
            "port": port, "container": f"contalibra-{slug}",
            "admin_user": admin_user, "admin_password": admin_password,
        }, indent=2, ensure_ascii=False)
    )

    # — imagen Docker —
    if not image_exists():
        build_image()
    else:
        if ask(f"Imagen {IMAGE_NAME} ya existe. ¿Reconstruir? [s/N]", "n").lower() == "s":
            build_image()

    # — levantar —
    print(f"\n[*] Iniciando contalibra-{slug} ...")
    r = subprocess.run(["docker","compose","up","-d"], cwd=str(client_dir))
    if r.returncode != 0:
        sys.exit("[ERROR] No se pudo iniciar el contenedor.")

    print("\n" + "=" * 60)
    print("  CLIENTE DADO DE ALTA EXITOSAMENTE")
    print("=" * 60)
    print(f"  Comercio:    {nombre}")
    print(f"  URL local:   http://localhost:{port}")
    if domain:
        print(f"  Dominio:     https://{domain}")
    print(f"  Admin:       {admin_user}  /  {admin_password}")
    print(f"  Datos:       {data_dir}")
    print(f"  Logs:        docker logs contalibra-{slug}")
    print("=" * 60)
    print("\n[!] Guardá las credenciales — no se volverán a mostrar.")

    # — proxy NPM (opcional) —
    if domain and _NPM_AVAILABLE:
        npm = client_from_config()
        if npm:
            cfg_ok = ask("¿Configurar proxy + SSL en Nginx Proxy Manager? [S/n]", "s").lower()
            if cfg_ok != "n":
                _setup_npm_proxy(npm, domain, port)
        else:
            print(f"[INFO] NPM no configurado. Ejecutá npm_setup.py para habilitar el proxy automático.")
            print(f"[!]    Apuntá {domain} → localhost:{port} en tu proxy inverso manualmente.")
    elif domain:
        print(f"[!] Apuntá {domain} → localhost:{port} en tu proxy inverso.")


if __name__ == "__main__":
    main()
