# Plano de Migracacao Grafica: tkinter → PySide6

**Projeto:** CapiHeater v0.9.5
**Branch:** `feature/pyside6-migration`
**Data:** 2026-03-29

---

## 1. Situacao Atual

- **Framework:** tkinter puro + ttk
- **Arquivos GUI:** 12 arquivos, ~4.968 linhas
- **Build:** PyInstaller 6.11.1, onedir, Python 3.11, CI windows-2022
- **Tema:** Dark theme customizado via ttk.Style (20+ estilos)

### Inventario de arquivos (por complexidade):

| Arquivo | Linhas | Complexidade |
|---------|--------|-------------|
| `gui/accounts_tab.py` | 882 | Alta |
| `gui/targets_tab.py` | 608 | Alta |
| `gui/docs_tab.py` | 608 | Media |
| `gui/schedule_tab.py` | 605 | Alta |
| `gui/app.py` | 548 | Media-Alta |
| `gui/login_window.py` | 427 | Media |
| `gui/settings_tab.py` | 325 | Media |
| `gui/dashboard_tab.py` | 320 | Media |
| `gui/admin_tab.py` | 252 | Baixa |
| `gui/logs_tab.py` | 228 | Baixa |
| `gui/widgets/account_card.py` | 118 | Baixa |
| `gui/widgets/status_indicator.py` | 58 | Baixa |

---

## 2. Mapeamento tkinter → PySide6

### 2.1 Widgets

| tkinter | PySide6 |
|---------|---------|
| `tk.Tk` | `QApplication` + `QMainWindow` |
| `tk.Toplevel` | `QDialog` |
| `ttk.Notebook` | `QTabWidget` |
| `ttk.Frame` / `tk.Frame` | `QWidget` / `QFrame` |
| `ttk.Label` / `tk.Label` | `QLabel` |
| `ttk.Button` / `tk.Button` | `QPushButton` |
| `ttk.Entry` / `tk.Entry` | `QLineEdit` |
| `ttk.Combobox` | `QComboBox` |
| `ttk.Treeview` | `QTableWidget` |
| `ttk.Scrollbar` | Nativo do `QScrollArea` |
| `ttk.Progressbar` | `QProgressBar` |
| `ttk.Spinbox` / `tk.Spinbox` | `QSpinBox` / `QDoubleSpinBox` |
| `ttk.Checkbutton` / `tk.Checkbutton` | `QCheckBox` |
| `tk.Radiobutton` | `QRadioButton` + `QButtonGroup` |
| `tk.Listbox` | `QListWidget` |
| `tk.Text` (read-only/rich) | `QTextBrowser` |
| `tk.Text` (editavel) | `QPlainTextEdit` |
| `tk.Canvas` (status) | `QWidget` com `paintEvent` |
| `tk.Menu` | `QMenu` |
| `ttk.LabelFrame` | `QGroupBox` |
| `ttk.Style` | QSS (stylesheet global) |

### 2.2 Layouts

| tkinter | PySide6 |
|---------|---------|
| `pack(fill=X)` | `QVBoxLayout` / `QHBoxLayout` |
| `pack(side=LEFT)` | `QHBoxLayout.addWidget()` |
| `grid()` | `QGridLayout` / `QFormLayout` |
| Canvas scrollavel | `QScrollArea` |

### 2.3 Dialogos

| tkinter | PySide6 |
|---------|---------|
| `messagebox.showinfo()` | `QMessageBox.information()` |
| `messagebox.showwarning()` | `QMessageBox.warning()` |
| `messagebox.showerror()` | `QMessageBox.critical()` |
| `messagebox.askyesno()` | `QMessageBox.question()` |
| `simpledialog.askstring()` | `QInputDialog.getText()` |
| `simpledialog.askinteger()` | `QInputDialog.getInt()` |
| `filedialog.askopenfilenames()` | `QFileDialog.getOpenFileNames()` |

### 2.4 Eventos

