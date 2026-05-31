from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import TermsOfService


DEFAULT_TERMS_CONTENT = """
<h5>1. Objet</h5>
<p>Les présentes conditions générales d'utilisation (CGU) ont pour objet de définir les modalités dans lesquelles TontineApp met à disposition des utilisateurs son application de gestion de tontines.</p>

<h5>2. Acceptation des conditions</h5>
<p>L'utilisation de TontineApp implique l'acceptation pleine et entière des présentes conditions générales. L'utilisateur s'engage à les respecter sans réserve.</p>

<h5>3. Description du service</h5>
<p>TontineApp permet de :</p>
<ul>
    <li>Créer et gérer des groupes de tontine</li>
    <li>Organiser des cotisations périodiques</li>
    <li>Gérer les tirages au sort pour l'attribution des gains</li>
    <li>Suivre l'historique des contributions</li>
</ul>

<h5>4. Obligations de l'utilisateur</h5>
<p>L'utilisateur s'engage à :</p>
<ul>
    <li>Fournir des informations exactes et à jour lors de son inscription</li>
    <li>Respecter les échéances de cotisations convenues</li>
    <li>Ne pas utiliser le service à des fins illicites</li>
    <li>Maintenir la confidentialité de ses identifiants de connexion</li>
</ul>

<h5>5. Responsabilité</h5>
<p>TontineApp agit uniquement en tant qu'outil de gestion. Les transactions financières entre membres relèvent de la responsabilité exclusive des participants. L'application ne garantit pas le remboursement en cas de défaillance d'un membre.</p>

<h5>6. Protection des données</h5>
<p>Vos données personnelles sont traitées conformément à notre Politique de Confidentialité. Vous disposez d'un droit d'accès, de rectification et de suppression de vos données.</p>

<h5>7. Modification des CGU</h5>
<p>TontineApp se réserve le droit de modifier les présentes CGU à tout moment. Les utilisateurs seront informés de toute modification substantielle.</p>
"""


@receiver(post_migrate)
def create_default_terms(sender, **kwargs):
    if sender.name == "accounts":
        if not TermsOfService.objects.exists():
            TermsOfService.objects.create(
                title="Conditions Générales d'Utilisation",
                content=DEFAULT_TERMS_CONTENT,
                version="1.0",
                is_active=True,
            )
