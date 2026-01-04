<script lang="ts">
	import { Card } from '$lib/components/ui';

	const weeklyStats = {
		emails_processed: 87,
		teams_messages: 42,
		meetings_attended: 12,
		tasks_completed: 34,
		focus_time_hours: 28,
		interruptions: 15
	};

	const trends = {
		emails: +12,
		productivity: +8,
		focus: -5
	};
</script>

<div class="p-4 md:p-6 max-w-4xl mx-auto">
	<header class="mb-6">
		<h1 class="text-2xl md:text-3xl font-bold text-[var(--color-text-primary)]">
			📊 Statistiques
		</h1>
		<p class="text-[var(--color-text-secondary)] mt-1">
			Aperçu de votre activité cette semaine
		</p>
	</header>

	<!-- Weekly Overview -->
	<section class="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
		<Card padding="lg">
			<div class="text-center">
				<p class="text-4xl font-bold text-[var(--color-event-email)]">{weeklyStats.emails_processed}</p>
				<p class="text-sm text-[var(--color-text-secondary)] mt-1">Emails traités</p>
				<p class="text-sm text-[var(--color-success)] mt-1">
					{trends.emails > 0 ? '+' : ''}{trends.emails}% vs semaine dernière
				</p>
			</div>
		</Card>
		<Card padding="lg">
			<div class="text-center">
				<p class="text-4xl font-bold text-[var(--color-event-teams)]">{weeklyStats.teams_messages}</p>
				<p class="text-sm text-[var(--color-text-secondary)] mt-1">Messages Teams</p>
			</div>
		</Card>
		<Card padding="lg">
			<div class="text-center">
				<p class="text-4xl font-bold text-[var(--color-event-calendar)]">{weeklyStats.meetings_attended}</p>
				<p class="text-sm text-[var(--color-text-secondary)] mt-1">Réunions</p>
			</div>
		</Card>
		<Card padding="lg">
			<div class="text-center">
				<p class="text-4xl font-bold text-[var(--color-event-omnifocus)]">{weeklyStats.tasks_completed}</p>
				<p class="text-sm text-[var(--color-text-secondary)] mt-1">Tâches complétées</p>
				<p class="text-sm text-[var(--color-success)] mt-1">
					+{trends.productivity}% productivité
				</p>
			</div>
		</Card>
		<Card padding="lg">
			<div class="text-center">
				<p class="text-4xl font-bold text-[var(--color-success)]">{weeklyStats.focus_time_hours}h</p>
				<p class="text-sm text-[var(--color-text-secondary)] mt-1">Temps focus</p>
				<p class="text-sm text-[var(--color-error)] mt-1">
					{trends.focus}% vs objectif
				</p>
			</div>
		</Card>
		<Card padding="lg">
			<div class="text-center">
				<p class="text-4xl font-bold text-[var(--color-warning)]">{weeklyStats.interruptions}</p>
				<p class="text-sm text-[var(--color-text-secondary)] mt-1">Interruptions</p>
			</div>
		</Card>
	</section>

	<!-- Insights -->
	<section>
		<h2 class="text-xl font-semibold text-[var(--color-text-primary)] mb-4">
			💡 Insights Scapin
		</h2>
		<div class="space-y-4">
			<Card padding="lg">
				<div class="flex items-start gap-3">
					<span class="text-2xl">🎯</span>
					<div>
						<h3 class="font-semibold text-[var(--color-text-primary)]">Productivité en hausse</h3>
						<p class="text-[var(--color-text-secondary)]">
							Vous avez complété 8% de tâches de plus que la semaine dernière.
							Vos créneaux du matin semblent les plus productifs.
						</p>
					</div>
				</div>
			</Card>
			<Card padding="lg">
				<div class="flex items-start gap-3">
					<span class="text-2xl">⚠️</span>
					<div>
						<h3 class="font-semibold text-[var(--color-text-primary)]">Attention aux interruptions</h3>
						<p class="text-[var(--color-text-secondary)]">
							15 interruptions cette semaine, principalement entre 14h et 16h.
							Envisagez de bloquer ce créneau pour du travail deep focus.
						</p>
					</div>
				</div>
			</Card>
		</div>
	</section>
</div>
