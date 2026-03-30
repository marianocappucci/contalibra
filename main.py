#!/usr/bin/env python3
"""
Generador de Remitos
"""
import os
import sys
from datetime import date

from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

import database as db
import pdf_generator as pdf_gen

console = Console()


# ── Utilidades ─────────────────────────────────────────────────────────────────

def clear():
    os.system("clear")


def pause():
    input("\nPresione Enter para continuar...")


def input_float(prompt, default=None):
    while True:
        raw = input(prompt).strip().replace(",", ".")
        if raw == "" and default is not None:
            return default
        try:
            val = float(raw)
            if val < 0:
                raise ValueError
            return val
        except ValueError:
            console.print("[red]Ingrese un número válido (≥ 0).[/red]")


def input_date(prompt):
    today = date.today().isoformat()
    while True:
        raw = input(f"{prompt} [Enter = {today}]: ").strip()
        if raw == "":
            return today
        try:
            date.fromisoformat(raw)
            return raw
        except ValueError:
            console.print("[red]Formato inválido. Use YYYY-MM-DD.[/red]")


def input_tax_rate():
    console.print("  Tasa de IVA disponible: [cyan]1[/cyan] 21%  [cyan]2[/cyan] 10.5%  [cyan]3[/cyan] 0%  [cyan]4[/cyan] Otro")
    opt = input("  Opción [Enter=21%]: ").strip()
    if opt == "2":
        return 0.105
    elif opt == "3":
        return 0.0
    elif opt == "4":
        pct = input_float("  Porcentaje de IVA (ej: 27): ", default=21.0)
        return pct / 100
    return 0.21


# ── Clientes ───────────────────────────────────────────────────────────────────

def show_clients_table(clients):
    t = Table(box=box.SIMPLE_HEAD, show_lines=False)
    t.add_column("#", style="dim", width=4)
    t.add_column("Nombre", style="bold")
    t.add_column("CUIT / DNI")
    t.add_column("Teléfono")
    t.add_column("Email")
    for i, c in enumerate(clients, 1):
        t.add_row(str(i), c["name"], c["cuit_dni"] or "—", c["phone"] or "—", c["email"] or "—")
    console.print(t)


def pick_client():
    clients = db.get_all_clients()
    if not clients:
        console.print("[yellow]No hay clientes registrados.[/yellow]")
        return None
    show_clients_table(clients)
    while True:
        raw = input("Seleccione cliente (número): ").strip()
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(clients):
                return clients[idx]
        except ValueError:
            pass
        console.print("[red]Número inválido.[/red]")


def form_client(existing=None):
    """Pide datos de cliente. Si existing != None, muestra los valores actuales."""
    def field(label, key, required=False):
        current = (existing or {}).get(key, "")
        hint = f" [dim][{current}][/dim]" if current else ""
        console.print(f"  {label}{hint}:", end=" ")
        val = input("").strip()
        if val == "" and current:
            return current
        if val == "" and required:
            console.print("[red]Este campo es obligatorio.[/red]")
            return field(label, key, required)
        return val

    name    = field("Nombre/Razón social", "name", required=True)
    address = field("Domicilio", "address")
    cuit    = field("CUIT / DNI", "cuit_dni")
    email   = field("Email", "email")
    phone   = field("Teléfono", "phone")
    return name, address, cuit, email, phone


def clientes_menu():
    while True:
        clear()
        console.print(Panel("[bold]CLIENTES[/bold]", expand=False))
        console.print(" [cyan]1[/cyan]  Listar clientes")
        console.print(" [cyan]2[/cyan]  Nuevo cliente")
        console.print(" [cyan]3[/cyan]  Editar cliente")
        console.print(" [cyan]4[/cyan]  Eliminar cliente")
        console.print(" [cyan]5[/cyan]  Ver remitos de un cliente")
        console.print(" [cyan]0[/cyan]  Volver")
        opt = input("\nOpción: ").strip()

        if opt == "1":
            clear()
            clients = db.get_all_clients()
            if clients:
                show_clients_table(clients)
            else:
                console.print("[yellow]Sin clientes registrados.[/yellow]")
            pause()

        elif opt == "2":
            clear()
            console.print("[bold]Nuevo cliente[/bold]\n")
            name, address, cuit, email, phone = form_client()
            cid = db.create_client(name, address, cuit, email, phone)
            console.print(f"\n[green]Cliente creado (ID {cid}).[/green]")
            pause()

        elif opt == "3":
            clear()
            client = pick_client()
            if client:
                console.print(f"\n[bold]Editar: {client['name']}[/bold]")
                console.print("  (Enter para mantener el valor actual)\n")
                name, address, cuit, email, phone = form_client(existing=client)
                db.update_client(client["id"], name=name, address=address,
                                 cuit_dni=cuit, email=email, phone=phone)
                console.print("[green]Cliente actualizado.[/green]")
            pause()

        elif opt == "4":
            clear()
            client = pick_client()
            if client:
                if Confirm.ask(f"¿Eliminar a [bold]{client['name']}[/bold]?"):
                    try:
                        db.delete_client(client["id"])
                        console.print("[green]Cliente eliminado.[/green]")
                    except ValueError as e:
                        console.print(f"[red]{e}[/red]")
            pause()

        elif opt == "5":
            clear()
            client = pick_client()
            if client:
                remitos = db.get_remitos_by_client(client["id"])
                console.print(f"\n[bold]Remitos de {client['name']}[/bold]")
                if remitos:
                    show_remitos_table(remitos)
                else:
                    console.print("[yellow]Sin remitos.[/yellow]")
            pause()

        elif opt == "0":
            break


