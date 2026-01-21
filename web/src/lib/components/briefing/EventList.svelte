<script lang="ts">
	import type { ScapinEvent } from '$lib/types';
	import { Badge, SwipeableCard } from '$lib/components/ui';
	import { formatRelativeTime } from '$lib/utils/formatters';

	interface Props {
		events: ScapinEvent[];
		title: string;
		icon: string;
		onarchive: (id: string) => void;
		onreply: (id: string) => void;
		onopenbriefing: (event: ScapinEvent) => void;
		dataTestid?: string;
	}

	let { events, title, icon, onarchive, onreply, onopenbriefing, dataTestid }: Props = $props();
</script>

<section class="mb-5" data-testid={dataTestid}>
	<h2 class="text-base font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2">
		<span>{icon}</span>
		{title}
	</h2>
	<div class="space-y-2">
		{#each events as event (event.id)}
			<SwipeableCard
				leftAction={{
					icon: '📦',
					label: 'Classer',
					color: 'var(--color-text-tertiary)',
					action: () => onarchive(event.id)
				}}
				rightAction={{
					icon: '↩️',
					label: 'Répondre',
					color: 'var(--color-accent)',
					action: () => onreply(event.id)
				}}
			>
				<button
					type="button"
					onclick={() => console.log('Navigate to', event.id)}
					class="w-full text-left p-3"
				>
					<div class="flex items-start gap-3">
						<div class="flex-1 min-w-0">
							<div class="flex flex-wrap items-center gap-1.5 mb-1">
								<Badge variant="source" source={event.source} />
								{#if event.urgency === 'urgent' || event.urgency === 'high'}
									<Badge variant="urgency" urgency={event.urgency} />
								{/if}
								<span class="text-xs text-[var(--color-text-tertiary)]">
									{formatRelativeTime(event.occurred_at)}
								</span>
							</div>
							<h3 class="text-sm font-semibold text-[var(--color-text-primary)] truncate">
								{event.title}
							</h3>
							<p class="text-sm text-[var(--color-text-secondary)] line-clamp-1">
								{event.summary}
							</p>
							{#if event.sender}
								<p class="text-xs text-[var(--color-text-tertiary)] mt-1 truncate">
									De : {event.sender}
								</p>
							{/if}
							{#if event.has_conflicts && event.conflicts?.length}
								<p
									class="text-xs text-orange-500 mt-1 flex items-center gap-1"
									title={event.conflicts.map((c) => c.message).join(', ')}
								>
									<span>⚠️</span>
									<span
										>{event.conflicts.length} conflit{event.conflicts.length > 1 ? 's' : ''}</span
									>
								</p>
							{/if}
						</div>
						<div class="shrink-0 flex items-center gap-2">
							{#if event.source === 'calendar'}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<span
									role="button"
									tabindex="0"
									class="p-1.5 rounded-lg text-[var(--color-event-calendar)] hover:bg-[var(--color-event-calendar)] hover:bg-opacity-10 transition-colors cursor-pointer"
									title="Briefing pré-réunion"
									onclick={(e) => {
										e.stopPropagation();
										onopenbriefing(event);
									}}
									onkeydown={(e) => {
										if (e.key === 'Enter' || e.key === ' ') {
											e.preventDefault();
											e.stopPropagation();
											onopenbriefing(event);
										}
									}}
								>
									<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
										/>
									</svg>
								</span>
							{/if}
							<span class="text-[var(--color-text-tertiary)]">→</span>
						</div>
					</div>
				</button>
			</SwipeableCard>
		{/each}
	</div>
</section>
