<script lang="ts">
	import type { ValetActivity } from '$lib/api/client';

	interface Props {
		activities: ValetActivity[];
		filter?: 'all' | 'success' | 'error';
		maxItems?: number;
	}

	let { activities, filter = 'all', maxItems = 50 }: Props = $props();

	const filteredActivities = $derived(() => {
		let filtered = activities;
		if (filter === 'success') {
			filtered = activities.filter((a) => a.success);
		} else if (filter === 'error') {
			filtered = activities.filter((a) => !a.success);
		}
		return filtered.slice(0, maxItems);
	});

	function formatTime(timestamp: string): string {
		const date = new Date(timestamp);
		return date.toLocaleTimeString('fr-FR', {
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatDuration(ms: number | null): string {
		if (!ms) return '';
		if (ms < 1000) return `${ms}ms`;
		return `${(ms / 1000).toFixed(1)}s`;
	}
</script>

<div class="activity-timeline">
	{#if filteredActivities().length === 0}
		<div class="empty-state">
			<span class="text-[var(--color-text-tertiary)]">Aucune activité</span>
		</div>
	{:else}
		<div class="timeline-list">
			{#each filteredActivities() as activity (activity.timestamp)}
				<div class="timeline-item" class:error={!activity.success}>
					<div class="timeline-dot" class:success={activity.success} class:error={!activity.success}>
						{#if activity.success}
							<span class="dot-icon">&#10003;</span>
						{:else}
							<span class="dot-icon">&#10007;</span>
						{/if}
					</div>
					<div class="timeline-content">
						<div class="timeline-header">
							<span class="timeline-time">{formatTime(activity.timestamp)}</span>
							{#if activity.duration_ms}
								<span class="timeline-duration">{formatDuration(activity.duration_ms)}</span>
							{/if}
						</div>
						<div class="timeline-action">{activity.action}</div>
						{#if activity.details}
							<div class="timeline-details">{activity.details}</div>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.activity-timeline {
		max-height: 400px;
		overflow-y: auto;
	}

	.empty-state {
		padding: 2rem;
		text-align: center;
	}

	.timeline-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.timeline-item {
		display: flex;
		gap: 0.75rem;
		padding: 0.75rem;
		border-radius: 0.5rem;
		background: var(--glass-tint);
		transition: background 0.2s;
	}

	.timeline-item:hover {
		background: var(--glass-bg);
	}

	.timeline-item.error {
		background: rgba(239, 68, 68, 0.1);
	}

	.timeline-dot {
		flex-shrink: 0;
		width: 1.5rem;
		height: 1.5rem;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.75rem;
	}

	.timeline-dot.success {
		background: rgba(34, 197, 94, 0.2);
		color: rgb(34, 197, 94);
	}

	.timeline-dot.error {
		background: rgba(239, 68, 68, 0.2);
		color: rgb(239, 68, 68);
	}

	.dot-icon {
		font-weight: bold;
	}

	.timeline-content {
		flex: 1;
		min-width: 0;
	}

	.timeline-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.25rem;
	}

	.timeline-time {
		font-size: 0.75rem;
		color: var(--color-text-tertiary);
		font-family: monospace;
	}

	.timeline-duration {
		font-size: 0.75rem;
		color: var(--color-text-tertiary);
		padding: 0.125rem 0.375rem;
		background: var(--glass-tint);
		border-radius: 0.25rem;
	}

	.timeline-action {
		font-size: 0.875rem;
		color: var(--color-text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.timeline-details {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
		margin-top: 0.25rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
</style>