# ── Remitos ────────────────────────────────────────────────────────────────────

def show_remitos_table(remitos):
    t = Table(box=box.SIMPLE_HEAD)
    t.add_column("#", style="dim", width=4)
    t.add_column("Número")
    t.add_column("Fecha")
    t.add_column("Cliente", style="bold")
    t.add_column("Total", justify="right", style="green")
    for i, r in enumerate(remitos, 1):
        t.add_row(str(i), r["number"], r["date"], r["client_name"],
                  f"$ {r['total']:,.2f}")
    console.print(t)


def input_items():
    items = []
    console.print("\n[bold]Ingrese los ítems del remito.[/bold]")
    console.print("  (Deje la descripción vacía para terminar)\n")
    while True:
        console.print(f"  [dim]Ítem {len(items)+1}[/dim]")
        desc = input("    Descripción: ").strip()
        if desc == "":
            if not items:
                console.print("[red]Debe agregar al menos un ítem.[/red]")
                continue
            break
        qty = input_float("    Cantidad: ")
        unit_price = input_float("    Precio unitario: $")
        subtotal = round(qty * unit_price, 2)
        items.append({"description": desc, "qty": qty,
                      "unit_price": unit_price, "subtotal": subtotal})
        console.print(f"    [green]→ Subtotal: $ {subtotal:,.2f}[/green]\n")
    return items


def preview_remito(number, date_str, client, items, subtotal, tax_rate, tax_amount, total):
    clear()
    console.print(Panel(f"[bold]REMITO N° {number}[/bold]  —  {date_str}", expand=False))

    console.print(f"\n  [bold]Cliente:[/bold] {client['name']}")
    if client.get("cuit_dni"):
        console.print(f"  [bold]CUIT/DNI:[/bold] {client['cuit_dni']}")

    t = Table(box=box.SIMPLE_HEAD, show_header=True)
    t.add_column("Descripción")
    t.add_column("Cant.", justify="right")
    t.add_column("P. Unit.", justify="right")
    t.add_column("Subtotal", justify="right")
    for item in items:
        t.add_row(item["description"], f"{item['qty']:g}",
                  f"$ {item['unit_price']:,.2f}", f"$ {item['subtotal']:,.2f}")
    console.print(t)

    tax_pct = int(tax_rate * 100)
    console.print(f"  Subtotal:  [cyan]$ {subtotal:,.2f}[/cyan]")
    console.print(f"  IVA {tax_pct}%:  [cyan]$ {tax_amount:,.2f}[/cyan]")
    console.print(f"  [bold green]TOTAL:     $ {total:,.2f}[/bold green]\n")


