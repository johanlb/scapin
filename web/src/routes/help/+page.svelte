<script lang="ts">
	import { Card } from '$lib/components/ui';

	// Sections data
	const sections = [
		{
			id: 'getting-started',
			title: 'Démarrage Rapide',
			icon: '🚀',
			content: [
				{ subtitle: 'Installation', text: 'Backend Python + Frontend SvelteKit. Voir docs/user-guide/01-demarrage.md' },
				{ subtitle: 'Configuration', text: 'Créer un fichier .env avec vos credentials email et clé API Anthropic' },
				{ subtitle: 'Lancement', text: 'scapin serve (backend) + npm run dev (frontend)' }
			]
		},
		{
			id: 'briefing',
			title: 'Briefing',
			icon: '☀️',
			content: [
				{ subtitle: 'Matinal', text: 'Vue d\'ensemble quotidienne : emails urgents, agenda, notifications' },
				{ subtitle: 'Pré-réunion', text: 'Cliquer sur 📄 pour obtenir le contexte avant une réunion' },
				{ subtitle: 'Conflits', text: 'Détection automatique des chevauchements de calendrier' }
			]
		},
		{
			id: 'flux',
			title: 'Flux',
			icon: '📧',
			content: [
				{ subtitle: 'Approuver', text: 'Swipe droite ou bouton vert. L\'action proposée est exécutée.' },
				{ subtitle: 'Rejeter', text: 'Swipe gauche ou bouton rouge. L\'email reste non traité.' },
				{ subtitle: 'Ré-analyser', text: 'Cliquer sur "Autre" pour donner des instructions spécifiques à l\'IA.' },
				{ subtitle: 'Modifier', text: 'Ajuster l\'action ou la destination avant approbation' }
			]
		},
		{
			id: 'notes',
			title: 'Notes',
			icon: '📝',
			content: [
				{ subtitle: 'Project-First', text: 'Organisation centralisée autour de vos projets et relations clés.' },
				{ subtitle: 'Wikilinks', text: 'Liens entre notes avec [[Nom de la Note]]' },
				{ subtitle: 'Révision SM-2', text: 'Algorithme de révision espacée pour maintenir vos notes à jour' },
				{ subtitle: 'Historique', text: 'Versioning Git de chaque note avec restauration possible' }
			]
		},
		{
			id: 'journal',
			title: 'Journal',
			icon: '📔',
			content: [
				{ subtitle: 'Quotidien', text: 'Scapin pré-remplit votre journée, vous complétez et corrigez' },
				{ subtitle: 'Feedback', text: 'Vos corrections améliorent les futures analyses de Scapin' },
				{ subtitle: 'Revues', text: 'Revues hebdomadaires et mensuelles pour identifier les patterns' }
			]
		},
		{
			id: 'shortcuts',
			title: 'Raccourcis Clavier',
			icon: '⌨️',
			content: [
				{ subtitle: 'Cmd+K', text: 'Recherche globale (Command Palette)' },
				{ subtitle: '?', text: 'Afficher l\'aide des raccourcis' },
				{ subtitle: 'Escape', text: 'Fermer le modal/panneau actif' },
				{ subtitle: '1-6', text: 'Noter une révision (page Notes Review)' },
				{ subtitle: 'a / r', text: 'Approuver / Rejeter (page Flux)' }
			]
		},
		{
			id: 'architecture',
			title: 'Les Valets',
			icon: '🎭',
			content: [
				{ subtitle: 'Trivelin', text: 'Perception et triage des événements (Email, Teams, Calendrier)' },
				{ subtitle: 'Sancho', text: 'Raisonnement multi-passes (v2.2) avec escalade intelligente (Haiku/Sonnet/Opus)' },
				{ subtitle: 'Passepartout', text: 'Mémoire contextuelle et recherche sémantique' },
				{ subtitle: 'Planchet', text: 'Planification et évaluation des risques' },
				{ subtitle: 'Figaro', text: 'Exécution atomique des actions' },
				{ subtitle: 'Sganarelle', text: 'Apprentissage continu à partir de vos feedbacks' }
			]
		}
	];

	const faq = [
		{
			question: 'Mes emails sont-ils traités automatiquement ?',
			answer: 'Non. Scapin analyse et propose des actions, mais vous devez approuver chaque action (sauf si la confiance dépasse 90%).'
		},
		{
			question: 'Comment Scapin apprend-il mes préférences ?',
			answer: 'Via le journal quotidien et vos corrections. Plus vous utilisez Scapin, plus il devient précis.'
		},
		{
			question: 'Puis-je annuler une action ?',
			answer: 'Oui, un bouton "Annuler" apparaît pendant 10 secondes après chaque approbation.'
		},
		{
			question: 'Mes données sont-elles sécurisées ?',
			answer: 'Toutes les données restent sur votre machine. L\'API Anthropic ne reçoit que le contenu nécessaire à l\'analyse.'
		}
	];
</script>

<svelte:head>
	<title>Aide - Scapin</title>
</svelte:head>

