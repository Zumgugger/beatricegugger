# Implementierungsplan - beatricegugger.ch

## Projektstand (10. Januar 2026)

### ✅ Abgeschlossen
| Feature | Details |
|---------|---------|
| Projektstruktur | Flask-App mit Blueprints, SQLAlchemy ORM |
| Datenbank-Modelle | User, Page, Course, CourseRegistration, ArtCategory, ArtImage, NavigationItem, SiteSettings |
| Authentifizierung | Login/Logout, Session-basiert |
| Landingpage | Hero-Bereich, Navigation, Responsive |
| About/Kontakt | Zwei Sektionen (Kontakt + Über mich), In-Place Editing |
| Kurse Übersicht | Grid-Layout mit Kursanzeige |
| Kurs-Details | Einzelansicht mit Beschreibung |
| Kurs-Anmeldung | Formular mit E-Mail-Bestätigung |
| Art-Kategorien | Übersicht aller Kategorien |
| Art-Galerie | Bildergalerie pro Kategorie |
| Admin-Statusleiste | Zeigt Admin-Status + Logout-Link |
| In-Place Text-Editing | Titel und Inhalte direkt bearbeitbar |
| In-Place Bild-Upload | Bilder per Klick austauschbar |
| Responsive Design | Mobile-optimiert |
| Docker Setup | Dockerfile + docker-compose.yml |
| **Kurse in-place verwalten** | ✅ Neuer Kurs, Bearbeiten, Löschen, Anmeldungen anzeigen |
| **Art-Kategorien in-place** | ✅ Neue Kategorie, Bearbeiten, Löschen |
| **Galerie-Bilder in-place** | ✅ Bilder hochladen (multi), Löschen |
| **Intuitiver Admin** | ✅ Kein separates Dashboard, alles auf Public-Seiten |

### ⚠️ Teilweise implementiert
| Feature | Was fehlt |
|---------|-----------|
| - | - |

### ❌ Noch nicht implementiert
| Feature | Priorität |
|---------|-----------|
| SMS-Erinnerungen | NIEDRIG (später) |

---

## Phase 1: Admin-Funktionen In-Place ✅ ABGESCHLOSSEN

### 1.1 Kurse-Seite erweitern ✅
- [x] "Neuer Kurs" Button hinzufügen (nur für Admins sichtbar)
- [x] Kurs-Titel in-place editierbar machen
- [x] Kurs-Beschreibung in-place editierbar machen
- [x] Kurs-Bild per Klick austauschbar
- [x] Löschen-Button pro Kurs (mit Bestätigung)
- [x] "Anmeldungen anzeigen" Toggle pro Kurs

### 1.2 Art-Kategorien verwalten ✅
- [x] "Neue Kategorie" Button hinzufügen
- [x] Kategorie-Name in-place editierbar
- [x] Kategorie-Bild per Klick austauschbar
- [x] Löschen-Button pro Kategorie

### 1.3 Galerie-Bilder verwalten ✅
- [x] "Bild hinzufügen" Button in Galerie
- [x] Multi-Upload für mehrere Bilder
- [x] Löschen-Button pro Bild (mit Bestätigung)

### 1.4 Admin-Panel vereinfachen ✅
- [x] /admin/dashboard → Weiterleitung zur Startseite
- [x] Logout-Link in Statusleiste

---

## Phase 2: UI-Verbesserungen (Optional)

### 2.1 Admin-Controls Styling
- [ ] Einheitliche Admin-Buttons (grün für hinzufügen, rot für löschen)
- [ ] Hover-Effekte für editierbare Elemente
- [ ] Bestätigungs-Dialoge für Löschaktionen
- [ ] Loading-Spinner bei Speichervorgängen

### 2.2 Feedback & UX
- [ ] Toast-Nachrichten bei erfolgreichen Aktionen
- [ ] Fehler-Handling mit benutzerfreundlichen Meldungen
- [ ] Autosave-Indikator

---

## Phase 3: Testing & Deployment

### 3.1 Testing
- [ ] Unit-Tests für neue API-Endpoints
- [ ] E2E-Tests für Admin-Funktionen
- [ ] Mobile-Testing

### 3.2 Deployment
- [ ] Produktions-Konfiguration prüfen
- [ ] SSL-Zertifikat
- [ ] Backup-Strategie

---

## API-Endpoints (implementiert)

### Kurse
```
POST   /admin/api/course              → Neuen Kurs erstellen
POST   /admin/api/course/<id>/content → Kurs-Text aktualisieren  
POST   /admin/api/course/<id>/image   → Kurs-Bild aktualisieren
DELETE /admin/api/course/<id>         → Kurs löschen
```

### Art-Kategorien
```
POST   /admin/api/art-category                  → Neue Kategorie erstellen
POST   /admin/api/art-category/<id>/content     → Kategorie-Text aktualisieren
POST   /admin/api/art-category/<id>/image       → Kategorie-Bild aktualisieren
DELETE /admin/api/art-category/<id>             → Kategorie löschen
POST   /admin/api/art-category/<id>/images      → Bilder hochladen
DELETE /admin/api/art-image/<id>                → Bild löschen
```

### Seiten
```
POST   /admin/api/page/<id>/content   → Seiten-Text aktualisieren
POST   /admin/api/page/<id>/image     → Seiten-Bild aktualisieren
```
