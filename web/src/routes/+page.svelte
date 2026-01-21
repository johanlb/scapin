<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Card, PullToRefresh } from '$lib/components/ui';
	import ProgressRing from '$lib/components/ui/ProgressRing.svelte';
	import { BriefingHeader, StatsGrid, EventList, PreMeetingModal } from '$lib/components/briefing';
	import { briefingStore } from '$lib/stores';
	import { notesReviewStore } from '$lib/stores/notes-review.svelte';
	import { memoryCyclesStore } from '$lib/stores/memory-cycles.svelte';
	import FilageWidget from '$lib/components/memory/FilageWidget.svelte';
	import { mockEvents, mockStats } from '$lib/mocks/briefing';
	import type { ScapinEvent } from '$lib/types';

	// Reactive state
	let events = $state<ScapinEvent[]>(mockEvents);
	let stats = $state(mockStats);
	let dataSource = $state<'mock' | 'api' | 'api-empty'>('mock');
	let showBriefingModal = $state(false);
	let selectedEvent = $state<ScapinEvent | null>(null);

	// Derived state
	const urgentEvents = $derived(
		events.filter((e) => e.urgency === 'urgent' || e.urgency === 'high')
	);
	const otherEvents = $derived(
		events.filter((e) => e.urgency !== 'urgent' && e.urgency !== 'high')
	);
	const eventsWithConflicts = $derived(
		events.filter((e) => e.has_conflicts && e.conflicts?.length)
	);
	const conflictsCount = $derived(briefingStore.briefing?.conflicts_count || 0);

	function openBriefing(event: ScapinEvent) {
		selectedEvent = event;
		showBriefingModal = true;
	}

	function closeBriefing() {
		showBriefingModal = false;
		selectedEvent = null;
	}

	onMount(async () => {
		await Promise.all([
			loadBriefingData(),
			notesReviewStore.fetchStats(),
			memoryCyclesStore.fetchFilage(20)
		]);
	});

	async function loadBriefingData(): Promise<void> {
		await briefingStore.fetchBriefing();

		if (briefingStore.briefing && briefingStore.stats) {
			const apiEvents: ScapinEvent[] = [
				...briefingStore.briefing.urgent_items.map(transformBriefingItem),
				...briefingStore.briefing.calendar_today.map(transformBriefingItem),
				...briefingStore.briefing.emails_pending.map(transformBriefingItem),
				...briefingStore.briefing.teams_unread.map(transformBriefingItem)
			];

			if (apiEvents.length > 0) {
				events = apiEvents;
				dataSource = 'api';
			} else {
				events = [];
				dataSource = 'api-empty';
			}

			stats = {
				emails_pending: briefingStore.briefing.emails_pending.length,
				teams_unread: briefingStore.briefing.teams_unread.length,
				meetings_today: briefingStore.briefing.meetings_today,
				tasks_due: 0
			};
		}
	}

	function transformBriefingItem(item: any): ScapinEvent {
		return {
			id: item.event_id || item.id || '',
			source: (item.source || item.type || 'email') as ScapinEvent['source'],
			title: item.title,
			summary: item.action_summary || item.summary || '',
			occurred_at: item.time_context || item.timestamp || '',
			status: 'pending',
			urgency: item.urgency as ScapinEvent['urgency'],
			confidence: 'high',
			suggested_actions: [],
			has_conflicts: item.has_conflicts,
			conflicts: item.conflicts
		};
	}

	const handleRefresh = () => loadBriefingData();
	const archiveEvent = (id: string) => {
		events = events.filter((e) => e.id !== id);
	};
	const replyToEvent = (id: string) => console.log('Reply to:', id);
</script>

