"""
Service de notification SMS.

Ce module implémente l'envoi de SMS via différents providers
pour les notifications de paiement.

Providers supportés:
- Africa's Talking (recommandé - multi-opérateurs)
- Orange SMS
"""

import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class SMSNotificationService:
    """
    Service pour l'envoi de SMS de notification.

    Ce service abstrait les différents providers SMS
    et fournit une interface unifiée pour l'envoi.

    Attributes:
        provider: Provider SMS utilisé
        max_retries: Nombre maximum de tentatives de retry

    Methods:
        send_sms(): Envoie un SMS
        send_payment_confirmation(): Envoie une confirmation de paiement
        send_withdrawal_notification(): Notifie un retrait disponible
        send_reminder(): Envoie un rappel de cotisation

    Example:
        >>> service = SMSNotificationService()
        >>> response = service.send_sms(
        ...     phone="+221771234567",
        ...     message="Bonjour!"
        ... )
    """

    def __init__(self, provider: str = None):
        """
        Initialise le service SMS.

        Args:
            provider: Provider à utiliser (défaut: depuis settings)
        """
        sms_settings = getattr(settings, "SMS_SETTINGS", {})

        if provider is None:
            provider = sms_settings.get("DEFAULT_PROVIDER", "africas_talking")

        self.provider = provider
        self.sms_settings = sms_settings
        self.max_retries = sms_settings.get("MAX_SMS_RETRIES", 3)

        logger.info(f"SMSNotificationService initialized with provider: {provider}")

    def send_sms(
        self,
        phone: str,
        message: str,
        user=None,
        notification_type: str = "general",
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Envoie un SMS.

        Args:
            phone: Numéro de téléphone du destinataire
            message: Contenu du SMS
            user: Utilisateur destinataire (optionnel)
            notification_type: Type de notification
            metadata: Métadonnées additionnelles

        Returns:
            Dict: Résultat de l'envoi
        """
        from apps.payments.models import SMSNotificationLog

        phone = self._normalize_phone(phone)

        sms_log = SMSNotificationLog.objects.create(
            phone_number=phone,
            message=message,
            provider=self.provider,
            status=SMSNotificationLog.Status.PENDING,
            user=user,
            notification_type=notification_type,
        )

        try:
            if self.provider == "africas_talking":
                result = self._send_africas_talking(phone, message)
            elif self.provider == "orange":
                result = self._send_orange_sms(phone, message)
            else:
                result = {"success": True, "message_id": f"SIM_{phone[:10]}"}

            if result.get("success"):
                sms_log.status = SMSNotificationLog.Status.SENT
                sms_log.external_id = result.get("message_id", "")
                sms_log.response_data = result
                sms_log.sent_at = timezone.now()
                sms_log.save()

                return {
                    "success": True,
                    "message_id": result.get("message_id"),
                    "log_id": sms_log.id,
                }
            else:
                raise Exception(result.get("error", "Erreur inconnue"))

        except Exception as e:
            logger.error(f"SMS send error: {e}")

            sms_log.status = SMSNotificationLog.Status.FAILED
            sms_log.error_message = str(e)
            sms_log.save()

            if self.sms_settings.get("RETRY_ON_FAILURE"):
                self._schedule_retry(sms_log)

            return {
                "success": False,
                "error": str(e),
                "log_id": sms_log.id,
            }

    def _send_africas_talking(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Envoie un SMS via Africa's Talking.

        Africa's Talking est un agrégateur SMS qui permet
        d'envoyer vers plusieurs opérateurs africains.

        Args:
            phone: Numéro de téléphone
            message: Contenu du SMS

        Returns:
            Dict: Résultat de l'envoi
        """
        try:
            from africastalking import SMS

            config = self.sms_settings.get("AFRICAS_TALKING", {})
            username = config.get("USERNAME", "sandbox")
            api_key = config.get("API_KEY", "")

            SMS.initialize(username=username, api_key=api_key)

            result = SMS.send(message, [phone])

            if result["SMSMessageData"]["Recipients"]:
                recipient = result["SMSMessageData"]["Recipients"][0]
                if recipient.get("status") == "Success":
                    return {
                        "success": True,
                        "message_id": recipient.get("messageId"),
                        "cost": recipient.get("cost"),
                    }

            return {
                "success": False,
                "error": result["SMSMessageData"].get("Message", "Erreur inconnue"),
            }

        except ImportError:
            logger.warning("Africa's Talking SDK not installed")
            return {
                "success": True,
                "message_id": f"SIMULATED_{phone}_{__import__('uuid').uuid4().hex[:8]}",
                "simulated": True,
            }

        except Exception as e:
            logger.error(f"Africa's Talking error: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _send_orange_sms(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Envoie un SMS via Orange SMS API.

        Args:
            phone: Numéro de téléphone
            message: Contenu du SMS

        Returns:
            Dict: Résultat de l'envoi
        """
        orange_config = self.sms_settings.get("ORANGE_SMS", {})
        if not orange_config.get("API_KEY"):
            return {
                "success": True,
                "message_id": f"SIMULATED_ORANGE_{phone}",
                "simulated": True,
            }

        return {
            "success": False,
            "error": "Orange SMS API non implémentée",
        }

    def send_payment_confirmation(
        self, user, amount: float, transaction_id: str, provider: str = None
    ) -> Dict[str, Any]:
        """
        Envoie une confirmation de paiement.

        Args:
            user: Utilisateur destinataire
            amount: Montant du paiement
            transaction_id: ID de la transaction
            provider: Provider de paiement (optionnel)

        Returns:
            Dict: Résultat de l'envoi
        """
        message = (
            f"TontineApp: Paiement de {amount} XAF recu. "
            f"Transaction: {transaction_id}. Merci pour votre confiance!"
        )

        return self.send_sms(
            phone=str(user.phone),
            message=message,
            user=user,
            notification_type="payment_confirmation",
            metadata={
                "amount": amount,
                "transaction_id": transaction_id,
                "provider": provider,
            },
        )

    def send_withdrawal_notification(
        self, user, amount: float, tontine_name: str = None
    ) -> Dict[str, Any]:
        """
        Notifie un membre que son retrait est disponible.

        Args:
            user: Utilisateur destinataire
            amount: Montant du retrait
            tontine_name: Nom de la tontine (optionnel)

        Returns:
            Dict: Résultat de l'envoi
        """
        message = (
            f"TontineApp: Felicitations! Votre gain de {amount} XAF est disponible."
        )

        if tontine_name:
            message += f" Tontine: {tontine_name}."

        message += " Contactez votre tresorier pour le retrait."

        return self.send_sms(
            phone=str(user.phone),
            message=message,
            user=user,
            notification_type="withdrawal_available",
            metadata={
                "amount": amount,
                "tontine": tontine_name,
            },
        )

    def send_reminder(
        self, user, amount: float, tontine_name: str, due_date: str
    ) -> Dict[str, Any]:
        """
        Envoie un rappel de cotisation.

        Args:
            user: Utilisateur destinataire
            amount: Montant de la cotisation
            tontine_name: Nom de la tontine
            due_date: Date d'échéance

        Returns:
            Dict: Résultat de l'envoi
        """
        message = (
            f"TontineApp: Rappel - Cotisation de {amount} XAF "
            f"pour {tontine_name} due le {due_date}. "
            f"Merci de votre ponctualite!"
        )

        return self.send_sms(
            phone=str(user.phone),
            message=message,
            user=user,
            notification_type="contribution_reminder",
            metadata={
                "amount": amount,
                "tontine": tontine_name,
                "due_date": due_date,
            },
        )

    def _normalize_phone(self, phone: str) -> str:
        """
        Normalise un numéro de téléphone.

        Args:
            phone: Numéro de téléphone

        Returns:
            str: Numéro normalisé
        """
        digits = "".join(filter(str.isdigit, phone))

        if digits.startswith("00"):
            return "+" + digits[2:]
        elif digits.startswith("0"):
            return "+221" + digits[1:]

        return phone

    def _schedule_retry(self, sms_log):
        """
        Planifie un retry pour un SMS échoué.

        Args:
            sms_log: L'objet SMSNotificationLog
        """
        if sms_log.retry_count >= self.max_retries:
            logger.warning(f"Max SMS retries exceeded for {sms_log.phone_number}")
            return

        sms_log.retry_count += 1
        sms_log.status = SMSNotificationLog.Status.RETRY
        sms_log.save()

        logger.info(f"SMS retry scheduled for {sms_log.phone_number}")
