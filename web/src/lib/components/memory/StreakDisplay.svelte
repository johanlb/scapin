<script lang="ts">
	/**
	 * StreakDisplay Component
	 * Shows review streak with flame animation and encouragement
	 */
	import type { StreakInfo } from '$lib/api/types/memory-cycles';

	interface Props {
		streak: StreakInfo;
		compact?: boolean;
	}

	let { streak, compact = false }: Props = $props();

	// Get encouragement message based on streak
	function getEncouragement(days: number): string {
		if (days === 0) return 'Commencez une nouvelle série !';
		if (days === 1) return 'Premier jour, continuez !';
		if (days < 3) return 'Beau départ !';
		if (days < 7) return 'Excellente progression !';
		if (days < 14) return 'Une semaine complète !';
		if (days < 30) return 'Impressionnant !';
		if (days < 100) return 'Incroyable discipline !';
		return 'Légendaire !';
	}

	// Generate heatmap for last 7 days
	function generateHeatmap(): { day: string; active: boolean }[] {
		const days: { day: string; active: boolean }[] = [];
		const today = new Date();
		const lastReview = streak.last_review_date ? new Date(streak.last_review_date) : null;

		for (let i = 6; i >= 0; i--) {
			const date = new Date(today);
			date.setDate(date.getDate() - i);
			const dayName = date.toLocaleDateString('fr-FR', { weekday: 'narrow' });

			// Simple heuristic: if within streak range, mark as active
			let active = false;
			if (lastReview && streak.current_streak > 0) {
				const diffDays = Math.floor((today.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
				active = diffDays < streak.current_streak;
			}

			days.push({ day: dayName, active });
		}

		return days;
	}

	const heatmap = $derived(generateHeatmap());
	const encouragement = $derived(getEncouragement(streak.current_streak));
	const isOnFire = $derived(streak.current_streak >= 3);
</script>

{#if compact}
	<!-- Compact display for widgets -->
	<div class="flex items-center gap-2">
		<span class="text-lg {isOnFire ? 'animate-pulse' : ''}">
			{isOnFire ? '🔥' : '✨'}
		</span>
		<span class="font-bold text-[var(--color-text-primary)]">
			{streak.current_streak}
		</span>
		<span class="text-xs text-[var(--color-text-tertiary)]">
			jour{streak.current_streak > 1 ? 's' : ''}
		</span>
	</div>
{:else}
	<!-- Full display -->
	<div class="space-y-3">
		<!-- Main streak display -->
		<div class="flex items-center gap-3">
			<div class="relative">
				<span class="text-4xl {isOnFire ? 'animate-bounce' : ''}">
					{isOnFire ? '🔥' : '✨'}
				</span>
				{#if isOnFire}
					<span class="absolute -top-1 -right-1 text-sm animate-ping">🔥</span>
				{/if}
			</div>
			<div>
				<p class="text-3xl font-bold text-[var(--color-text-primary)]">
					{streak.current_streak}
					<span class="text-base font-normal text-[var(--color-text-secondary)]">
						jour{streak.current_streak > 1 ? 's' : ''}
					</span>
				</p>
				<p class="text-sm text-[var(--color-accent)]">
					{encouragement}
				</p>
			</div>
		</div>

		<!-- Heatmap -->
		<div class="flex items-center gap-1">
			{#each heatmap as { day, active }}
				<div class="flex flex-col items-center gap-1">
					<div
						class="w-6 h-6 rounded-lg transition-colors
							{active
								? 'bg-[var(--color-accent)]'
								: 'bg-[var(--glass-subtle)]'}"
					></div>
					<span class="text-[10px] text-[var(--color-text-tertiary)]">
						{day}
					</span>
				</div>
			{/each}
		</div>

		<!-- Stats -->
		<div class="flex items-center gap-4 text-xs text-[var(--color-text-tertiary)]">
			<span>Record: {streak.longest_streak}j</span>
			{#if streak.last_review_date}
				<span>
					Dernière: {new Date(streak.last_review_date).toLocaleDateString('fr-FR')}
				</span>
			{/if}
		</div>

		<!-- Warning if streak at risk -->
		{#if !streak.streak_maintained}
			<div class="p-2 bg-[var(--color-warning)]/10 rounded-xl border border-[var(--color-warning)]/30">
				<p class="text-xs text-[var(--color-warning)]">
					⚠️ Révisez aujourd'hui pour maintenir votre série !
				</p>
			</div>
		{/if}
	</div>
{/if}

<style>
	@keyframes bounce {
		0%, 100% { transform: translateY(0); }
		50% { transform: translateY(-5px); }
	}

	.animate-bounce {
		animation: bounce 0.5s ease-in-out infinite;
	}
</style>
