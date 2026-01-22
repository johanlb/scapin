<script lang="ts">
	import type { PassHistoryEntry } from '$lib/api/client';

	export let passHistory: PassHistoryEntry[];

	const modelColors: Record<string, string> = {
		haiku: 'bg-green-500/20 text-green-400 border-green-500/30',
		sonnet: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
		opus: 'bg-red-500/20 text-red-400 border-red-500/30'
	};

	const modelIcons: Record<string, string> = {
		haiku: '🟢',
		sonnet: '🟠',
		opus: '🔴'
	};

	const passTypeLabels: Record<string, string> = {
		// Legacy v2.2
		blind: 'Extraction aveugle',
		refine: 'Raffinement contextuel',
		deep: 'Analyse approfondie',
		expert: 'Expertise maximale',
		// Four Valets v3.0
		grimaud: 'grimaud',
		bazin: 'bazin',
		planchet: 'planchet',
		mousqueton: 'mousqueton'
	};

	const passTypeTooltips: Record<string, string> = {
		// Legacy v2.2
		blind: 'Première analyse sans contexte pour extraire les informations de base',
		refine: 'Enrichissement avec le contexte personnel (notes, calendrier)',
		deep: 'Analyse en profondeur pour cas complexes ou à enjeux',
		expert: 'Utilisation du modèle le plus puissant pour décision finale',
		// Four Valets v3.0
		grimaud: 'Extraction silencieuse - Athos: extraction rapide des faits',
		bazin: 'Critique rigoureuse - Aramis: vérification et enrichissement',
		planchet: 'Action résolue - d\'Artagnan: décision finale confiante',
		mousqueton: 'Sagesse profonde - Porthos: arbitrage des cas complexes'
	};

	function formatDuration(ms: number): string {
		if (ms < 1000) return `${Math.round(ms)}ms`;
		return `${(ms / 1000).toFixed(1)}s`;
	}

	function hasThinkingBubbles(pass: PassHistoryEntry): boolean {
		return (pass.questions?.length ?? 0) > 0;
	}
</script>

<div class="space-y-0" data-testid="pass-timeline">
	{#each passHistory as pass, i}
		{@const isLast = i === passHistory.length - 1}
		{@const hasQuestions = hasThinkingBubbles(pass)}
		{@const confidenceDelta = pass.confidence_after - pass.confidence_before}
		{@const confidenceImproved = confidenceDelta > 0.01}

		<div class="relative flex gap-3" data-testid={`timeline-pass-${pass.pass_number}`}>
			<!-- Timeline connector -->
			<div class="flex flex-col items-center">
				<!-- Node -->
				<div
					class="w-8 h-8 rounded-full flex items-center justify-center text-sm border-2 {modelColors[pass.model] ?? 'bg-gray-500/20 text-gray-400 border-gray-500/30'}"
					title="{pass.model} - {passTypeTooltips[pass.pass_type] ?? pass.pass_type}"
				>
					{modelIcons[pass.model] ?? '⚪'}
				</div>
				<!-- Line (except for last) -->
				{#if !isLast}
					<div class="w-0.5 flex-1 min-h-4 bg-[var(--glass-border-subtle)]"></div>
				{/if}
			</div>

			<!-- Pass content -->
			<div class="flex-1 pb-4 {isLast ? '' : 'border-b border-[var(--glass-border-subtle)]'}">
				<!-- Header row -->
				<div class="flex items-center gap-2 flex-wrap">
					<span class="font-medium text-[var(--color-text-primary)]">
						Pass {pass.pass_number}
					</span>
					<span
						class="text-xs px-1.5 py-0.5 rounded {modelColors[pass.model] ?? 'bg-gray-500/20'}"
						title="Modele IA: {pass.model}"
					>
						{pass.model}
					</span>
					<span
						class="text-xs text-[var(--color-text-tertiary)]"
						title={passTypeTooltips[pass.pass_type] ?? pass.pass_type}
					>
						{passTypeLabels[pass.pass_type] ?? pass.pass_type}
					</span>
					<span class="text-xs text-[var(--color-text-tertiary)] ml-auto" title="Duree de cette passe">
						{formatDuration(pass.duration_ms)}
					</span>
				</div>

				<!-- Confidence evolution -->
				<div class="flex items-center gap-2 mt-1 text-sm">
					<span
						class="text-[var(--color-text-secondary)]"
						title="Evolution de la confiance durant cette passe"
					>
						{Math.round(pass.confidence_before * 100)}%
						<span class="mx-1 {confidenceImproved ? 'text-green-400' : 'text-[var(--color-text-tertiary)]'}">→</span>
						<span class={confidenceImproved ? 'text-green-400 font-medium' : ''}>
							{Math.round(pass.confidence_after * 100)}%
						</span>
					</span>
					{#if confidenceImproved}
						<span class="text-green-400 text-xs" title="Amelioration de {Math.round(confidenceDelta * 100)}%">
							+{Math.round(confidenceDelta * 100)}%
						</span>
					{/if}
				</div>

				<!-- Status badges -->
				<div class="flex items-center gap-2 mt-2 flex-wrap">
					{#if pass.context_searched}
						<span
							class="text-xs px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400"
							title="Recherche de contexte effectuee: {pass.notes_found} note{pass.notes_found !== 1 ? 's' : ''} trouvee{pass.notes_found !== 1 ? 's' : ''}"
							data-testid="timeline-context-badge"
						>
							🔍 {pass.notes_found} note{pass.notes_found !== 1 ? 's' : ''}
						</span>
					{/if}
					{#if pass.escalation_triggered}
						<span
							class="text-xs px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400"
							title="Cette passe a declenche une escalade vers un modele plus puissant"
							data-testid="timeline-escalation-badge"
						>
							↑ Escalade
						</span>
					{/if}
					{#if hasQuestions}
						<span
							class="text-xs px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400"
							title="L'IA a pose des questions/doutes pour la passe suivante"
							data-testid="timeline-thinking-badge"
						>
							💭 {pass.questions?.length} question{(pass.questions?.length ?? 0) !== 1 ? 's' : ''}
						</span>
					{/if}
				</div>

				<!-- Thinking Bubbles (questions) -->
				{#if hasQuestions && pass.questions}
					<div
						class="mt-3 p-3 rounded-lg bg-purple-500/10 border border-purple-500/20"
						data-testid="timeline-questions"
					>
						<div class="text-xs font-medium text-purple-400 mb-2" title="Questions que l'IA s'est posees pour la passe suivante">
							💭 Questions pour la suite
						</div>
						<ul class="space-y-1">
							{#each pass.questions as question}
								<li class="text-sm text-[var(--color-text-secondary)] flex items-start gap-2">
									<span class="text-purple-400 mt-0.5">•</span>
									<span>{question}</span>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			</div>
		</div>
	{/each}
</div>

<style>
	/* Ensure timeline looks good at small sizes */
	:global([data-testid="pass-timeline"]) {
		min-width: 0;
	}
</style>