| tkinter | PySide6 |
|---------|---------|
| `<Return>` | `QShortcut(Qt.Key_Return)` |
| `<Button-3>` | `customContextMenuRequested` signal |
| `<Double-1>` | `doubleClicked` signal |
| `<Control-a>` | `QShortcut("Ctrl+A")` |
| `<MouseWheel>` | Nativo do QScrollArea |
| `<<ComboboxSelected>>` | `currentIndexChanged` signal |
| `<<NotebookTabChanged>>` | `currentChanged` signal |
| `<<TreeviewSelect>>` | `itemSelectionChanged` signal |
| `trace_add("write")` | `textChanged` signal |

### 2.5 Threading

| tkinter | PySide6 |
|---------|---------|
| `threading.Thread` + `after(0, cb)` | `QThread` + `Signal` ou `Thread` + `QMetaObject.invokeMethod` |
| `self.root.after(ms, cb)` | `QTimer` |
| `self.root.after_cancel(id)` | `QTimer.stop()` |
| Queue polling com `after()` | `QTimer.timeout` signal |

### 2.6 Variaveis

| tkinter | PySide6 |
|---------|---------|
| `tk.StringVar` | Acesso direto (`widget.text()`) ou `Signal` |
| `tk.IntVar` / `tk.BooleanVar` | Acesso direto (`widget.value()`, `widget.isChecked()`) |
| `var.trace_add()` | Signals (`textChanged`, `valueChanged`) |

---

## 3. Tema QSS (Dark Theme)

Paleta de cores mantida do tema atual:

```css
/* gui/theme.qss */

* {
    font-family: "Segoe UI";
    font-size: 10pt;
    color: #e0e0e0;
}

QMainWindow, QDialog, QWidget#centralWidget {
    background-color: #1a1a2e;
}

QTabWidget::pane {
    border: none;
    background-color: #1a1a2e;
}

QTabBar::tab {
    background-color: #16213e;
    color: #9e9e9e;
    padding: 6px 14px;
}

QTabBar::tab:selected {
    background-color: #0f3460;
    color: #ffffff;
}

QFrame#card {
    background-color: #16213e;
    border-radius: 4px;
}

QPushButton#accent {
    background-color: #1a73e8;
    color: #ffffff;
    padding: 6px 12px;
    border: none;
    border-radius: 3px;
}

QPushButton#danger {
    background-color: #ff1744;
    color: #ffffff;
    padding: 6px 12px;
    border: none;
    border-radius: 3px;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #0d1b2a;
    color: #e0e0e0;
    border: 1px solid #0f3460;
    border-radius: 3px;
    padding: 4px 8px;
}

QTableWidget, QTreeView {
    background-color: #16213e;
    color: #e0e0e0;
    gridline-color: #0f3460;
    selection-background-color: #1a73e8;
    selection-color: #ffffff;
    border: none;
}

QHeaderView::section {
    background-color: #0f3460;
    color: #ffffff;
    font-weight: bold;
    padding: 4px;
    border: none;
}

QScrollBar:vertical {
    background: #1a1a2e;
    width: 10px;
}

QScrollBar::handle:vertical {
    background: #0f3460;
    border-radius: 5px;
    min-height: 20px;
}

QProgressBar {
    background-color: #1a1a2e;
    border: none;
    height: 6px;
}

QProgressBar::chunk {
    background-color: #1a73e8;
}

QCheckBox, QRadioButton {
    color: #e0e0e0;
}

QGroupBox {
    color: #ffffff;
    font-weight: bold;
    border: 1px solid #0f3460;
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 12px;
}

QStatusBar {
    background-color: #16213e;
    color: #9e9e9e;
    font-size: 9pt;
}
```

---

## 4. Fases da Migracao

### Fase 0 — Infraestrutura (criar antes de tudo)

**Arquivos novos:**
- `gui/theme.py` — constantes de cor + QSS como string Python
- `gui/base.py` — `BaseTab(QWidget)` com interface padrao (refresh, on_status_update, on_new_log)

**Arquivos modificados:**
- `requirements.txt` — adicionar `PySide6>=6.6.0`

**Verificacao:** QSS carrega sem erros, BaseTab instancia ok.

---

### Fase 1 — Widgets folha

**`gui/widgets/status_indicator.py`** (58 linhas)
- `tk.Canvas` → `QWidget` com `paintEvent`
- `create_oval` → `QPainter.drawEllipse`
- `itemconfig` → `self.update()` apos mudar cor

