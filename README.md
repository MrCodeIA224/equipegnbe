# GnExpress — Backend API

API REST de la plateforme GnExpress, la super-app guinéenne regroupant livraison de repas, courses au marché et boutiques numériques.

## Stack technique

- **Python** 3.12
- **Django** 4.2 + **Django REST Framework** 3.15
- **Authentification** : JWT via `djangorestframework-simplejwt`
- **Base de données** : SQLite (développement) / PostgreSQL (production)
- **Autres** : django-filter, django-cors-headers, Pillow, python-decouple

## Architecture

Le projet suit une architecture **multi-bases de données** : chaque module métier dispose de sa propre base SQLite en développement, simulant une séparation microservices.

```
backend/
├── apps/
│   ├── authentication/   → Utilisateurs, JWT, rôles          (db_auth.sqlite3)
│   ├── delivery/         → Restaurants, menus, livraisons    (db_delivery.sqlite3)
│   ├── market/           → Courses au marché, coursiers      (db_market.sqlite3)
│   └── marketplace/      → Boutiques, produits, commandes    (db_marketplace.sqlite3)
├── config/
│   ├── settings/
│   │   ├── base.py           → Configuration commune
│   │   ├── development.py    → Surcharges développement
│   │   └── production.py     → Surcharges production
│   ├── database_router.py    → Routage multi-bases
│   └── urls.py
├── media/                → Fichiers uploadés
├── manage.py
└── requirements.txt
```

## Rôles utilisateurs

| Rôle | Description |
|------|-------------|
| `ADMIN` | Accès complet à toute la plateforme |
| `CLIENT` | Passe des commandes |
| `LIVREUR` | Prend en charge les livraisons |
| `RESTAURANT` | Gère son restaurant et ses commandes |
| `BOUTIQUIERR` | Gère sa boutique et ses produits |
| `COURSIER` | Effectue les courses au marché |

## Endpoints API

```
/api/v1/auth/           → Authentification, gestion des utilisateurs
/api/v1/delivery/       → Restaurants, menus, commandes de livraison
/api/v1/market/         → Demandes de courses, offres coursiers
/api/v1/marketplace/    → Boutiques, produits, commandes boutique

/admin/                 → Interface d'administration Django
```

---

## Démarrage en développement

### 1. Prérequis

- Python 3.10+
- pip

### 2. Cloner et installer les dépendances

```bash
git clone <url-du-repo>
cd backend

python3 -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### 3. Appliquer les migrations

Les bases SQLite sont créées automatiquement à la première migration.

```bash
python manage.py migrate --database=default
python manage.py migrate --database=delivery_db
python manage.py migrate --database=market_db
python manage.py migrate --database=marketplace_db
```

### 4. Créer le super-utilisateur

Un script prêt à l'emploi est fourni (identifiants déjà renseignés) :

```bash
python create_superuser.py
```

### 5. Injecter les données de test

```bash
python manage.py seed_data
```

Cela crée des restaurants, produits, utilisateurs de test, etc.

### 6. Lancer le serveur

```bash
python manage.py runserver
```

L'API est accessible sur **http://localhost:8000**

---

## Comptes de test

Mot de passe universel : `GnExpress@2024`

| Email | Rôle |
|-------|------|
| admin@gnexpress.gn | ADMIN |
| mamadou@test.gn | CLIENT |
| ibrahima.livreur@test.gn | LIVREUR |
| resto.madina@test.gn | RESTAURANT |
| boutique.mode@test.gn | BOUTIQUIERR |
| kouyate.coursier@test.gn | COURSIER |

---

## Variables d'environnement

Créer un fichier `.env` à la racine du dossier `backend/` (copier `.env.example` si disponible) :

```env
SECRET_KEY=votre-clé-secrète-django
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000

# JWT
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# Production uniquement
DATABASE_URL=postgres://user:password@host:5432/dbname
```

En développement, les valeurs par défaut dans `config/settings/development.py` suffisent.

---

## Démarrage en production

```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

Définir `DJANGO_SETTINGS_MODULE=config.settings.production` dans l'environnement.
