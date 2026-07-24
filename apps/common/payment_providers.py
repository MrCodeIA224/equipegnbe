"""
Simulateurs de paiement Mobile Money (Orange Money, MTN MoMo).

Ce module n'est PAS une app Django : pas de modèles, pas de migrations, pas
d'entrée dans INSTALLED_APPS ni dans database_router. C'est de la pure logique
métier, importée par les modèles *Payment de chaque app (delivery, marketplace).

Aucun identifiant API réel n'est disponible pour Orange Money / MTN MoMo dans ce
projet. Ces providers simulent le round-trip USSD habituel (initiation -> code
reçu par SMS -> confirmation) sans appel réseau réel. Pour brancher les vraies
API plus tard, il suffit de remplacer le corps de `initiate`/`confirm` dans les
classes ci-dessous - le reste du code (modèles, vues, frontend) n'a pas à changer.
"""
import random
import uuid
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class InitiateResult:
    transaction_reference: str
    otp_code: str


@dataclass
class ConfirmResult:
    success: bool


class BaseMobileMoneyProvider:
    """Interface commune aux providers Mobile Money simulés."""

    display_name = "Mobile Money"

    def initiate(self, phone: str, amount: Decimal) -> InitiateResult:
        """Démarre une transaction : génère une référence + un code OTP simulé
        (l'équivalent du code reçu par SMS lors d'un vrai paiement)."""
        reference = str(uuid.uuid4())
        otp = f"{random.randint(0, 9999):04d}"
        return InitiateResult(transaction_reference=reference, otp_code=otp)

    def confirm(self, otp_code: str, expected_otp: str) -> ConfirmResult:
        """Confirme la transaction en comparant le code saisi au code envoyé."""
        return ConfirmResult(success=(otp_code == expected_otp))


class OrangeMoneyProvider(BaseMobileMoneyProvider):
    display_name = "Orange Money"


class MTNMoMoProvider(BaseMobileMoneyProvider):
    display_name = "MTN Mobile Money"


PROVIDER_REGISTRY = {
    'ORANGE_MONEY': OrangeMoneyProvider(),
    'MTN_MOMO': MTNMoMoProvider(),
}


def get_provider(method: str) -> BaseMobileMoneyProvider:
    provider = PROVIDER_REGISTRY.get(method)
    if provider is None:
        raise ValueError(f"Provider de paiement inconnu: {method}")
    return provider