**`gui/widgets/account_card.py`** (118 linhas)
- `ttk.Frame` → `QFrame`
- Layout: `QHBoxLayout` (topo) + `QVBoxLayout` (geral)
- `ttk.Progressbar` → `QProgressBar`

**Verificacao:** Widgets renderizam corretamente isolados.

---

### Fase 2 — Login Window

**`gui/login_window.py`** (427 linhas)
- `LoginWindow(tk.Tk)` → `LoginDialog(QDialog)`
- Layout: `QVBoxLayout` simples (vertical)
- `tk.Entry` → `QLineEdit` (senha com `setEchoMode(Password)`)
- `tk.Checkbutton` → `QCheckBox`
- `self.bind("<Return>")` → `QShortcut` ou `returnPressed` signal
- Threading: manter `threading.Thread`, usar `QMetaObject.invokeMethod` para UI
- `self.after(500)` → `QTimer.singleShot(500)`
- `self.after(15000)` → `QTimer.singleShot(15000)`
- Persistencia (last_email.json, remember.dat) — sem mudanca

**Fluxo de lancamento:**
```python
# main.py
app = QApplication(sys.argv)
login = LoginDialog()
if login.exec() != QDialog.Accepted:
    return
main_window = CapiHeaterApp(login.auth_session)
main_window.show()
sys.exit(app.exec())
```

**Verificacao:** Login funciona, auto-login funciona, timeout funciona, registrar funciona.

---

### Fase 3 — Tabs simples

**`gui/logs_tab.py`** (228 linhas)
- `ttk.Treeview` → `QTableWidget` (6 colunas)
- Filtros: `ttk.Combobox` → `QComboBox`
- Auto-refresh: `self.after()` → `QTimer`
- Tags de cor → `QTableWidgetItem.setForeground(QColor(...))`

**`gui/admin_tab.py`** (252 linhas)
- `tk.Frame` → `QWidget`
- `tk.Radiobutton` → `QRadioButton` + `QButtonGroup`
- `simpledialog.askstring` → `QInputDialog.getText`

**`gui/dashboard_tab.py`** (320 linhas)
- Cards: `ttk.Frame` → `QFrame` com QSS
- `ttk.Treeview` → `QTableWidget` (5 colunas)
- Context menu: `<Button-3>` → `customContextMenuRequested`
- `simpledialog.askinteger` → `QInputDialog.getInt`
- Unicode dots (●/○) → mesmos caracteres ou QIcon colorido

**Verificacao por tab:** dados carregam, filtros funcionam, menus de contexto funcionam, cores corretas.

---

### Fase 4 — Tabs medias

**`gui/settings_tab.py`** (325 linhas)
- Canvas scrollavel → `QScrollArea` (grande simplificacao!)
- Mouse wheel → nativo (sem binding manual)
- `ttk.Spinbox` → `QSpinBox` / `QDoubleSpinBox`
- Presets dropdown → `QComboBox.currentIndexChanged`
- 24 campos de scroll config → `QFormLayout` ou `QGridLayout`

**`gui/docs_tab.py`** (608 linhas)
- Layout dois paineis → `QSplitter(Qt.Horizontal)`
- Sidebar `tk.Listbox` → `QListWidget`
- `tk.Text` com tags → `QTextBrowser` com HTML
- Tags (title/section/body) → `<h2>`, `<h3>`, `<p>`, `<hr>`
- Navegacao por marks → `scrollToAnchor()` com `<a name="...">`

**Verificacao:** scroll suave, documentacao renderiza bem, presets aplicam valores.

---

### Fase 5 — Tabs complexas

**`gui/targets_tab.py`** (608 linhas)
- `ttk.Treeview` → `QTableWidget`
- Bulk add `tk.Text` → `QPlainTextEdit`
- `tk.Listbox(MULTIPLE)` → `QListWidget(ExtendedSelection)`
- Form dialogs → `QDialog` + `QFormLayout`
- `webbrowser.open()` — sem mudanca

**`gui/schedule_tab.py`** (605 linhas)
- `ttk.Treeview` → `QTableWidget` (8 colunas)
- Edit day dialog com ~12 Spinbox → `QDialog` + `QGridLayout` + `QSpinBox`
- `tk.Checkbutton` → `QCheckBox`
- `dlg.wait_window()` → `dlg.exec()`

