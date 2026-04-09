"""
Página GUI para generar certificados ARCA de forma automatizada.
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFormLayout, QMessageBox, QScrollArea, QFrame, QTextEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import arca_setup


def make_btn(label, style="primary"):
    """Helper para crear botones con estilo."""
    btn = QPushButton(label)
    btn.setCursor(Qt.PointingHandCursor)

    styles = {
        "primary": "background-color: #2563eb; color: white; padding: 8px 16px; border-radius: 5px; font-weight: bold; border: none;",
        "success": "background-color: #16a34a; color: white; padding: 8px 16px; border-radius: 5px; font-weight: bold; border: none;",
        "danger": "background-color: #dc2626; color: white; padding: 8px 16px; border-radius: 5px; font-weight: bold; border: none;",
        "secondary": "background-color: #6b7280; color: white; padding: 8px 16px; border-radius: 5px; border: none;",
        "muted": "background-color: #d1d5db; color: #374151; padding: 8px 16px; border-radius: 5px; border: none;",
    }
    btn.setStyleSheet(styles.get(style, styles["primary"]))
    return btn


class ARCAConfigPage(QWidget):
    """Página para generar certificados ARCA de forma automatizada."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 20)
        root.setSpacing(12)

        # Título
        title = QLabel("Configuración ARCA - Generar Certificado")
        title.setObjectName("page_title")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #0f172a;")
        root.addWidget(title)

        # Descripción
        desc = QLabel(
            "Genera automáticamente una clave privada y CSR para tu empresa.\n"
            "Luego sube el CSR a ARCA para obtener el certificado."
        )
        desc.setStyleSheet("color: #64748b; font-size: 12px;")
        root.addWidget(desc)

        # Separador
        sep = QFrame()
        sep.setStyleSheet("background-color: #e2e8f0;")
        sep.setFixedHeight(1)
        root.addWidget(sep)

        # Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(scroll)

        container = QWidget()
        container.setObjectName("content_area")
        scroll.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 8, 0, 28)
        layout.setSpacing(16)

        # Card 1: Datos de la empresa
        card1, form1 = self._card("Datos de la Empresa")
        layout.addWidget(card1)

        self._empresa_edit = QLineEdit()
        self._empresa_edit.setPlaceholderText("Ej: compulibra")
        form1.addRow("Nombre Empresa *", self._empresa_edit)

        self._cuit_edit = QLineEdit()
        self._cuit_edit.setPlaceholderText("Ej: 20289933604 (sin guiones)")
        self._cuit_edit.setMaximumWidth(300)
        form1.addRow("CUIT *", self._cuit_edit)

        self._sistema_edit = QLineEdit()
        self._sistema_edit.setPlaceholderText("Ej: sistemas_remitos (opcional)")
        form1.addRow("Nombre del Sistema", self._sistema_edit)

        # Card 2: Directorio de salida
        card2, form2 = self._card("Ubicación de Certificados")
        layout.addWidget(card2)

        self._directorio_edit = QLineEdit()
        self._directorio_edit.setText("certs/")
        self._directorio_edit.setPlaceholderText("Carpeta donde guardar")
        form2.addRow("Directorio", self._directorio_edit)

        info = QLabel("Los certificados se guardarán en: <directorio>/<empresa>_<cuit>/")
        info.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic;")
        form2.addRow("", info)

        # Botones
        btns_layout = QHBoxLayout()
        b_generar = make_btn("Generar Certificado", "success")
        b_generar.clicked.connect(self._generar)
        btns_layout.addWidget(b_generar)
        btns_layout.addStretch()
        layout.addLayout(btns_layout)

        # Card 3: Resultado
        card3, form3 = self._card("Resultado")
        layout.addWidget(card3)

        self._resultado_text = QTextEdit()
        self._resultado_text.setReadOnly(True)
        self._resultado_text.setMinimumHeight(300)
        self._resultado_text.setStyleSheet(
            "background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 5px; "
            "font-family: 'Courier New', monospace; font-size: 11px;"
        )
        form3.addRow(self._resultado_text)

        layout.addStretch()

    def _card(self, title):
        """Crea una tarjeta con título."""
        card = QFrame()
        card.setStyleSheet(
            "background-color: white; border: 1px solid #e2e8f0; border-radius: 8px;"
        )
        v = QVBoxLayout(card)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(12)

        lbl = QLabel(title)
        lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #0f172a;")
        v.addWidget(lbl)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)
        v.addLayout(form)

        return card, form

    def _generar(self):
        """Genera clave y CSR."""
        empresa = self._empresa_edit.text().strip()
        cuit = self._cuit_edit.text().strip().replace("-", "").replace(" ", "")
        sistema = self._sistema_edit.text().strip() or None
        directorio = self._directorio_edit.text().strip()

        # Validaciones
        if not empresa:
            QMessageBox.warning(self, "Atención", "Ingresa el nombre de la empresa.")
            self._empresa_edit.setFocus()
            return

        if not cuit or not cuit.isdigit() or len(cuit) != 11:
            QMessageBox.warning(self, "Atención", "CUIT inválido. Debe tener 11 dígitos.")
            self._cuit_edit.setFocus()
            return

        # Generar certificados
        resultado = arca_setup.generar_carpeta_empresa(
            base_dir=directorio,
            empresa=empresa,
            cuit=cuit,
            sistema=sistema
        )

        # Mostrar resultado
        mensaje = "\n".join(resultado['mensajes'])

        if resultado['éxito']:
            # Generar instrucciones
            instrucciones = arca_setup.crear_instrucciones_upload(
                empresa=empresa,
                cuit=cuit,
                csr_path=resultado['csr_path']
            )
            mensaje += instrucciones

            self._resultado_text.setText(mensaje)
            QMessageBox.information(
                self,
                "✓ Certificado Generado",
                f"Clave y CSR generados exitosamente.\n\n"
                f"Ubicación: {os.path.dirname(resultado['csr_path'])}\n\n"
                f"Lee las instrucciones en el área de resultado."
            )
        else:
            self._resultado_text.setText(f"❌ ERROR:\n{resultado['error']}")
            QMessageBox.critical(
                self,
                "Error",
                f"No se pudo generar el certificado:\n{resultado['error']}"
            )
