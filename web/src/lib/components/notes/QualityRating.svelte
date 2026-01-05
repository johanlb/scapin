<script lang="ts">
	/**
	 * QualityRating Component
	 * SM-2 quality rating buttons (0-5) with keyboard support
	 */

	interface Props {
		onRate: (quality: number) => void;
		disabled?: boolean;
	}

	let { onRate, disabled = false }: Props = $props();

	const ratings = [
		{ value: 0, emoji: '😟', label: 'Blackout', desc: 'Aucun souvenir' },
		{ value: 1, emoji: '😕', label: 'Difficile', desc: 'Vague souvenir' },
		{ value: 2, emoji: '😐', label: 'Moyen', desc: 'Avec effort' },
		{ value: 3, emoji: '🙂', label: 'Bien', desc: 'Correct' },
		{ value: 4, emoji: '😊', label: 'Excellent', desc: 'Facile' },
		{ value: 5, emoji: '🌟', label: 'Parfait', desc: 'Automatique' }
	];

	function handleKeydown(e: KeyboardEvent) {
		if (disabled) return;

		// Keys 1-6 map to quality 0-5
		const key = parseInt(e.key);
		if (key >= 1 && key <= 6) {
			e.preventDefault();
			onRate(key - 1);
		}
	}

	$effect(() => {
		if (typeof window !== 'undefined') {
			window.addEventListener('keydown', handleKeydown);
			return () => window.removeEventListener('keydown', handleKeydown);
		}
	});
</script>

<div class="space-y-3">
	<p class="text-sm text-gray-600 dark:text-gray-400 text-center">
		Cette note est-elle à jour ?
	</p>

	<div class="grid grid-cols-3 gap-2 sm:grid-cols-6">
		{#each ratings as rating}
			<button
				type="button"
				onclick={() => onRate(rating.value)}
				{disabled}
				class="flex flex-col items-center gap-1 p-2 rounded-lg border border-gray-200 dark:border-gray-700
					hover:bg-gray-50 dark:hover:bg-gray-800
					disabled:opacity-50 disabled:cursor-not-allowed
					transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
				title="{rating.label}: {rating.desc} (touche {rating.value + 1})"
			>
				<span class="text-2xl">{rating.emoji}</span>
				<span class="text-xs font-medium text-gray-700 dark:text-gray-300">{rating.value}</span>
			</button>
		{/each}
	</div>

	<p class="text-xs text-gray-500 dark:text-gray-500 text-center">
		Touches 1-6 pour noter rapidement
	</p>
</div>