**`gui/accounts_tab.py`** (882 linhas) — MAIOR e MAIS COMPLEXA
- `ttk.Treeview` → `QTableWidget` (7 colunas)
- Search com trace → `QLineEdit.textChanged`
- Form dialog com grid → `QDialog` + `QFormLayout`
- `tk.Listbox(MULTIPLE)` para categorias → `QListWidget(ExtendedSelection)`
- `filedialog.askopenfilenames` → `QFileDialog.getOpenFileNames`
- Bulk edit dialog → `QDialog` customizado
- Bulk import dialog → `QDialog` customizado

**Verificacao por tab:** CRUD completo funciona, bulk operations funcionam, file dialogs abrem, categorias selecionam.

---

### Fase 6 — Janela principal

**`gui/app.py`** (548 linhas)
- `CapiHeaterApp` com `self.root = tk.Tk()` → herda `QMainWindow`
- `ttk.Notebook` → `QTabWidget`
- `_configure_styles()` → REMOVIDO (QSS global cuida)
- Status bar: `ttk.Label` + `tk.StringVar` → `QStatusBar` nativo
- Logout button → `QStatusBar.addPermanentWidget()`
- Queue polling: `after(100)` → `QTimer(100ms)`
- Update progress: `tk.Toplevel` → `QDialog` + `QProgressBar`
- `_center_window()` → calculo com `QScreen.geometry()`
- Threading auto-update → `QThread` com signals

**Verificacao:** Tabs carregam, status bar atualiza, queue polling funciona, update checker funciona.

---

### Fase 7 — Entry point e Build

**`main.py`**
- Reescrever para `QApplication` unico
- Login via `LoginDialog.exec()`
- Main window via `CapiHeaterApp.show()` + `app.exec()`
- High DPI: `QApplication.setHighDpiScaleFactorRoundingPolicy(PassThrough)`

**`capiheater.spec`**
- Remover hidden imports: `tkinter`, `tkinter.ttk`, `tkinter.messagebox`, `tkinter.filedialog`, `tkinter.simpledialog`
- Adicionar hidden imports: `PySide6.QtWidgets`, `PySide6.QtCore`, `PySide6.QtGui`
- Adicionar excludes: `tkinter`
- Excluir modulos Qt nao usados para reduzir tamanho

**`.github/workflows/release.yml`**
- Adicionar verificacao de `qwindows.dll` no dist

**`ci/verify_exe.py`**
- Adicionar check para Qt platform plugins

**Verificacao:** `pyinstaller capiheater.spec` compila, exe abre, login → todas as tabs → funcionalidade completa.

---

## 5. Riscos e Mitigacoes

| Risco | Mitigacao |
|-------|----------|
| Thread safety — PySide6 e mais rígido | Usar Signal/Slot ou QMetaObject.invokeMethod em TODOS os pontos |
| Exe muito grande (+50-80MB) | Excluir modulos Qt nao usados (Qt3D, Bluetooth, Multimedia, etc.) |
| Qt platform plugins faltando no exe | Verificar qwindows.dll no CI, adicionar ao spec se necessario |
| Combobox dropdown dificil de estilizar | QSS especifico + setItemDelegate se necessario |
| Cores de linha na QTableWidget | Helper `set_row_color(table, row, color)` reutilizavel |
| Dados em Treeview items | `QTableWidgetItem.setData(Qt.UserRole, id)` para IDs |

---

## 6. Ordem de Execucao Resumida

```
Fase 0: gui/theme.py, gui/base.py, requirements.txt
Fase 1: gui/widgets/status_indicator.py, gui/widgets/account_card.py
Fase 2: gui/login_window.py
Fase 3: gui/logs_tab.py → gui/admin_tab.py → gui/dashboard_tab.py
Fase 4: gui/settings_tab.py → gui/docs_tab.py
Fase 5: gui/targets_tab.py → gui/schedule_tab.py → gui/accounts_tab.py
Fase 6: gui/app.py
Fase 7: main.py → capiheater.spec → release.yml → verify_exe.py
```

> **Nota:** Cada fase so comeca depois da anterior estar testada e funcionando.
