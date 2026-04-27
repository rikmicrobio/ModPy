# ModPy — Homology Modelling Pipeline
**Developed by Rik Ganguly, Post Doctoral Fellow @ Hazra Group, IIT Roorkee**

---
<img width="406" height="426" alt="Image" src="https://github.com/user-attachments/assets/b9b2a88a-3460-4975-8b00-e76ee8c7a70d" />

## Files included

| File | Purpose |
|------|---------|
| `app.py` | GUI front-end (Tkinter) |
| `homology_model.py` | Modelling back-end (MODELLER) |
| `logo.png` | App logo |
| `app.spec` | PyInstaller build spec |

---

## How to run (development / script mode)

### 1. Install dependencies
```bash
pip install pillow           # for logo display in the GUI
# MODELLER must be installed separately — see below
```

### 2. Launch the GUI
```bash
python app.py
```

---

## MODELLER installation

ModPy uses [MODELLER](https://salilab.org/modeller/) for homology modelling.

1. Register for a free academic licence at https://salilab.org/modeller/registration.html
2. Download and install MODELLER for your OS
3. Set your licence key in the MODELLER config file (`modeller/config.py`)

**Without MODELLER installed**, the app runs in *demo mode* — all GUI features work but no real models are generated.

---

## How to build a standalone executable (PyInstaller)

```bash
pip install pyinstaller pillow
pyinstaller app.spec
```

The executable will be at `dist/ModPy` (Linux/macOS) or `dist/ModPy.exe` (Windows).

> **Note:** You must have MODELLER installed on the target machine for real modelling runs.

---

## Pipeline modes

| Mode | Description |
|------|-------------|
| `single` | Build one model quickly |
| `multi` | Build N models, rank by DOPE score |
| `loop` | Loop refinement only |
| `full` | Multi-model build + full loop refinement (recommended) |

---

## Output directory

Use the **Output Directory** browser in the GUI to choose where results are saved.  
Default: `results/` in the current working directory.

---

## Contact
Hazra Group · Department of Chemistry · IIT Roorkee
