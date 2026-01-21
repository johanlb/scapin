<script lang="ts">
	import { Card } from '$lib/components/ui';

	interface Props {
		stats: {
			emails_pending: number;
			teams_unread: number;
			meetings_today: number;
			tasks_due: number;
		};
	}

	let { stats }: Props = $props();
</script>

<section class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-5">
	<Card padding="sm">
		<div class="text-center">
			<p class="text-xl md:text-2xl font-bold text-[var(--color-event-email)]">
				{stats.emails_pending}
			</p>
			<p class="text-xs text-[var(--color-text-tertiary)]">Emails</p>
		</div>
	</Card>
	<Card padding="sm">
		<div class="text-center">
			<p class="text-xl md:text-2xl font-bold text-[var(--color-event-teams)]">
				{stats.teams_unread}
			</p>
			<p class="text-xs text-[var(--color-text-tertiary)]">Teams</p>
		</div>
	</Card>
	<Card padding="sm">
		<div class="text-center">
			<p class="text-xl md:text-2xl font-bold text-[var(--color-event-calendar)]">
				{stats.meetings_today}
			</p>
			<p class="text-xs text-[var(--color-text-tertiary)]">Réunions</p>
		</div>
	</Card>
	<Card padding="sm">
		<div class="text-center">
			<p class="text-xl md:text-2xl font-bold text-[var(--color-event-omnifocus)]">
				{stats.tasks_due}
			</p>
			<p class="text-xs text-[var(--color-text-tertiary)]">Tâches</p>
		</div>
	</Card>
</section>