<div class="max-w-4xl mx-auto p-4 md:p-6 pb-24 md:pb-6">
	<!-- Header -->
	<div class="mb-8">
		<h1 class="text-3xl font-bold text-[var(--color-text-primary)] mb-2">
			Aide Scapin
		</h1>
		<p class="text-[var(--color-text-secondary)]">
			Votre gardien cognitif personnel — Guide de référence rapide
		</p>
	</div>

	<!-- Quick Start Card -->
	<Card variant="glass" class="mb-8 p-6">
		<div class="flex items-center gap-3 mb-4">
			<span class="text-3xl">💡</span>
			<h2 class="text-xl font-semibold text-[var(--color-text-primary)]">
				En bref
			</h2>
		</div>
		<div class="grid gap-4 md:grid-cols-3">
			<div class="text-center p-4 bg-[var(--color-bg-tertiary)] rounded-xl">
				<div class="text-2xl mb-2">☀️</div>
				<div class="font-medium">Briefing</div>
				<div class="text-sm text-[var(--color-text-secondary)]">Votre journée en un coup d'œil</div>
			</div>
			<div class="text-center p-4 bg-[var(--color-bg-tertiary)] rounded-xl">
				<div class="text-2xl mb-2">📧</div>
				<div class="font-medium">Flux</div>
				<div class="text-sm text-[var(--color-text-secondary)]">Approuver/rejeter les actions</div>
			</div>
			<div class="text-center p-4 bg-[var(--color-bg-tertiary)] rounded-xl">
				<div class="text-2xl mb-2">📝</div>
				<div class="font-medium">Notes</div>
				<div class="text-sm text-[var(--color-text-secondary)]">Votre base de connaissances</div>
			</div>
		</div>
	</Card>

	<!-- Sections -->
	<div class="space-y-6 mb-8">
		{#each sections as section}
			<Card variant="default" class="p-6" data-testid="help-section-{section.id}">
				<div class="flex items-center gap-3 mb-4">
					<span class="text-2xl">{section.icon}</span>
					<h2 class="text-xl font-semibold text-[var(--color-text-primary)]">
						{section.title}
					</h2>
				</div>
				<div class="grid gap-3">
					{#each section.content as item}
						<div class="flex gap-3">
							<div class="font-medium text-[var(--color-primary)] min-w-[100px]">
								{item.subtitle}
							</div>
							<div class="text-[var(--color-text-secondary)]">
								{item.text}
							</div>
						</div>
					{/each}
				</div>
			</Card>
		{/each}
	</div>

	<!-- FAQ -->
	<div class="mb-8">
		<h2 class="text-2xl font-bold text-[var(--color-text-primary)] mb-4">
			Questions Fréquentes
		</h2>
		<div class="space-y-4">
			{#each faq as item, i}
				<Card variant="default" class="p-4" data-testid="help-faq-{i}">
					<h3 class="font-semibold text-[var(--color-text-primary)] mb-2">
						{item.question}
					</h3>
					<p class="text-[var(--color-text-secondary)]">
						{item.answer}
					</p>
				</Card>
			{/each}
		</div>
	</div>

	<!-- Footer Links -->
	<Card variant="glass" class="p-6">
		<h2 class="text-xl font-semibold text-[var(--color-text-primary)] mb-4">
			Ressources
		</h2>
		<div class="grid gap-3 md:grid-cols-2">
			<a
				href="https://github.com/johanlb/scapin/tree/main/docs/user-guide"
				target="_blank"
				rel="noopener noreferrer"
				class="flex items-center gap-3 p-3 rounded-lg bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors"
			>
				<span class="text-xl">📚</span>
				<div>
					<div class="font-medium">Guide Complet</div>
					<div class="text-sm text-[var(--color-text-secondary)]">Documentation détaillée</div>
				</div>
			</a>
			<a
				href="https://github.com/johanlb/scapin/issues"
				target="_blank"
				rel="noopener noreferrer"
				class="flex items-center gap-3 p-3 rounded-lg bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors"
			>
				<span class="text-xl">🐛</span>
				<div>
					<div class="font-medium">Signaler un Bug</div>
					<div class="text-sm text-[var(--color-text-secondary)]">GitHub Issues</div>
				</div>
			</a>
			<a
				href="/settings"
				class="flex items-center gap-3 p-3 rounded-lg bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors"
			>
				<span class="text-xl">⚙️</span>
				<div>
					<div class="font-medium">Configuration</div>
					<div class="text-sm text-[var(--color-text-secondary)]">Réglages de l'application</div>
				</div>
			</a>
			<a
				href="/valets"
				class="flex items-center gap-3 p-3 rounded-lg bg-[var(--color-bg-tertiary)] hover:bg-[var(--color-bg-secondary)] transition-colors"
			>
				<span class="text-xl">🎭</span>
				<div>
					<div class="font-medium">Dashboard Valets</div>
					<div class="text-sm text-[var(--color-text-secondary)]">État du système</div>
				</div>
			</a>
		</div>
	</Card>
</div>
