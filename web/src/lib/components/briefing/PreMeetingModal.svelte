<!--
	PreMeetingModal Component
	Displays a pre-meeting briefing with attendee context,
	related emails/notes, and suggested talking points.
-->
<script lang="ts">
	import { Modal, Badge, Skeleton } from '$lib/components/ui';
	import { getPreMeetingBriefing } from '$lib/api';
	import { formatRelativeTime } from '$lib/utils/formatters';

	interface Props {
		open: boolean;
		eventId: string;
		eventTitle?: string | null;
		onclose?: () => void;
	}

	let { open = $bindable(false), eventId, eventTitle = null, onclose }: Props = $props();

	// Briefing data state
	let loading = $state(true);
	let error = $state<string | null>(null);
	let briefing = $state<Awaited<ReturnType<typeof getPreMeetingBriefing>> | null>(null);

	// AbortController for cancelable fetch
	let abortController: AbortController | null = null;

	// Fetch briefing when modal opens, reset when it closes
	$effect(() => {
		if (open && eventId) {
			fetchBriefing();
		} else {
			// Cancel any pending request when modal closes
			abortController?.abort();
			abortController = null;
			// Reset state for next open
			loading = true;
			error = null;
		}
	});

	async function fetchBriefing() {
		// Cancel previous request if any
		abortController?.abort();
		abortController = new AbortController();
		const signal = abortController.signal;

		loading = true;
		error = null;
		try {
			briefing = await getPreMeetingBriefing(eventId, signal);
		} catch (e) {
			// Ignore abort errors
			if (e instanceof Error && e.name === 'AbortError') {
				return;
			}
			error = e instanceof Error ? e.message : 'Erreur lors du chargement du briefing';
			briefing = null;
		} finally {
			// Only update loading if not aborted
			if (!signal.aborted) {
				loading = false;
			}
		}
	}

	/**
	 * Get initials from a name (max 2 characters)
	 * Handles empty names gracefully
	 */
	function getInitials(name: string): string {
		if (!name || name.trim() === '') return '?';
		return name
			.split(' ')
			.filter((part) => part.length > 0)
			.map((part) => part[0]?.toUpperCase() ?? '')
			.join('')
			.slice(0, 2) || '?';
	}

	function formatTime(isoString: string): string {
		return new Date(isoString).toLocaleTimeString('fr-FR', {
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatDate(isoString: string): string {
		return new Date(isoString).toLocaleDateString('fr-FR', {
			weekday: 'long',
			day: 'numeric',
			month: 'long'
		});
	}

	function handleClose() {
		open = false;
		onclose?.();
	}
</script>

<Modal {open} title={eventTitle || 'Briefing pré-réunion'} size="lg" onclose={handleClose}>
	{#if loading}
		<!-- Loading skeleton -->
		<div class="space-y-4" data-testid="briefing-loading">
			<Skeleton variant="rectangular" height="60px" />
			<Skeleton variant="text" lines={3} />
			<Skeleton variant="rectangular" height="100px" />
		</div>
	{:else if error}
		<!-- Error state -->
		<div class="text-center py-6" data-testid="briefing-error">
			<p class="text-4xl mb-3">⚠️</p>
			<p class="text-[var(--color-urgency-urgent)] mb-3">{error}</p>
			<button
				type="button"
				class="px-4 py-2 rounded-lg bg-[var(--color-accent)] text-white text-sm font-medium"
				onclick={fetchBriefing}
			>
				Réessayer
			</button>
		</div>
	{:else if briefing}
		<div class="space-y-5" data-testid="briefing-content">
			<!-- Meeting info -->
			<section>
				<div
					class="flex items-center gap-3 p-3 rounded-lg bg-[var(--color-bg-tertiary)] border border-[var(--color-border)]"
				>
					<div
						class="w-12 h-12 rounded-lg bg-[var(--color-event-calendar)] bg-opacity-20 flex items-center justify-center text-xl"
					>
						📅
					</div>
					<div class="flex-1 min-w-0">
						<h3 class="font-semibold text-[var(--color-text-primary)] truncate">
							{briefing.title}
						</h3>
						<p class="text-sm text-[var(--color-text-secondary)]">
							{formatDate(briefing.start_time)} de {formatTime(briefing.start_time)} à {formatTime(
								briefing.end_time
							)}
						</p>
					</div>
				</div>
			</section>

			<!-- Attendees -->
			{#if briefing.attendees.length > 0}
				<section>
					<h4 class="text-sm font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2">
						<span>👥</span> Participants ({briefing.attendees.length})
					</h4>
					<div class="space-y-2">
						{#each briefing.attendees as attendee}
							<div
								class="p-3 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)]"
							>
								<div class="flex items-start gap-3">
									<div
										class="w-9 h-9 rounded-full bg-[var(--color-accent)] bg-opacity-20 flex items-center justify-center text-sm font-medium text-[var(--color-accent)]"
									>
										{getInitials(attendee.name)}
									</div>
									<div class="flex-1 min-w-0">
										<p class="font-medium text-[var(--color-text-primary)]">
											{attendee.name}
										</p>
										<p class="text-xs text-[var(--color-text-secondary)]">{attendee.email}</p>
										{#if attendee.role}
											<p class="text-xs text-[var(--color-text-tertiary)] mt-0.5">
												{attendee.role}
											</p>
										{/if}
										{#if attendee.recent_interactions.length > 0}
											<div class="mt-2 text-xs text-[var(--color-text-tertiary)]">
												<p class="font-medium mb-1">Interactions récentes :</p>
												<ul class="list-disc list-inside space-y-0.5">
													{#each attendee.recent_interactions.slice(0, 3) as interaction}
														<li>{interaction}</li>
													{/each}
												</ul>
											</div>
										{/if}
									</div>
								</div>
							</div>
						{/each}
					</div>
				</section>
			{/if}

			<!-- Agenda -->
			{#if briefing.agenda}
				<section>
					<h4 class="text-sm font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2">
						<span>📋</span> Ordre du jour
					</h4>
					<div
						class="p-3 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)] text-sm text-[var(--color-text-secondary)] whitespace-pre-wrap"
					>
						{briefing.agenda}
					</div>
				</section>
			{/if}

			<!-- Suggested Talking Points -->
			{#if briefing.suggested_talking_points.length > 0}
				<section>
					<h4 class="text-sm font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2">
						<span>💡</span> Points de discussion suggérés
					</h4>
					<ul class="space-y-1.5">
						{#each briefing.suggested_talking_points as point}
							<li
								class="flex items-start gap-2 p-2 rounded-lg bg-[var(--color-bg-secondary)] text-sm text-[var(--color-text-secondary)]"
							>
								<span class="text-[var(--color-accent)]">•</span>
								{point}
							</li>
						{/each}
					</ul>
				</section>
			{/if}

			<!-- Related Emails -->
			{#if briefing.related_emails.length > 0}
				<section>
					<h4 class="text-sm font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2">
						<span>✉️</span> Emails liés ({briefing.related_emails.length})
					</h4>
					<div class="space-y-2">
						{#each briefing.related_emails.slice(0, 5) as email}
							<div
								class="p-2 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)]"
							>
								<div class="flex items-start gap-2">
									<Badge variant="source" source="email" />
									<div class="flex-1 min-w-0">
										<p class="text-sm font-medium text-[var(--color-text-primary)] truncate">
											{email.title}
										</p>
										<p class="text-xs text-[var(--color-text-tertiary)]">
											{formatRelativeTime(email.timestamp)}
										</p>
									</div>
								</div>
							</div>
						{/each}
					</div>
				</section>
			{/if}

			<!-- Related Notes -->
			{#if briefing.related_notes.length > 0}
				<section>
					<h4 class="text-sm font-semibold text-[var(--color-text-primary)] mb-2 flex items-center gap-2">
						<span>📝</span> Notes liées ({briefing.related_notes.length})
					</h4>
					<div class="flex flex-wrap gap-1.5">
						{#each briefing.related_notes as note}
							<span
								class="px-2 py-1 text-xs rounded-full bg-[var(--color-bg-tertiary)] text-[var(--color-text-secondary)] border border-[var(--color-border)]"
							>
								[[{note}]]
							</span>
						{/each}
					</div>
				</section>
			{/if}
		</div>
	{/if}
</Modal>
