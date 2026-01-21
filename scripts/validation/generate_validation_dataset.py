#!/usr/bin/env python3
"""
Generate Validation Dataset for Four Valets v3.0

Creates a dataset of 100 realistic email scenarios for validating
the Four Valets pipeline. Each email includes expected outcomes.

Categories:
- Ephemeral (OTP, notifications, reminders): 20 emails
- Newsletters/Spam: 15 emails
- Business (meetings, deadlines, contracts): 25 emails
- Personal (family, friends): 15 emails
- Financial (invoices, payments): 15 emails
- Complex (conflicts, multi-topic): 10 emails
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent.parent / "tests" / "validation" / "dataset"


def generate_id() -> str:
    """Generate a unique email ID."""
    return f"val-{uuid.uuid4().hex[:8]}"


def random_date(days_ahead: int = 30) -> str:
    """Generate a random future date."""
    future = datetime.now() + timedelta(days=random.randint(1, days_ahead))
    return future.strftime("%d %B %Y")


def random_time() -> str:
    """Generate a random time."""
    hour = random.randint(8, 19)
    minute = random.choice([0, 15, 30, 45])
    return f"{hour:02d}h{minute:02d}"


def random_amount() -> str:
    """Generate a random financial amount."""
    amount = random.choice([99, 149, 299, 499, 999, 1499, 2999, 4999, 9999, 14999, 24999, 49999])
    return f"{amount:,}".replace(",", " ") + "€"


# ============================================================================
# Email Templates by Category
# ============================================================================


def generate_ephemeral_emails(count: int = 20) -> list[dict]:
    """Generate ephemeral content emails (OTP, notifications, reminders)."""
    emails = []

    # OTP codes (8 emails)
    otp_senders = [
        ("noreply@boursorama.fr", "Boursorama Banque"),
        ("security@paypal.com", "PayPal"),
        ("noreply@google.com", "Google"),
        ("noreply@apple.com", "Apple"),
        ("no-reply@amazon.fr", "Amazon"),
        ("noreply@microsoft.com", "Microsoft"),
        ("security@stripe.com", "Stripe"),
        ("noreply@github.com", "GitHub"),
    ]

    for i, (sender, name) in enumerate(otp_senders[:8]):
        code = f"{random.randint(100000, 999999)}"
        emails.append({
            "id": generate_id(),
            "category": "ephemeral",
            "subcategory": "otp",
            "expected": {
                "stopped_at": "grimaud",
                "action": "delete",
                "early_stop": True,
                "extractions_count": 0,
            },
            "event": {
                "event_id": f"otp-{i+1:03d}",
                "title": f"Votre code de vérification {name}",
                "content": f"Bonjour,\n\nVotre code de vérification est : {code}\n\nCe code expire dans 10 minutes.\n\nSi vous n'êtes pas à l'origine de cette demande, ignorez ce message.\n\nCordialement,\n{name}",
                "from_person": sender,
                "to_people": ["johan@example.com"],
                "source": "email",
                "event_type": "information",
                "urgency": "low",
            },
        })

    # Calendar reminders (6 emails)
    reminder_types = [
        "Rappel: Réunion dans 15 minutes",
        "Rappel: Appel prévu dans 30 minutes",
        "Rappel: Meeting demain à 14h",
        "Notification: Événement modifié",
        "Rappel quotidien: Standup 9h",
        "Notification: Réunion annulée",
    ]

    for i, title in enumerate(reminder_types):
        emails.append({
            "id": generate_id(),
            "category": "ephemeral",
            "subcategory": "reminder",
            "expected": {
                "stopped_at": "grimaud",
                "action": "delete",
                "early_stop": True,
                "extractions_count": 0,
            },
            "event": {
                "event_id": f"reminder-{i+1:03d}",
                "title": title,
                "content": f"Rappel automatique de votre calendrier.\n\n{title}\n\n---\nGoogle Calendar",
                "from_person": "calendar-notification@google.com",
                "to_people": ["johan@example.com"],
                "source": "email",
                "event_type": "information",
                "urgency": "low",
            },
        })

    # Shipping notifications (6 emails)
    shipping_subjects = [
        "Votre colis est en cours de livraison",
        "Votre commande a été expédiée",
        "Livraison prévue demain",
        "Votre colis a été livré",
        "Mise à jour de livraison",
        "Votre retour a été reçu",
    ]

    for i, title in enumerate(shipping_subjects):
        tracking = f"LP{random.randint(100000000, 999999999)}FR"
        emails.append({
            "id": generate_id(),
            "category": "ephemeral",
            "subcategory": "shipping",
            "expected": {
                "stopped_at": "grimaud",
                "action": "delete",
                "early_stop": True,
                "extractions_count": 0,
            },
            "event": {
                "event_id": f"shipping-{i+1:03d}",
                "title": title,
                "content": f"Bonjour,\n\n{title}\n\nN° de suivi: {tracking}\n\nSuivre mon colis sur laposte.fr\n\nCordialement,\nAmazon.fr",
                "from_person": "shipping@amazon.fr",
                "to_people": ["johan@example.com"],
                "source": "email",
                "event_type": "information",
                "urgency": "low",
            },
        })

    return emails[:count]


def generate_newsletter_emails(count: int = 15) -> list[dict]:
    """Generate newsletter and spam emails."""
    emails = []

    newsletters = [
        ("newsletter@techcrunch.com", "TechCrunch Weekly", "AI Startups Raise $5B"),
        ("digest@medium.com", "Medium Daily Digest", "Top Stories for You"),
        ("news@theverge.com", "The Verge", "Latest Tech News"),
        ("updates@linkedin.com", "LinkedIn", "Your weekly digest"),
        ("newsletter@wired.com", "WIRED", "This Week in Tech"),
        ("daily@hackernews.com", "Hacker News", "Top Stories"),
        ("newsletter@producthunt.com", "Product Hunt", "New Products"),
        ("digest@substack.com", "Substack Reads", "Weekly Roundup"),
    ]

    for i, (sender, name, topic) in enumerate(newsletters[:8]):
        emails.append({
            "id": generate_id(),
            "category": "newsletter",
            "subcategory": "newsletter",
            "expected": {
                "stopped_at": "grimaud",
                "action": "delete",
                "early_stop": True,
                "extractions_count": 0,
            },
            "event": {
                "event_id": f"newsletter-{i+1:03d}",
                "title": f"{name}: {topic}",
                "content": f"This week's top stories:\n\n• Story 1\n• Story 2\n• Story 3\n\nRead more at {name.lower().replace(' ', '')}.com\n\nUnsubscribe | Privacy Policy",
                "from_person": sender,
                "to_people": ["johan@example.com"],
                "source": "email",
                "event_type": "information",
                "urgency": "low",
            },
        })

    # Spam emails
    spam_subjects = [
        ("promo@marketing-xyz.com", "MEGA PROMO -80% SUR TOUT", "spam"),
        ("deals@unknown-store.xyz", "iPhone 15 Pro à 99€ !!!", "spam"),
        ("lottery@winner.xyz", "Vous avez gagné 1 000 000€", "scam"),
        ("prince@nigeria.xyz", "Urgent business proposal", "scam"),
        ("crypto@moon.xyz", "Make $10k/day with crypto", "scam"),
        ("promo@sales-now.xyz", "Dernière chance: -90%", "spam"),
        ("winner@prize.xyz", "Réclamez votre prix", "scam"),
    ]

    for i, (sender, subject, subcat) in enumerate(spam_subjects[:7]):
        emails.append({
            "id": generate_id(),
            "category": "newsletter",
            "subcategory": subcat,
            "expected": {
                "stopped_at": "grimaud",
                "action": "delete",
                "early_stop": True,
                "extractions_count": 0,
            },
            "event": {
                "event_id": f"spam-{i+1:03d}",
                "title": subject,
                "content": "⚡ OFFRE LIMITÉE ⚡\n\nCliquez ICI maintenant!\n\nhttp://suspicious-link.xyz/offer\n\nSe désinscrire",
                "from_person": sender,
                "to_people": ["johan@example.com"],
                "source": "email",
                "event_type": "information",
                "urgency": "low",
            },
        })

    return emails[:count]


def generate_business_emails(count: int = 25) -> list[dict]:
    """Generate business emails (meetings, deadlines, contracts)."""
    emails = []

    # Meeting invitations (10 emails)
    meeting_types = [
        ("Réunion budget Q1", "Sophie Martin", "Directrice Financière"),
        ("Point projet Alpha", "Thomas Leclerc", "Chef de projet"),
        ("Review technique", "Pierre Durand", "Lead Developer"),
        ("Sync équipe Marketing", "Marie Lambert", "Responsable Marketing"),
        ("Comité de direction", "Jean Dubois", "DG"),
        ("Entretien annuel", "Claire Petit", "RH"),
        ("Demo client Nexus", "Marc Dupont", "Commercial"),
        ("Brainstorm produit", "Julie Martin", "Product Manager"),
        ("Rétrospective sprint", "Paul Bernard", "Scrum Master"),
        ("Kick-off projet Beta", "Anne Rousseau", "Directrice Projets"),
    ]

    for i, (subject, person, role) in enumerate(meeting_types):
        date = random_date(14)
        time = random_time()
        emails.append({
            "id": generate_id(),
            "category": "business",
            "subcategory": "meeting",
            "expected": {
                "stopped_at": "planchet",
                "action": "archive",
                "early_stop": False,
                "min_extractions": 1,
                "expected_types": ["evenement"],
                "calendar": True,
            },
            "event": {
                "event_id": f"meeting-{i+1:03d}",
                "title": f"Invitation: {subject} - {date} {time}",
                "content": f"Bonjour Johan,\n\nJe vous invite à une réunion.\n\nSujet: {subject}\nDate: {date}\nHeure: {time}\nLieu: Salle Confluence\n\nMerci de confirmer votre présence.\n\nCordialement,\n{person}\n{role} - Acme Corp",
                "from_person": f"{person.lower().replace(' ', '.')}@acme.com",
                "to_people": ["johan@example.com"],
                "source": "email",
                "event_type": "action_required",
                "urgency": "medium",
            },
        })

    # Deadline emails (8 emails)
    deadlines = [
        ("Rapport mensuel à soumettre", "3 jours", "haute"),
        ("Validation contrat urgent", "demain 17h", "haute"),
        ("Documentation technique", "fin de semaine", "moyenne"),
        ("Revue de code PR #456", "2 jours", "moyenne"),
        ("Budget prévisionnel", "vendredi", "haute"),
        ("Présentation client", "lundi prochain", "haute"),
        ("Mise à jour du backlog", "cette semaine", "moyenne"),
        ("Tests de recette", "avant déploiement", "haute"),
    ]

    for i, (subject, deadline, importance) in enumerate(deadlines):
        emails.append({
            "id": generate_id(),
            "category": "business",
            "subcategory": "deadline",
            "expected": {
                "stopped_at": "planchet",
                "action": "archive",
                "early_stop": False,
                "min_extractions": 1,
                "expected_types": ["deadline"],
                "omnifocus": True,
            },
            "event": {
                "event_id": f"deadline-{i+1:03d}",
                "title": f"[Action requise] {subject}",
                "content": f"Bonjour,\n\nRappel: {subject}\n\nDélai: {deadline}\n\nMerci de traiter ce point en priorité.\n\nCordialement,\nL'équipe",
                "from_person": "team@acme.com",
                "to_people": ["johan@example.com"],
                "source": "email",
                "event_type": "action_required",
                "urgency": "high" if importance == "haute" else "medium",
            },
        })

    # Contract emails (7 emails)
    contracts = [
        ("Contrat de prestation", "Nexus Inc", "45000"),
        ("Renouvellement licence", "Adobe", "2400"),
        ("Avenant contrat", "CloudHost", "599"),
        ("Proposition commerciale", "DataTech", "15000"),
        ("NDA à signer", "StartupXYZ", "0"),
        ("Contrat de maintenance", "TechSupport", "3600"),
        ("Accord de partenariat", "Partner Corp", "10000"),
    ]

    for i, (subject, company, amount) in enumerate(contracts):
        emails.append({
            "id": generate_id(),
            "category": "business",
            "subcategory": "contract",
            "expected": {
                "stopped_at": "mousqueton",  # High stakes = Mousqueton
                "action": "archive",
                "early_stop": False,
                "min_extractions": 2,
                "expected_types": ["engagement", "montant"] if int(amount) > 0 else ["engagement"],
                "high_stakes": True,
            },
            "event": {
                "event_id": f"contract-{i+1:03d}",
                "title": f"{subject} - {company}",
                "content": f"Bonjour,\n\nVeuillez trouver ci-joint le {subject.lower()} avec {company}.\n\nMontant: {amount}€\nDurée: 12 mois\n\nMerci de nous retourner le document signé.\n\nCordialement,\nService Juridique",
                "from_person": f"legal@{company.lower().replace(' ', '')}.com",
                "to_people": ["johan@example.com"],
                "source": "email",
                "event_type": "action_required",
                "urgency": "high",
            },
        })

    return emails[:count]


def generate_personal_emails(count: int = 15) -> list[dict]:
    """Generate personal emails (family, friends)."""
    emails = []

    family_members = [
        ("marie.durand@gmail.com", "Maman", "Marie"),
        ("papa.durand@gmail.com", "Papa", "Pierre"),
        ("claire.durand@gmail.com", "Claire (soeur)", "Claire"),
        ("thomas.d@gmail.com", "Thomas (frère)", "Thomas"),
        ("mamie@orange.fr", "Mamie", "Mamie"),
    ]

    family_subjects = [
        ("Anniversaire Papa", "On organise l'anniversaire de Papa le 15 février. Tu peux venir?"),
        ("Repas de Noël", "Cette année, c'est chez nous pour Noël. Confirme ta venue."),
        ("Photos vacances", "Voici les photos des vacances. Super moments en famille!"),
        ("Nouvelle adresse", "Je t'envoie ma nouvelle adresse. On a déménagé le mois dernier."),
        ("Cadeau pour Maman", "Tu as des idées pour l'anniversaire de Maman?"),
    ]

    for i, ((sender, _relation, name), (subject, content)) in enumerate(zip(family_members, family_subjects)):
        emails.append({
            "id": generate_id(),
            "category": "personal",
            "subcategory": "family",
            "expected": {
                "stopped_at": "planchet",
                "action": "archive",
                "early_stop": False,
                "min_extractions": 1,
                "expected_types": ["relation", "evenement"],
            },
            "event": {
                "event_id": f"family-{i+1:03d}",
                "title": f"Re: {subject}",
                "content": f"Mon chéri,\n\n{content}\n\nBisous,\n{name}",
                "from_person": sender,
                "to_people": ["johan@example.com"],
                "source": "email",
                "event_type": "information",
                "urgency": "medium",
            },
        })

    # Friend emails
    friends = [
        ("alex.martin@gmail.com", "Alex"),
        ("julie.b@gmail.com", "Julie"),
        ("nico.dev@gmail.com", "Nicolas"),
        ("emma.photo@gmail.com", "Emma"),
        ("lucas.music@gmail.com", "Lucas"),
    ]

    friend_subjects = [
        ("Soirée samedi", "On fait une soirée chez moi samedi. Tu viens?"),
        ("Concert prévu", "J'ai trouvé des places pour le concert. Ça te dit?"),
        ("Resto ce week-end", "Ça fait longtemps qu'on s'est pas vu. On se fait un resto?"),
        ("Projet perso", "Je voulais te parler de mon nouveau projet. On se cale un call?"),
        ("Vacances cet été", "Tu as prévu quoi cet été? On pourrait partir ensemble."),
    ]

    for i, ((sender, name), (subject, content)) in enumerate(zip(friends, friend_subjects)):
        emails.append({
            "id": generate_id(),
            "category": "personal",
            "subcategory": "friend",
            "expected": {
                "stopped_at": "planchet",
                "action": "archive",
                "early_stop": False,
                "min_extractions": 1,
            },
            "event": {
                "event_id": f"friend-{i+1:03d}",
                "title": subject,
                "content": f"Salut!\n\n{content}\n\nA+\n{name}",
                "from_person": sender,
                "to_people": ["johan@example.com"],
                "source": "email",
                "event_type": "information",
                "urgency": "low",
            },
        })

    # Social invitations
    social = [
        ("events@meetup.com", "Meetup Python Lyon", "Nouveau meetup mardi prochain"),
        ("no-reply@eventbrite.com", "EventBrite", "Confirmation de votre inscription"),
        ("invitation@conference.tech", "TechConf 2026", "Votre badge est prêt"),
        ("alumni@ecole.fr", "Alumni Network", "Soirée networking le 20 janvier"),
        ("club@running.fr", "Running Club", "Prochaine sortie dimanche"),
    ]

    for i, (sender, name, subject) in enumerate(social):
        emails.append({
            "id": generate_id(),
            "category": "personal",
            "subcategory": "social",
            "expected": {
                "stopped_at": "planchet",
                "action": "archive",
                "early_stop": False,
                "min_extractions": 1,
                "expected_types": ["evenement"],
            },
            "event": {
                "event_id": f"social-{i+1:03d}",
                "title": f"{name}: {subject}",
                "content": f"Bonjour,\n\n{subject}\n\nPlus d'infos sur notre site.\n\nCordialement,\n{name}",
                "from_person": sender,
                "to_people": ["johan@example.com"],
                "source": "email",
                "event_type": "information",
                "urgency": "low",
            },
        })

    return emails[:count]


def generate_financial_emails(count: int = 15) -> list[dict]:
    """Generate financial emails (invoices, payments)."""
    emails = []

    # Invoices
    invoices = [
        ("facturation@cloudhost.pro", "CloudHost Pro", "531.60", "Hébergement serveur"),
        ("billing@aws.amazon.com", "AWS", "234.56", "Services cloud"),
        ("invoice@figma.com", "Figma", "15", "Licence mensuelle"),
        ("billing@github.com", "GitHub", "21", "GitHub Pro"),
        ("facturation@ovh.net", "OVH", "89.99", "Domaines et DNS"),
        ("billing@notion.so", "Notion", "8", "Workspace"),
        ("invoice@vercel.com", "Vercel", "20", "Hosting Pro"),
    ]

    for i, (sender, company, amount, desc) in enumerate(invoices):
        invoice_num = f"2026-{random.randint(1000, 9999)}"
        emails.append({
            "id": generate_id(),
            "category": "financial",
            "subcategory": "invoice",
            "expected": {
                "stopped_at": "planchet",
                "action": "archive",
                "early_stop": False,
                "min_extractions": 2,
                "expected_types": ["montant", "deadline"],
                "omnifocus": True,
            },
            "event": {
                "event_id": f"invoice-{i+1:03d}",
                "title": f"Facture N°{invoice_num} - {company}",
                "content": f"Bonjour,\n\nVeuillez trouver votre facture mensuelle:\n\nFacture N°: {invoice_num}\nDescription: {desc}\nMontant: {amount}€\nÉchéance: dans 30 jours\n\nMerci de régler par virement.\n\nCordialement,\n{company}",
                "from_person": sender,
                "to_people": ["johan@example.com"],
                "source": "email",
                "event_type": "action_required",
                "urgency": "medium",
            },
        })

    # Bank notifications
    banks = [
        ("alertes@banque.fr", "Ma Banque", "Virement reçu de 2 500€"),
        ("notifications@boursorama.fr", "Boursorama", "Paiement carte de 45.90€"),
        ("secure@bnp.fr", "BNP Paribas", "Prélèvement automatique EDF"),
        ("info@revolut.com", "Revolut", "Paiement à l'étranger de 120€"),
    ]

    for i, (sender, bank, subject) in enumerate(banks):
        emails.append({
            "id": generate_id(),
            "category": "financial",
            "subcategory": "bank",
            "expected": {
                "stopped_at": "planchet",
                "action": "archive",
                "early_stop": False,
                "min_extractions": 1,
                "expected_types": ["montant"],
            },
            "event": {
                "event_id": f"bank-{i+1:03d}",
                "title": f"{bank}: {subject}",
                "content": f"Notification de votre compte:\n\n{subject}\n\nConsultez votre compte sur l'app {bank}.\n\nCordialement,\n{bank}",
                "from_person": sender,
                "to_people": ["johan@example.com"],
                "source": "email",
                "event_type": "information",
                "urgency": "medium",
            },
        })

    # Payment confirmations
    payments = [
        ("receipt@paypal.com", "PayPal", "Paiement de 89.99€ effectué"),
        ("no-reply@stripe.com", "Stripe", "Paiement reçu: 150€"),
        ("confirmation@amazon.fr", "Amazon", "Commande confirmée: 67.50€"),
        ("orders@apple.com", "Apple", "Reçu de votre achat: 0.99€"),
    ]

    for i, (sender, company, subject) in enumerate(payments):
        emails.append({
            "id": generate_id(),
            "category": "financial",
            "subcategory": "payment",
            "expected": {
                "stopped_at": "grimaud",  # Simple confirmations = early stop
                "action": "delete",
                "early_stop": True,
                "extractions_count": 0,
            },
            "event": {
                "event_id": f"payment-{i+1:03d}",
                "title": f"{company}: {subject}",
                "content": f"Confirmation de paiement\n\n{subject}\n\nMerci pour votre achat.\n\n{company}",
                "from_person": sender,
                "to_people": ["johan@example.com"],
                "source": "email",
                "event_type": "information",
                "urgency": "low",
            },
        })

    return emails[:count]


def generate_complex_emails(count: int = 10) -> list[dict]:
    """Generate complex emails (conflicts, multi-topic)."""
    emails = []

    # Conflict emails requiring Mousqueton
    conflicts = [
        {
            "subject": "Re: Date de livraison Projet Beta",
            "content": "Il y a confusion sur les dates.\n\nMarie dit 28 janvier.\nThomas confirme 4 février.\n\nLe budget aussi: 25k€ vs 32k€.\n\nPeux-tu trancher?",
        },
        {
            "subject": "Désaccord sur le scope",
            "content": "L'équipe dev et le client ne sont pas d'accord sur le périmètre.\n\nDev: MVP sans feature X\nClient: Feature X indispensable\n\nBesoin d'arbitrage.",
        },
        {
            "subject": "Conflit de ressources",
            "content": "Sophie demande Pierre sur son projet.\nThomas a aussi besoin de Pierre.\n\nLes deux projets sont critiques.\n\nQui a priorité?",
        },
        {
            "subject": "Versions contradictoires",
            "content": "J'ai reçu deux versions du contrat.\n\nVersion A: 50k€ sur 6 mois\nVersion B: 45k€ sur 8 mois\n\nLaquelle est la bonne?",
        },
        {
            "subject": "Priorités incompatibles",
            "content": "Marketing veut lancer la campagne le 15.\nProduit dit que la feature sera prête le 20.\n\nComment on gère?",
        },
    ]

    for i, conflict in enumerate(conflicts):
        emails.append({
            "id": generate_id(),
            "category": "complex",
            "subcategory": "conflict",
            "expected": {
                "stopped_at": "mousqueton",
                "action": "archive",
                "early_stop": False,
                "min_extractions": 2,
                "needs_mousqueton": True,
            },
            "event": {
                "event_id": f"conflict-{i+1:03d}",
                "title": conflict["subject"],
                "content": f"Johan,\n\n{conflict['content']}\n\nMerci,\nMarc",
                "from_person": "marc.dupont@acme.com",
                "to_people": ["johan@example.com"],
                "source": "email",
                "event_type": "action_required",
                "urgency": "high",
            },
        })

    # Multi-topic emails
    multi_topics = [
        {
            "subject": "Plusieurs points à traiter",
            "content": "1. Budget Q2: validé à 80k€\n2. Réunion vendredi 14h\n3. Contrat Nexus à signer\n4. Facture CloudHost reçue",
        },
        {
            "subject": "Update projet + admin",
            "content": "Projet Alpha avance bien (80%).\n\nPar ailleurs:\n- Valider mes congés du 15-20 février\n- Signer la note de frais\n- RDV entretien annuel à fixer",
        },
        {
            "subject": "Synthèse hebdo + actions",
            "content": "Cette semaine:\n✅ Sprint terminé\n✅ Demo client réussie\n\nActions:\n- Préparer le budget 2027\n- Contacter nouveau fournisseur\n- Former l'équipe sur le nouvel outil",
        },
        {
            "subject": "Infos diverses importantes",
            "content": "En vrac:\n\n1. Changement de bureau le 1er février\n2. Nouvelle politique de télétravail\n3. Augmentation prévue pour l'équipe\n4. Objectifs Q2 à définir",
        },
        {
            "subject": "Point perso et pro",
            "content": "Pour le boulot: deadline rapport vendredi.\n\nSinon, on fait un resto samedi? Ma mère vient aussi.\n\nEt n'oublie pas l'anniversaire de Paul dimanche!",
        },
    ]

    for i, topic in enumerate(multi_topics):
        emails.append({
            "id": generate_id(),
            "category": "complex",
            "subcategory": "multi_topic",
            "expected": {
                "stopped_at": "planchet",
                "action": "archive",
                "early_stop": False,
                "min_extractions": 3,
            },
            "event": {
                "event_id": f"multi-{i+1:03d}",
                "title": topic["subject"],
                "content": f"Bonjour,\n\n{topic['content']}\n\nCordialement,\nL'équipe",
                "from_person": "team@acme.com",
                "to_people": ["johan@example.com"],
                "source": "email",
                "event_type": "information",
                "urgency": "medium",
            },
        })

    return emails[:count]


def generate_validation_dataset():
    """Generate the complete validation dataset of 100 emails."""
    dataset = []

    # Generate by category
    dataset.extend(generate_ephemeral_emails(20))
    dataset.extend(generate_newsletter_emails(15))
    dataset.extend(generate_business_emails(25))
    dataset.extend(generate_personal_emails(15))
    dataset.extend(generate_financial_emails(15))
    dataset.extend(generate_complex_emails(10))

    # Shuffle for variety
    random.shuffle(dataset)

    # Add index
    for i, email in enumerate(dataset):
        email["index"] = i + 1

    return dataset


def main():
    """Generate and save the validation dataset."""
    print("Generating validation dataset...")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate dataset
    dataset = generate_validation_dataset()

    # Save as single JSON file
    output_file = OUTPUT_DIR / "validation_100_emails.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(dataset)} emails")
    print(f"Saved to: {output_file}")

    # Print category breakdown
    categories = {}
    for email in dataset:
        cat = email["category"]
        categories[cat] = categories.get(cat, 0) + 1

    print("\nCategory breakdown:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
