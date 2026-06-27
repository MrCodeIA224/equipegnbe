"""
Router de bases de données - Architecture microservices GnExpress
Chaque service a sa propre base de données isolée.
La communication inter-services se fait via la couche service (ORM cross-db).
"""


class ServiceDatabaseRouter:
    """
    Dirige les requêtes ORM vers la bonne base de données selon l'app Django.

    - authentication  → default (db_auth)
    - delivery        → delivery_db
    - market          → market_db
    - marketplace     → marketplace_db
    """

    APP_DB_MAP = {
        'authentication': 'default',
        'token_blacklist': 'default',
        'admin': 'default',
        'auth': 'default',
        'contenttypes': 'default',
        'sessions': 'default',
        'delivery': 'delivery_db',
        'market': 'market_db',
        'marketplace': 'marketplace_db',
    }

    def db_for_read(self, model, **hints):
        return self.APP_DB_MAP.get(model._meta.app_label, 'default')

    def db_for_write(self, model, **hints):
        return self.APP_DB_MAP.get(model._meta.app_label, 'default')

    def allow_relation(self, obj1, obj2, **hints):
        """
        Autorise les relations entre objets du même service.
        Les relations cross-services doivent passer par des IDs (pas FK directes).
        """
        db1 = self.APP_DB_MAP.get(obj1._meta.app_label, 'default')
        db2 = self.APP_DB_MAP.get(obj2._meta.app_label, 'default')
        return db1 == db2

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        target_db = self.APP_DB_MAP.get(app_label, 'default')
        return target_db == db