def nuevo_remito():
    clear()
    console.print(Panel("[bold]NUEVO REMITO[/bold]", expand=False))

    # Cliente
    clients = db.get_all_clients()
    if clients:
        console.print("\n[bold]Seleccionar cliente:[/bold]")
        console.print(" [cyan]1[/cyan]  Elegir cliente existente")
        console.print(" [cyan]2[/cyan]  Crear nuevo cliente")
        opt = input("\nOpción: ").strip()
        if opt == "2":
            console.print()
            name, address, cuit, email, phone = form_client()
            cid = db.create_client(name, address, cuit, email, phone)
            client = db.get_client(cid)
        else:
            client = pick_client()
            if not client:
                return
    else:
        console.print("\n[yellow]No hay clientes. Creando nuevo cliente...[/yellow]\n")
        name, address, cuit, email, phone = form_client()
        cid = db.create_client(name, address, cuit, email, phone)
        client = db.get_client(cid)

    # Fecha y tasa IVA
    console.print()
    date_str = input_date("Fecha del remito")
    console.print("  Tasa de IVA:")
    tax_rate = input_tax_rate()

    # Ítems
    items = input_items()

    # Observaciones
    observations = input("Observaciones (opcional): ").strip()

    # Cálculos
    subtotal = round(sum(i["subtotal"] for i in items), 2)
    tax_amount = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax_amount, 2)

    number = db.get_next_remito_number()

    # Vista previa
    preview_remito(number, date_str, client, items, subtotal, tax_rate, tax_amount, total)

    if not Confirm.ask("¿Guardar remito y generar PDF?"):
        console.print("[yellow]Remito descartado.[/yellow]")
        pause()
        return

    # Guardar en DB
    remito_id = db.create_remito(
        number=number, date=date_str,
        client_id=client["id"],
        client_name=client["name"],
        client_address=client.get("address", ""),
        client_cuit=client.get("cuit_dni", ""),
        client_email=client.get("email", ""),
        client_phone=client.get("phone", ""),
        items=items, subtotal=subtotal,
        tax_rate=tax_rate, tax_amount=tax_amount,
        total=total, observations=observations,
    )

    # Generar PDF
    remito_data = db.get_remito(remito_id)
    pdf_path = pdf_gen.generate_pdf(remito_data)
    db.update_remito_pdf_path(remito_id, pdf_path)

    console.print(f"\n[bold green]Remito guardado exitosamente.[/bold green]")
    console.print(f"  PDF generado en:\n  [cyan]{pdf_path}[/cyan]")
    pause()


def ver_remitos():
    clear()
    console.print(Panel("[bold]REMITOS[/bold]", expand=False))

    remitos = db.get_all_remitos()
    if not remitos:
        console.print("[yellow]No hay remitos registrados.[/yellow]")
        pause()
        return

    show_remitos_table(remitos)

    raw = input("\nNúmero de remito para ver detalle (Enter para volver): ").strip()
    if raw == "":
        return
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(remitos):
            r = remitos[idx]
            preview_remito(r["number"], r["date"],
                           {"name": r["client_name"], "cuit_dni": r["client_cuit"]},
                           r["items"], r["subtotal"], r["tax_rate"],
                           r["tax_amount"], r["total"])
            if r.get("observations"):
                console.print(f"  [bold]Observaciones:[/bold] {r['observations']}")
            if r.get("pdf_path") and os.path.exists(r["pdf_path"]):
                console.print(f"\n  PDF: [cyan]{r['pdf_path']}[/cyan]")
                if Confirm.ask("  ¿Re-generar PDF?"):
                    new_path = pdf_gen.generate_pdf(r)
                    db.update_remito_pdf_path(r["id"], new_path)
                    console.print(f"  [green]PDF regenerado: {new_path}[/green]")
            else:
                if Confirm.ask("  ¿Generar PDF?"):
                    path = pdf_gen.generate_pdf(r)
                    db.update_remito_pdf_path(r["id"], path)
                    console.print(f"  [green]PDF generado: {path}[/green]")
    except (ValueError, IndexError):
        console.print("[red]Número inválido.[/red]")

    pause()


def buscar_remitos():
    clear()
    query = input("Buscar (número, cliente, observaciones): ").strip()
    if not query:
        return
    results = db.search_remitos(query)
    if results:
        show_remitos_table(results)
    else:
        console.print("[yellow]Sin resultados.[/yellow]")
    pause()


# ── Menú principal ─────────────────────────────────────────────────────────────

def main_menu():
    while True:
        clear()
        console.print(Panel(
            "[bold white]GENERADOR DE REMITOS[/bold white]",
            subtitle="[dim]Ctrl+C para salir[/dim]",
            expand=False,
        ))
        console.print(" [cyan]1[/cyan]  Nuevo remito")
        console.print(" [cyan]2[/cyan]  Ver remitos")
        console.print(" [cyan]3[/cyan]  Buscar remito")
        console.print(" [cyan]4[/cyan]  Clientes")
        console.print(" [cyan]0[/cyan]  Salir\n")
        opt = input("Opción: ").strip()

        if opt == "1":
            nuevo_remito()
        elif opt == "2":
            ver_remitos()
        elif opt == "3":
            buscar_remitos()
        elif opt == "4":
            clientes_menu()
        elif opt == "0":
            console.print("\nHasta luego.")
            sys.exit(0)


if __name__ == "__main__":
    db.init_db()
    os.makedirs(pdf_gen.PDF_DIR, exist_ok=True)
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n\nHasta luego.")
        sys.exit(0)
