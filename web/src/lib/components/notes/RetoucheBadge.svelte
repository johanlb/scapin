<script lang="ts">
	/**
	 * RetoucheBadge Component
	 * Shows the retouche status of a note with quality score
	 */

	interface Props {
		qualityScore: number | null;
		retoucheCount?: number;
		pending?: boolean;
		size?: 'sm' | 'md' | 'lg';
		class?: string;
	}

	let {
		qualityScore,
		retoucheCount = 0,
		pending = false,
		size = 'md',
		class: className = ''
	}: Props = $props();

	const sizeClasses = {
		sm: 'text-xs px-1.5 py-0.5',
		md: 'text-sm px-2 py-1',
		lg: 'text-base px-3 py-1.5'
	};

	const qualityColor = $derived.by(() => {
		if (qualityScore === null) return 'bg-gray-500/20 text-gray-400';
		if (qualityScore >= 80) return 'bg-green-500/20 text-green-400';
		if (qualityScore >= 60) return 'bg-yellow-500/20 text-yellow-400';
		if (qualityScore >= 40) return 'bg-orange-500/20 text-orange-400';
		return 'bg-red-500/20 text-red-400';
	});

	const qualityIcon = $derived.by(() => {
		if (pending) return '🔄';
		if (qualityScore === null) return '❓';
		if (qualityScore >= 80) return '✨';
		if (qualityScore >= 60) return '👍';
		if (qualityScore >= 40) return '📝';
		return '⚠️';
	});
</script>

<div
	class="inline-flex items-center gap-1.5 rounded-full font-medium {sizeClasses[size]} {qualityColor} {className}"
	title={pending
		? 'Retouche en cours...'
		: qualityScore !== null
			? `Qualité: ${qualityScore}% (${retoucheCount} retouche${retoucheCount !== 1 ? 's' : ''})`
			: 'Non évalué'}
>
	<span class="quality-icon">{qualityIcon}</span>
	{#if qualityScore !== null}
		<span class="font-mono">{qualityScore}%</span>
	{:else if pending}
		<span>...</span>
	{:else}
		<span>?</span>
	{/if}
</div>

<style>
	.quality-icon {
		font-size: 0.9em;
	}
</style>