<PullToRefresh onrefresh={handleRefresh}>
	<div class="p-4 md:p-6 max-w-4xl mx-auto overflow-hidden" data-testid="briefing-content">
		<BriefingHeader
			loading={briefingStore.loading}
			error={briefingStore.error}
			isMock={dataSource === 'mock'}
			isEmpty={dataSource === 'api-empty'}
		/>

		<StatsGrid {stats} />

		{#if memoryCyclesStore.filage && memoryCyclesStore.totalLectures > 0}
			<FilageWidget
				totalLectures={memoryCyclesStore.totalLectures}
				completedToday={memoryCyclesStore.completedToday}
				questionsCount={memoryCyclesStore.pendingQuestionsCount}
				loading={memoryCyclesStore.loading}
			/>
		{/if}

		{#if notesReviewStore.stats && notesReviewStore.stats.total_due > 0}
			<section class="mb-5" data-testid="notes-review-widget">
				<h2
					class="text-base font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2"
				>
					<span>📝</span> Notes à réviser
				</h2>
				<Card interactive onclick={() => goto('/memoires/review')}>
					<div class="flex items-center justify-between p-3">
						<div>
							<p class="text-lg font-semibold text-[var(--color-text-primary)]">
								{notesReviewStore.stats.total_due} notes
							</p>
							<p class="text-xs text-[var(--color-text-tertiary)]">
								{notesReviewStore.stats.reviewed_today} révisées aujourd'hui
							</p>
						</div>
						<div class="flex items-center gap-3">
							<ProgressRing
								percent={notesReviewStore.stats.total_notes > 0
									? Math.round(
											((notesReviewStore.stats.total_notes - notesReviewStore.stats.total_due) /
												notesReviewStore.stats.total_notes) *
												100
										)
									: 100}
								size={48}
								color="primary"
							/>
							<span class="text-[var(--color-text-tertiary)]">→</span>
						</div>
					</div>
				</Card>
			</section>
		{/if}

		{#if conflictsCount > 0 && eventsWithConflicts.length > 0}
			<section class="mb-5">
				<h2
					class="text-base font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2"
				>
					<span class="text-orange-500">⚠️</span> Conflits Calendrier
					<span
						class="text-xs font-normal px-1.5 py-0.5 rounded-full bg-orange-500/10 text-orange-500"
					>
						{conflictsCount}
					</span>
				</h2>
				<Card class="border-orange-500/30 bg-orange-500/5">
					<ul class="divide-y divide-[var(--color-border)]">
						{#each eventsWithConflicts as event (event.id)}
							<li class="p-3">
								<div class="flex items-start gap-2">
									<span class="text-orange-500 text-sm mt-0.5">📅</span>
									<div class="flex-1 min-w-0">
										<p class="text-sm font-medium text-[var(--color-text-primary)] truncate">
											{event.title}
										</p>
										<p class="text-xs text-[var(--color-text-tertiary)]">{event.occurred_at}</p>
										{#if event.conflicts}
											<ul class="mt-1.5 space-y-1">
												{#each event.conflicts as conflict}
													<li class="flex items-start gap-1.5">
														<span
															class="inline-block w-1.5 h-1.5 rounded-full mt-1.5 shrink-0"
															class:bg-red-500={conflict.severity === 'high'}
															class:bg-orange-500={conflict.severity === 'medium'}
															class:bg-yellow-500={conflict.severity === 'low'}
														></span>
														<span class="text-xs text-orange-600 dark:text-orange-400"
															>{conflict.message}</span
														>
													</li>
												{/each}
											</ul>
										{/if}
									</div>
								</div>
							</li>
						{/each}
					</ul>
				</Card>
			</section>
		{/if}

		{#if briefingStore.loading}
			<div class="flex justify-center py-8">
				<div
					class="w-8 h-8 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin"
				></div>
			</div>
		{:else if dataSource === 'api-empty'}
			<div class="text-center py-12">
				<p class="text-4xl mb-3">🎉</p>
				<h3 class="text-lg font-semibold text-[var(--color-text-primary)] mb-1">
					Tout est en ordre, Monsieur
				</h3>
				<p class="text-sm text-[var(--color-text-secondary)]">
					Aucune affaire pressante ne requiert votre attention
				</p>
			</div>
		{:else}
			{#if urgentEvents.length > 0}
				<EventList
					events={urgentEvents}
					title="Affaires pressantes"
					icon="🔔"
					dataTestid="urgent-items"
					onarchive={archiveEvent}
					onreply={replyToEvent}
					onopenbriefing={openBriefing}
				/>
			{/if}

			{#if otherEvents.length > 0}
				<EventList
					events={otherEvents}
					title="À votre attention"
					icon="📌"
					onarchive={archiveEvent}
					onreply={replyToEvent}
					onopenbriefing={openBriefing}
				/>
			{/if}
		{/if}

		<p class="text-xs text-[var(--color-text-tertiary)] text-center mt-6 md:hidden">
			Glissez les cartes pour répondre ou archiver
		</p>
	</div>
</PullToRefresh>

{#if selectedEvent}
	<PreMeetingModal
		bind:open={showBriefingModal}
		eventId={selectedEvent.id}
		eventTitle={selectedEvent.title}
		onclose={closeBriefing}
	/>
{/if}
