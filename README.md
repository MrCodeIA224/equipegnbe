# GnExpress — Backend API

API REST de la plateforme GnExpress, la super-app guinéenne regroupant livraison de repas, courses au marché, boutiques numériques, géolocalisation, notifications et messagerie.

## Stack technique

- **Python** 3.12+ (testé avec 3.14)
- **Django** 6.0 + **Django REST Framework** 3.17
- **Authentification** : JWT via `djangorestframework-simplejwt` (+ blacklist des refresh tokens)
- **Base de données** : SQLite (développement) / PostgreSQL (production, via `psycopg`)
- **Autres** : django-filter, django-cors-headers, Pillow, python-decouple, gunicorn
- **Tests** : pytest + pytest-django

## Architecture

Le projet suit une architecture **multi-bases de données** : chaque module métier dispose de sa propre base SQLite en développement, simulant une séparation microservices. Aucune clé étrangère cross-base n'est possible : les références entre services (ex. une commande de livraison référencée par une notification) passent par un couple `(order_type, order_id)` en entier brut, résolu dynamiquement — voir `apps/authentication/services.py` et `config/database_router.py`.

```
equipegnbe/
├── apps/
│   ├── authentication/   → Utilisateurs, JWT, rôles, adresses, codes promo,   (db_auth.sqlite3)
│   │                        position livreur, notifications, chat, OTP
│   ├── common/            → Simulateurs de paiement Mobile Money (pas une app Django)
│   ├── delivery/          → Restaurants, menus, livraisons                    (db_delivery.sqlite3)
│   ├── market/             → Courses au marché, coursiers                     (db_market.sqlite3)
│   └── marketplace/       → Boutiques, produits, commandes                    (db_marketplace.sqlite3)
├── config/
│   ├── settings/
│   │   ├── base.py           → Configuration commune
│   │   ├── development.py    → Surcharges développement
│   │   └── production.py     → Surcharges production
│   ├── constants.py          → Liste des villes de Guinée
│   ├── database_router.py    → Routage multi-bases
│   └── urls.py
├── media/                → Fichiers uploadés
├── conftest.py            → Fixtures pytest partagées (utilisateurs de test par rôle)
├── manage.py
├── requirements.txt
└── requirements-dev.txt   → requirements.txt + pytest
```

## Rôles utilisateurs

| Rôle | Description |
|------|-------------|
| `ADMIN` | Accès complet à toute la plateforme |
| `CLIENT` | Passe des commandes (livraison, courses, boutiques) |
| `LIVREUR` | Prend en charge les livraisons et diffuse sa position GPS |
| `RESTAURANT` | Gère son restaurant, son menu et ses commandes |
| `BOUTIQUIERR` | Gère sa boutique et ses produits |
| `COURSIER` | Effectue les courses au marché pour le compte des clients |

## Fonctionnalités

- **Livraison** : restaurants, menus, panier, suivi de commande, annulation/réassignation livreur
- **Mon Marché** : demande de courses, offres des coursiers, livraison finale par un livreur
- **Boutiques (marketplace)** : catalogue produits, commandes avec livraison ou retrait
- **Paiement Mobile Money simulé** (Orange Money / MTN MoMo) avec code OTP de confirmation, ou paiement à la livraison
- **Codes promo** : validation au checkout, gestion admin (création, activation/désactivation, historique d'utilisation)
- **Adresses enregistrées** avec coordonnées GPS optionnelles
- **Géolocalisation** : placement de repère GPS sur restaurants/boutiques, suivi en direct de la position du livreur pendant une livraison
- **Notifications in-app** : créées automatiquement à chaque étape clé d'une commande
- **Chat par commande** entre le client et le livreur/coursier qui lui est assigné
- **Recommande rapide** : aucune route dédiée, s'appuie sur les endpoints de lecture existants (restaurant/menu, position, etc.)
- **Mot de passe oublié** et **changement d'email** par code OTP (simulé — aucun email n'est réellement envoyé, le code est retourné dans la réponse API pour la démo)
- **Intégrité référentielle** : commande `check_referential_integrity` pour auditer les références cross-service orphelines

## Endpoints API

