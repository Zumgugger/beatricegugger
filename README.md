# Beatrice Gugger Website

Eine moderne Website für Kurse und Kunstgalerie mit Admin-Panel.

## Features

- **Public Website**: Landing Page, About/Kontakt, Kursangebote, Kunstgalerie
- **Course Registration**: Anmeldeformular mit E-Mail-Bestätigung
- **Admin Panel**: WYSIWYG-Editing für alle Inhalte
- **Responsive Design**: Optimiert für Desktop, Tablet und Mobile

## Installation

### Voraussetzungen

- Python 3.10+
- Git

### Setup

1. Repository klonen:
```bash
git clone https://github.com/Zumgugger/beatricegugger.git
cd beatricegugger
```

2. Virtual Environment erstellen:
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# oder
.venv\Scripts\activate  # Windows
```

3. Dependencies installieren:
```bash
pip install -r requirements.txt
```

4. Environment-Variablen konfigurieren:
```bash
cp .env.example .env
# Bearbeite .env und passe die Werte an
```

5. Datenbank initialisieren:
```bash
python init_db.py
```

6. Flask-Migrationen initialisieren:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

7. Server starten:
```bash
python run.py
```

Die Website ist nun verfügbar unter: http://localhost:5003

### Admin-Zugang

Nach der Initialisierung der Datenbank:
- URL: http://localhost:5003/admin/login
- E-Mail: admin@beatricegugger.ch
- Passwort: admin123

⚠️ **Wichtig**: Ändern Sie das Admin-Passwort nach dem ersten Login!

## Projekt-Struktur

```
beatricegugger/
├── app/                    # Flask-Anwendung
│   ├── routes/            # Route-Blueprints
│   ├── static/            # CSS, JS, Bilder
│   ├── templates/         # HTML-Templates
│   ├── __init__.py        # App Factory
│   └── models.py          # Datenbankmodelle
├── uploads/               # Hochgeladene Inhalte
├── PNGs/                  # Statische Design-Assets
├── docs/                  # Dokumentation
├── config.py              # Konfiguration
├── run.py                 # Entry Point
├── init_db.py             # DB-Initialisierung
└── requirements.txt       # Python-Dependencies
```

## Entwicklung

### Neue Migration erstellen

```bash
flask db migrate -m "Beschreibung"
flask db upgrade
```

### Tests ausführen

```bash
python -m pytest
```

## Deployment

Siehe [docs/deployment.md](docs/deployment.md) für Deployment-Anweisungen.

## Technologie-Stack

- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: Jinja2 Templates, Vanilla JavaScript
- **Authentication**: Flask-Login
- **Email**: Flask-Mail

## Lizenz

© 2026 Beatrice Gugger. Alle Rechte vorbehalten.
