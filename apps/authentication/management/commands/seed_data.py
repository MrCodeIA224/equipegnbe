"""
Commande de chargement de données de test GnExpress
Usage: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password


class Command(BaseCommand):
    help = 'Charge les données de test pour GnExpress'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Chargement des données de test GnExpress ===\n'))

        self._create_users()
        self._create_food_categories()
        self._create_restaurants()
        self._create_menu_items()
        self._create_marketplace_categories()
        self._create_shops()
        self._create_products()
        self._create_sample_orders()

        self.stdout.write(self.style.SUCCESS('\n=== Données de test chargées avec succès! ==='))
        self._print_credentials()

    def _create_users(self):
        self.stdout.write('Création des utilisateurs...')
        from apps.authentication.models import User, LivreurProfile, CoursierProfile

        users_data = [
            {
                'username': 'admin',
                'email': 'admin@gnexpress.gn',
                'first_name': 'Admin',
                'last_name': 'GnExpress',
                'role': 'ADMIN',
                'phone': '+224 620 000 001',
                'city': 'Conakry',
                'is_staff': True,
                'is_superuser': True,
                'is_verified': True,
            },
            {
                'username': 'mamadou.diallo',
                'email': 'mamadou@test.gn',
                'first_name': 'Mamadou',
                'last_name': 'Diallo',
                'role': 'CLIENT',
                'phone': '+224 622 111 001',
                'city': 'Conakry',
                'address': 'Quartier Ratoma, Conakry',
                'is_verified': True,
            },
            {
                'username': 'fatoumata.bah',
                'email': 'fatoumata@test.gn',
                'first_name': 'Fatoumata',
                'last_name': 'Bah',
                'role': 'CLIENT',
                'phone': '+224 622 111 002',
                'city': 'Conakry',
                'address': 'Kaloum, Conakry',
                'is_verified': True,
            },
            {
                'username': 'ibrahima.livreur',
                'email': 'ibrahima.livreur@test.gn',
                'first_name': 'Ibrahima',
                'last_name': 'Sow',
                'role': 'LIVREUR',
                'phone': '+224 628 222 001',
                'city': 'Conakry',
                'is_verified': True,
                'is_available': True,
            },
            {
                'username': 'alpha.livreur',
                'email': 'alpha.livreur@test.gn',
                'first_name': 'Alpha',
                'last_name': 'Camara',
                'role': 'LIVREUR',
                'phone': '+224 628 222 002',
                'city': 'Conakry',
                'is_verified': True,
                'is_available': True,
            },
            {
                'username': 'resto_madina',
                'email': 'resto.madina@test.gn',
                'first_name': 'Aissatou',
                'last_name': 'Barry',
                'role': 'RESTAURANT',
                'phone': '+224 631 333 001',
                'city': 'Conakry',
                'is_verified': True,
            },
            {
                'username': 'resto_kaloum',
                'email': 'resto.kaloum@test.gn',
                'first_name': 'Sekou',
                'last_name': 'Toure',
                'role': 'RESTAURANT',
                'phone': '+224 631 333 002',
                'city': 'Conakry',
                'is_verified': True,
            },
            {
                'username': 'boutique_mode',
                'email': 'boutique.mode@test.gn',
                'first_name': 'Mariama',
                'last_name': 'Conde',
                'role': 'BOUTIQUIERR',
                'phone': '+224 664 444 001',
                'city': 'Conakry',
                'is_verified': True,
            },
            {
                'username': 'boutique_tech',
                'email': 'boutique.tech@test.gn',
                'first_name': 'Oumar',
                'last_name': 'Keita',
                'role': 'BOUTIQUIERR',
                'phone': '+224 664 444 002',
                'city': 'Conakry',
                'is_verified': True,
            },
            {
                'username': 'kouyate.coursier',
                'email': 'kouyate.coursier@test.gn',
                'first_name': 'Kouyaté',
                'last_name': 'Lansana',
                'role': 'COURSIER',
                'phone': '+224 655 555 001',
                'city': 'Conakry',
                'is_verified': True,
                'is_available': True,
            },
            {
                'username': 'balde.coursier',
                'email': 'balde.coursier@test.gn',
                'first_name': 'Baldé',
                'last_name': 'Thierno',
                'role': 'COURSIER',
                'phone': '+224 655 555 002',
                'city': 'Conakry',
                'is_verified': True,
                'is_available': True,
            },
        ]

        self.users = {}
        password = make_password('GnExpress@2024')

        for data in users_data:
            username = data['username']
            user, created = User.objects.get_or_create(
                username=username,
                defaults={**data, 'password': password}
            )
            if not created:
                self.stdout.write(f'  Utilisateur déjà existant: {username}')
            else:
                self.stdout.write(f'  + Créé: {user.get_full_name()} ({user.get_role_display()})')
            self.users[username] = user

        # Profils livreurs
        for username in ['ibrahima.livreur', 'alpha.livreur']:
            user = self.users[username]
            LivreurProfile.objects.get_or_create(
                user=user,
                defaults={
                    'vehicle_type': 'MOTO',
                    'zone': 'Conakry',
                    'rating': 4.80,
                }
            )

        # Profils coursiers
        for username in ['kouyate.coursier', 'balde.coursier']:
            user = self.users[username]
            CoursierProfile.objects.get_or_create(
                user=user,
                defaults={
                    'preferred_markets': 'Marché Madina, Marché Cosa',
                    'zone': 'Conakry',
                    'rating': 4.70,
                }
            )

        self.stdout.write(self.style.SUCCESS(f'  {len(users_data)} utilisateurs traités.'))

    def _create_food_categories(self):
        self.stdout.write('Création des catégories de plats...')
        from apps.delivery.models import FoodCategory

        categories = [
            {'name': 'Riz et plats locaux', 'icon': '🍚'},
            {'name': 'Grillades', 'icon': '🍖'},
            {'name': 'Soupes et sauces', 'icon': '🍲'},
            {'name': 'Pain et sandwichs', 'icon': '🥪'},
            {'name': 'Boissons', 'icon': '🥤'},
            {'name': 'Desserts', 'icon': '🍰'},
            {'name': 'Petit-déjeuner', 'icon': '🥐'},
            {'name': 'Fruits', 'icon': '🍉'},
        ]

        self.food_categories = {}
        for cat_data in categories:
            cat, _ = FoodCategory.objects.using('delivery_db').get_or_create(**cat_data)
            self.food_categories[cat.name] = cat

        self.stdout.write(self.style.SUCCESS(f'  {len(categories)} catégories créées.'))

    def _create_restaurants(self):
        self.stdout.write('Création des restaurants...')
        from apps.delivery.models import Restaurant

        restaurants_data = [
            {
                'owner_id': self.users['resto_madina'].id,
                'name': 'Restaurant Chez Aissatou',
                'description': 'Cuisine guinéenne authentique - Riz gras, Poulet yassa, Foufou',
                'address': 'Avenue de la République, Madina',
                'city': 'Conakry',
                'phone': '+224 631 333 001',
                'is_open': True,
                'delivery_time_min': 20,
                'delivery_time_max': 40,
                'min_order': 20000,
                'delivery_fee': 5000,
                'rating': 4.8,
            },
            {
                'owner_id': self.users['resto_kaloum'].id,
                'name': 'Fast Food Kaloum',
                'description': 'Burgers, sandwichs et grillades - Livraison rapide dans Kaloum',
                'address': 'Rue KA-030, Kaloum',
                'city': 'Conakry',
                'phone': '+224 631 333 002',
                'is_open': True,
                'delivery_time_min': 15,
                'delivery_time_max': 30,
                'min_order': 15000,
                'delivery_fee': 3000,
                'rating': 4.5,
            },
            {
                'owner_id': self.users['resto_madina'].id,
                'name': 'Brochettes du Bord de Mer',
                'description': 'Grillades de poisson frais et brochettes - Spécialité de la côte',
                'address': 'Bord de mer, Dixinn',
                'city': 'Conakry',
                'phone': '+224 631 333 003',
                'is_open': True,
                'delivery_time_min': 25,
                'delivery_time_max': 45,
                'min_order': 25000,
                'delivery_fee': 5000,
                'rating': 4.7,
            },
        ]

        self.restaurants = {}
        for data in restaurants_data:
            rest, created = Restaurant.objects.using('delivery_db').get_or_create(
                name=data['name'],
                defaults=data
            )
            self.restaurants[rest.name] = rest
            if created:
                self.stdout.write(f'  + Restaurant: {rest.name}')

        self.stdout.write(self.style.SUCCESS(f'  {len(restaurants_data)} restaurants traités.'))

    def _create_menu_items(self):
        self.stdout.write('Création des menus...')
        from apps.delivery.models import MenuItem

        menu_data = {
            'Restaurant Chez Aissatou': [
                ('Riz et plats locaux', [
                    ('Riz gras au poulet', 'Riz cuit dans une sauce tomate avec poulet grillé', 25000, True),
                    ('Foufou sauce arachide', 'Foufou de manioc avec sauce arachide traditionnelle', 20000, True),
                    ('Riz sauce feuille', 'Riz blanc avec sauce feuilles de manioc', 22000, False),
                    ('Tô sauce gombo', 'Tô de maïs avec sauce gombo', 18000, False),
                ]),
                ('Boissons', [
                    ('Jus de gingembre', 'Jus de gingembre frais maison', 5000, True),
                    ('Jus de bissap', 'Jus d\'hibiscus sucré', 4000, False),
                    ('Eau minérale', 'Bouteille 1.5L', 3000, False),
                ]),
            ],
            'Fast Food Kaloum': [
                ('Pain et sandwichs', [
                    ('Burger Kaloum', 'Steak, fromage, laitue, tomate, sauce maison', 22000, True),
                    ('Sandwich poulet', 'Poulet grillé, légumes, sauce piquante', 18000, True),
                    ('Hot-dog', 'Saucisse grillée, moutarde, ketchup', 12000, False),
                ]),
                ('Grillades', [
                    ('Poulet grillé 1/2', 'Demi-poulet mariné aux épices', 30000, True),
                    ('Brochettes de bœuf (5 pcs)', '5 brochettes avec pain et sauce', 20000, True),
                ]),
                ('Boissons', [
                    ('Coca-Cola 33cl', '', 3000, False),
                    ('Jus d\'orange pressé', 'Orange pressée fraîche', 5000, True),
                ]),
            ],
            'Brochettes du Bord de Mer': [
                ('Grillades', [
                    ('Poisson barracuda grillé', 'Barracuda entier grillé avec légumes', 35000, True),
                    ('Crevettes grillées (10 pcs)', 'Crevettes marinées au citron et épices', 40000, True),
                    ('Brochettes de poulet (6 pcs)', '6 brochettes avec sauce piquante', 25000, False),
                    ('Capitaine grillé', 'Poisson capitaine grillé tradition', 45000, True),
                ]),
                ('Soupes et sauces', [
                    ('Soupe de poisson', 'Soupe épicée aux fruits de mer', 18000, False),
                ]),
                ('Boissons', [
                    ('Jus de coco', 'Noix de coco fraîche', 3000, True),
                ]),
            ],
        }

        total = 0
        for resto_name, categories in menu_data.items():
            resto = self.restaurants.get(resto_name)
            if not resto:
                continue
            for cat_name, items in categories:
                cat = self.food_categories.get(cat_name)
                for item_name, desc, price, popular in items:
                    obj, created = MenuItem.objects.using('delivery_db').get_or_create(
                        restaurant=resto,
                        name=item_name,
                        defaults={
                            'description': desc,
                            'price': price,
                            'category': cat,
                            'is_popular': popular,
                            'is_available': True,
                        }
                    )
                    if created:
                        total += 1

        self.stdout.write(self.style.SUCCESS(f'  {total} plats créés.'))

    def _create_marketplace_categories(self):
        self.stdout.write('Création des catégories marketplace...')
        from apps.marketplace.models import Category

        categories = [
            {'name': 'Mode & Vêtements', 'slug': 'mode-vetements', 'icon': '👗', 'order': 1},
            {'name': 'Électronique & Téléphones', 'slug': 'electronique-telephones', 'icon': '📱', 'order': 2},
            {'name': 'Maison & Cuisine', 'slug': 'maison-cuisine', 'icon': '🏠', 'order': 3},
            {'name': 'Beauté & Cosmétiques', 'slug': 'beaute-cosmetiques', 'icon': '💄', 'order': 4},
            {'name': 'Alimentation & Épicerie', 'slug': 'alimentation-epicerie', 'icon': '🛒', 'order': 5},
            {'name': 'Agriculture & Jardinage', 'slug': 'agriculture-jardinage', 'icon': '🌱', 'order': 6},
            {'name': 'Automobile & Moto', 'slug': 'automobile-moto', 'icon': '🚗', 'order': 7},
            {'name': 'Sport & Loisirs', 'slug': 'sport-loisirs', 'icon': '⚽', 'order': 8},
            {'name': 'Livres & Fournitures', 'slug': 'livres-fournitures', 'icon': '📚', 'order': 9},
            {'name': 'Artisanat Guinéen', 'slug': 'artisanat-guineen', 'icon': '🎨', 'order': 10},
        ]

        self.mp_categories = {}
        for data in categories:
            cat, created = Category.objects.using('marketplace_db').get_or_create(
                slug=data['slug'], defaults=data
            )
            self.mp_categories[cat.slug] = cat
            if created:
                self.stdout.write(f'  + Catégorie: {cat.name}')

        self.stdout.write(self.style.SUCCESS(f'  {len(categories)} catégories marketplace créées.'))

    def _create_shops(self):
        self.stdout.write('Création des boutiques...')
        from apps.marketplace.models import Shop

        shops_data = [
            {
                'owner_id': self.users['boutique_mode'].id,
                'name': 'Mariama Mode',
                'description': 'Vêtements et accessoires tendance pour femmes et hommes. Mode africaine et internationale.',
                'category': self.mp_categories['mode-vetements'],
                'address': 'Marché Madina, Stand 45',
                'city': 'Conakry',
                'phone': '+224 664 444 001',
                'whatsapp': '+224664444001',
                'is_active': True,
                'has_delivery': True,
                'delivery_fee': 5000,
                'rating': 4.7,
            },
            {
                'owner_id': self.users['boutique_tech'].id,
                'name': 'Oumar Tech Shop',
                'description': 'Smartphones, accessoires, tablettes et réparation. Produits garantis neufs et occasion.',
                'category': self.mp_categories['electronique-telephones'],
                'address': 'Quartier Kaloum, Boulevard Diallo',
                'city': 'Conakry',
                'phone': '+224 664 444 002',
                'whatsapp': '+224664444002',
                'is_active': True,
                'has_delivery': True,
                'delivery_fee': 3000,
                'rating': 4.9,
            },
            {
                'owner_id': self.users['boutique_mode'].id,
                'name': 'Artisanat Guinéen Premium',
                'description': 'Bogolan, sculpture, bijoux et objets d\'art guinéens. Authenticité garantie.',
                'category': self.mp_categories['artisanat-guineen'],
                'address': 'Cité des Artistes, Ratoma',
                'city': 'Conakry',
                'phone': '+224 664 444 003',
                'is_active': True,
                'has_delivery': False,
                'delivery_fee': 0,
                'rating': 4.6,
            },
        ]

        self.shops = {}
        for data in shops_data:
            shop, created = Shop.objects.using('marketplace_db').get_or_create(
                name=data['name'],
                defaults=data
            )
            self.shops[shop.name] = shop
            if created:
                self.stdout.write(f'  + Boutique: {shop.name}')

        self.stdout.write(self.style.SUCCESS(f'  {len(shops_data)} boutiques créées.'))

    def _create_products(self):
        self.stdout.write('Création des produits...')
        from apps.marketplace.models import Product

        products_data = {
            'Mariama Mode': [
                ('Boubou africain brodé', 'Boubou traditionnel guinéen brodé à la main, disponible en plusieurs couleurs', 150000, 10, 'mode-vetements', 'NEW', True),
                ('Robe wax imprimé', 'Robe élégante en tissu wax africain, coupe moderne', 85000, 15, 'mode-vetements', 'NEW', True),
                ('Chemise bâtik homme', 'Chemise en tissu bâtik, idéale pour les occasions', 65000, 20, 'mode-vetements', 'NEW', False),
                ('Foulard soie', 'Foulard en soie naturelle, motifs africains', 35000, 30, 'mode-vetements', 'NEW', False),
                ('Sac cuir artisanal', 'Sac à main en cuir véritable fait main', 120000, 5, 'mode-vetements', 'NEW', True),
            ],
            'Oumar Tech Shop': [
                ('iPhone 13 - 128GB', 'iPhone 13 reconditionné, excellent état, batterie 90%, débloqué tous opérateurs', 4500000, 3, 'electronique-telephones', 'USED_GOOD', True),
                ('Samsung Galaxy A54', 'Samsung Galaxy A54 5G neuf sous emballage, garantie 1 an', 2800000, 5, 'electronique-telephones', 'NEW', True),
                ('Chargeur rapide 65W', 'Chargeur USB-C 65W compatible Samsung, Xiaomi, etc.', 75000, 20, 'electronique-telephones', 'NEW', False),
                ('Écouteurs Bluetooth', 'Écouteurs sans fil TWS, 8h d\'autonomie, résistant à la sueur', 120000, 10, 'electronique-telephones', 'NEW', False),
                ('Coque protection iPhone', 'Coque antichoc pour iPhone 13/14, plusieurs coloris', 25000, 50, 'electronique-telephones', 'NEW', False),
                ('Tablette Xiaomi Pad 6', 'Tablette 11 pouces, 256GB, idéale pour les étudiants', 1800000, 4, 'electronique-telephones', 'NEW', True),
            ],
            'Artisanat Guinéen Premium': [
                ('Masque traditionnel Baga', 'Masque sculpté à la main par artisan baga, bois noble', 350000, 3, 'artisanat-guineen', 'NEW', True),
                ('Bijoux en bronze Malinké', 'Collier et bracelets en bronze, style malinké traditionnel', 180000, 8, 'artisanat-guineen', 'NEW', True),
                ('Tableau bogolan', 'Peinture sur tissu bogolan, scène de vie guinéenne, 60x80cm', 220000, 5, 'artisanat-guineen', 'NEW', False),
                ('Djembé artisanal', 'Djembé fait main en bois de tamarinier, peau de chèvre naturelle', 450000, 2, 'artisanat-guineen', 'NEW', True),
                ('Panier tressé Peul', 'Panier traditionnel tressé à la main par artisanes peules', 55000, 15, 'artisanat-guineen', 'NEW', False),
            ],
        }

        total = 0
        for shop_name, products in products_data.items():
            shop = self.shops.get(shop_name)
            if not shop:
                continue
            for name, desc, price, stock, cat_slug, condition, featured in products:
                cat = self.mp_categories.get(cat_slug)
                product, created = Product.objects.using('marketplace_db').get_or_create(
                    shop=shop,
                    name=name,
                    defaults={
                        'description': desc,
                        'price': price,
                        'stock': stock,
                        'category': cat,
                        'condition': condition,
                        'is_featured': featured,
                        'is_available': True,
                        'has_delivery': shop.has_delivery,
                    }
                )
                if created:
                    total += 1

        self.stdout.write(self.style.SUCCESS(f'  {total} produits créés.'))

    def _create_sample_orders(self):
        self.stdout.write('Création de quelques commandes de démonstration...')

        # Commande livraison
        from apps.delivery.models import DeliveryOrder, DeliveryOrderItem, MenuItem
        client = self.users['mamadou.diallo']
        resto = list(self.restaurants.values())[0]
        menu_items = list(MenuItem.objects.using('delivery_db').filter(restaurant=resto)[:2])

        if menu_items:
            order, created = DeliveryOrder.objects.using('delivery_db').get_or_create(
                client_id=client.id,
                restaurant=resto,
                delivery_address='Quartier Ratoma, Conakry',
                defaults={
                    'status': 'DELIVERED',
                    'delivery_fee': resto.delivery_fee,
                    'items_total': sum(i.price for i in menu_items),
                    'total_price': sum(i.price for i in menu_items) + resto.delivery_fee,
                    'livreur_id': self.users['ibrahima.livreur'].id,
                }
            )
            if created:
                for mi in menu_items:
                    DeliveryOrderItem.objects.using('delivery_db').create(
                        order=order, menu_item=mi, quantity=1, unit_price=mi.price
                    )
                self.stdout.write(f'  + Commande livraison #{order.id} (DELIVERED)')

        # Demande de marché
        from apps.market.models import MarketRequest, MarketItem
        market_req, created = MarketRequest.objects.using('market_db').get_or_create(
            client_id=client.id,
            market_name='Marché Madina',
            defaults={
                'title': 'Courses de la semaine',
                'status': 'COMPLETED',
                'delivery_address': 'Quartier Ratoma, Conakry',
                'budget': 200000,
                'coursier_id': self.users['kouyate.coursier'].id,
                'livreur_id': self.users['ibrahima.livreur'].id,
                'actual_total': 185000,
            }
        )
        if created:
            for item_name, qty in [('Riz 25kg', '1 sac'), ('Huile de palme', '2 litres'), ('Oignons', '2 kg')]:
                MarketItem.objects.using('market_db').create(
                    request=market_req, name=item_name, quantity=qty, is_found=True
                )
            self.stdout.write(f'  + Demande marché #{market_req.id} (COMPLETED)')

        self.stdout.write(self.style.SUCCESS('  Commandes de démo créées.'))

    def _print_credentials(self):
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('ACCÈS DE TEST GNEXPRESS'))
        self.stdout.write('='*60)
        self.stdout.write('')
        credentials = [
            ('ADMIN', 'admin@gnexpress.gn', 'GnExpress@2024', 'Accès total'),
            ('CLIENT', 'mamadou@test.gn', 'GnExpress@2024', 'Passer des commandes'),
            ('CLIENT 2', 'fatoumata@test.gn', 'GnExpress@2024', 'Passer des commandes'),
            ('LIVREUR', 'ibrahima.livreur@test.gn', 'GnExpress@2024', 'Gérer les livraisons'),
            ('LIVREUR 2', 'alpha.livreur@test.gn', 'GnExpress@2024', 'Gérer les livraisons'),
            ('RESTAURANT', 'resto.madina@test.gn', 'GnExpress@2024', 'Gérer restaurants & menus'),
            ('RESTAURANT 2', 'resto.kaloum@test.gn', 'GnExpress@2024', 'Gérer restaurants & menus'),
            ('BOUTIQUIERR', 'boutique.mode@test.gn', 'GnExpress@2024', 'Gérer boutiques & produits'),
            ('BOUTIQUIERR 2', 'boutique.tech@test.gn', 'GnExpress@2024', 'Gérer boutiques & produits'),
            ('COURSIER', 'kouyate.coursier@test.gn', 'GnExpress@2024', 'Missions de courses'),
            ('COURSIER 2', 'balde.coursier@test.gn', 'GnExpress@2024', 'Missions de courses'),
        ]
        for role, email, pwd, desc in credentials:
            self.stdout.write(f'  {role:<15} | {email:<35} | {pwd} | {desc}')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('  Interface admin Django: http://localhost:8000/admin/'))
        self.stdout.write(self.style.WARNING('  API:                   http://localhost:8000/api/v1/'))
        self.stdout.write('='*60)