```
/api/v1/auth/
  login/, register/, token/refresh/, logout/
  me/, me/change-password/
  me/email-change/request/, me/email-change/confirm/
  password-reset/request/, password-reset/confirm/
  addresses/                          (CRUD adresses du client connecté)
  promo-codes/validate/
  admin/promo-codes/, admin/promo-redemptions/, admin/users/
  livreurs/available/, livreurs/position/
  notifications/ (+ unread_count/, mark_read/, mark_all_read/)
  conversations/open/, conversations/<id>/messages/

/api/v1/delivery/
  restaurants/ (+ menu/, menu-items/, toggle_open/)
  orders/ (+ update_status/, assign_livreur/, cancel_delivery/, livreur-position/,
            payment/initiate/, payment/confirm/, available/)
  categories/
  admin/stats/

/api/v1/market/
  requests/ (+ make_offer/, accept_offer/, update_status/, assign_livreur/,
              update_items/, livreur-position/, open_requests/, need_delivery/)
  admin/stats/

/api/v1/marketplace/
  categories/, products/ (+ reviews/, featured/)
  shops/ (+ products/)
  orders/ (+ update_status/, assign_livreur/, cancel_delivery/, livreur-position/,
            payment/initiate/, payment/confirm/, available_for_delivery/)
  admin/stats/

/admin/                 → Interface d'administration Django
```

---

## Démarrage en développement

### 1. Prérequis

- Python 3.12+
- pip

### 2. Cloner et installer les dépendances

```bash
git clone <url-du-repo> equipegnbe
cd equipegnbe

python3 -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate           # Windows

pip install -r requirements.txt
# Pour lancer les tests, installer aussi les dépendances de dev :
pip install -r requirements-dev.txt
```

### 3. Variables d'environnement

Copier `.env.example` vers `.env` à la racine du projet :

```bash
cp .env.example .env
```

Les valeurs par défaut suffisent en développement (SQLite, `DEBUG=True`). Générer une `SECRET_KEY` dédiée est recommandé même en local :

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4. Appliquer les migrations

Les 4 bases SQLite sont créées automatiquement à la première migration. **Chacune doit recevoir toutes les migrations** (le routeur multi-bases fait qu'un modèle d'une app peut avoir des tables dans plusieurs bases) :

```bash
python manage.py migrate --database=default
python manage.py migrate --database=delivery_db
python manage.py migrate --database=market_db
python manage.py migrate --database=marketplace_db
```

À refaire après chaque `git pull` qui ajoute de nouvelles migrations.

### 5. Créer le super-utilisateur

Un script prêt à l'emploi est fourni (identifiants déjà renseignés) :

```bash
python create_superuser.py
```

Identifiants créés : `admin@gnexpress.gn` / `GnExpress@2024`

### 6. Injecter les données de test

```bash
python manage.py seed_data
```

Cela crée des restaurants, boutiques, produits et un jeu d'utilisateurs de test pour chaque rôle (voir table ci-dessous).

### 7. Lancer le serveur

```bash
python manage.py runserver
```

L'API est accessible sur **http://localhost:8000**

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Les tests couvrent l'ensemble des apps (authentification, adresses, codes promo, position livreur, notifications, chat, intégrité référentielle, OTP, flux de commande delivery/market/marketplace, paiement simulé). Ils tournent sur les 4 bases SQLite de test créées automatiquement par pytest-django.

## Commandes utiles

```bash
# Vérifier qu'aucune référence cross-service (notification, chat, position livreur...) n'est orpheline
python manage.py check_referential_integrity

# Vérifier que le projet Django est correctement configuré
python manage.py check
```

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

`seed_data` crée également un second compte pour chaque rôle métier (ex. `fatoumata@test.gn`, `alpha.livreur@test.gn`, `resto.kaloum@test.gn`, `boutique.tech@test.gn`, `balde.coursier@test.gn`) utile pour tester les interactions entre deux comptes du même rôle.

---

## Variables d'environnement

Voir `.env.example` pour la liste complète et commentée. Résumé :

```env
DJANGO_ENV=development
SECRET_KEY=votre-clé-secrète-django
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Bases de données (SQLite par défaut, PostgreSQL en indiquant une URL postgresql://... en prod)
DEFAULT_DB_URL=sqlite:///db_auth.sqlite3
DELIVERY_DB_URL=sqlite:///db_delivery.sqlite3
MARKET_DB_URL=sqlite:///db_market.sqlite3
MARKETPLACE_DB_URL=sqlite:///db_marketplace.sqlite3

# JWT
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
```

Les blocs `MEDIA_ROOT`/`MEDIA_URL` et `EMAIL_*` de `.env.example` sont prévus pour une évolution future : le stockage de fichiers et l'envoi d'email réel via SMTP ne sont pas branchés aujourd'hui — le paiement Mobile Money et les codes OTP (mot de passe oublié, changement d'email) sont **simulés** et retournent leur code directement dans la réponse API plutôt que de l'envoyer réellement.

---

## Démarrage en production

```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --database=default
python manage.py migrate --database=delivery_db
python manage.py migrate --database=market_db
python manage.py migrate --database=marketplace_db
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

Définir `DJANGO_ENV=production` dans l'environnement (voir `config/settings/production.py`).
