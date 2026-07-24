"""
Constantes partagées entre toutes les apps GnExpress.
Ce module n'est pas une app Django : il n'a pas de modèles ni de migrations,
il peut donc être importé librement depuis authentication/delivery/market/marketplace
sans jamais poser de problème de routage multi-bases.
"""

# Valeur == libellé (le français déjà utilisé partout dans le projet), pour que
# les champs `city` existants (default='Conakry') restent valides sans backfill.
GUINEA_CITIES = [
    ('Conakry', 'Conakry'),
    ('Kindia', 'Kindia'),
    ('Kankan', 'Kankan'),
    ('Labé', 'Labé'),
    ("N'Zérékoré", "N'Zérékoré"),
    ('Boké', 'Boké'),
    ('Mamou', 'Mamou'),
    ('Faranah', 'Faranah'),
    ('Kissidougou', 'Kissidougou'),
    ('Guéckédou', 'Guéckédou'),
]
