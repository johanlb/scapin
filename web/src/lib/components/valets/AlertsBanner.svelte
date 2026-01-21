<script lang="ts">
	import type { Alert, AlertSeverity } from '$lib/api/client';

	interface Props {
		alerts: Alert[];
		totalCritical: number;
		totalWarning: number;
		totalInfo: number;
		onDismiss?: () => void;
	}

	let { alerts, totalCritical, totalWarning, totalInfo, onDismiss }: Props = $props();

	let expanded = $state(true);

	function getSeverityIcon(severity: AlertSeverity): string {
		switch (severity) {
			case 'critical':
				return '&#128308;'; // red circle
			case 'warning':
				return '&#128993;'; // yellow circle
			case 'info':
				return '&#128309;'; // blue circle
			default:
				return '&#9679;';
		}
	}

	function getSeverityLabel(severity: AlertSeverity): string {
		switch (severity) {
			case 'critical':
				return 'CRITIQUE';
			case 'warning':
				return 'AVERTISSEMENT';
			case 'info':
				return 'INFO';
			default:
				return (severity as string).toUpperCase();
		}
	}

	function getSeverityClass(severity: AlertSeverity): string {
		switch (severity) {
			case 'critical':
				return 'severity-critical';
			case 'warning':
				return 'severity-warning';
			case 'info':
				return 'severity-info';
			default:
				return '';
		}
	}

	function formatTime(timestamp: string): string {
		const date = new Date(timestamp);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);

		if (diffMins < 1) return "À l'instant";
		if (diffMins < 60) return `Il y a ${diffMins} min`;

		const diffHours = Math.floor(diffMins / 60);
		if (diffHours < 24) return `Il y a ${diffHours}h`;

		return date.toLocaleDateString('fr-FR');
	}

	function toggleExpanded() {
		expanded = !expanded;
	}
</script>

{#if alerts.length > 0}
	<div class="alerts-banner" class:has-critical={totalCritical > 0}>
		<button class="alerts-header" onclick={toggleExpanded}>
			<div class="alerts-summary">
				{#if totalCritical > 0}
					<span class="summary-badge critical"
						>{@html '&#128308;'} {totalCritical} critique{totalCritical > 1 ? 's' : ''}</span
					>
				{/if}
				{#if totalWarning > 0}
					<span class="summary-badge warning"
						>{@html '&#128993;'} {totalWarning} avertissement{totalWarning > 1 ? 's' : ''}</span
					>
				{/if}
				{#if totalInfo > 0}
					<span class="summary-badge info"
						>{@html '&#128309;'} {totalInfo} info{totalInfo > 1 ? 's' : ''}</span
					>
				{/if}
			</div>

			<div class="header-actions">
				<span class="expand-icon">{expanded ? '&#9650;' : '&#9660;'}</span>
				{#if onDismiss}
					<span
						role="button"
						tabindex="0"
						class="dismiss-btn"
						onclick={(e) => {
							e.stopPropagation();
							onDismiss?.();
						}}
						onkeydown={(e) => {
							if (e.key === 'Enter' || e.key === ' ') {
								e.stopPropagation();
								onDismiss?.();
							}
						}}
						aria-label="Fermer"
					>
						&#10005;
					</span>
				{/if}
			</div>
		</button>

		{#if expanded}
			<div class="alerts-list">
				{#each alerts as alert (alert.id)}
					<div class="alert-item {getSeverityClass(alert.severity)}">
						<div class="alert-header">
							<span class="alert-severity">
								{@html getSeverityIcon(alert.severity)}
								{getSeverityLabel(alert.severity)}
							</span>
							<span class="alert-message">{alert.message}</span>
						</div>
						<div class="alert-meta">
							{#if alert.valet}
								<span class="alert-valet">{alert.valet}</span>
								&bull;
							{/if}
							<span class="alert-time">{formatTime(alert.triggered_at)}</span>
						</div>
						{#if alert.details}
							<div class="alert-details">{alert.details}</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}

<style>
	.alerts-banner {
		background: var(--glass-bg);
		border: 1px solid var(--glass-border-subtle);
		border-radius: 0.75rem;
		overflow: hidden;
	}

	.alerts-banner.has-critical {
		border-color: rgba(239, 68, 68, 0.5);
		background: rgba(239, 68, 68, 0.05);
	}

	.alerts-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		width: 100%;
		padding: 0.75rem 1rem;
		background: transparent;
		border: none;
		cursor: pointer;
		text-align: left;
	}

	.alerts-summary {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.summary-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.75rem;
		font-weight: 500;
		padding: 0.25rem 0.5rem;
		border-radius: 0.375rem;
	}

	.summary-badge.critical {
		background: rgba(239, 68, 68, 0.2);
		color: #ef4444;
	}

	.summary-badge.warning {
		background: rgba(234, 179, 8, 0.2);
		color: #eab308;
	}

	.summary-badge.info {
		background: rgba(59, 130, 246, 0.2);
		color: #3b82f6;
	}

	.header-actions {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.expand-icon {
		font-size: 0.75rem;
		color: var(--color-text-tertiary);
	}

	.dismiss-btn {
		padding: 0.25rem;
		background: transparent;
		border: none;
		color: var(--color-text-tertiary);
		cursor: pointer;
		font-size: 0.875rem;
	}

	.dismiss-btn:hover {
		color: var(--color-text-primary);
	}

	.alerts-list {
		border-top: 1px solid var(--glass-border-subtle);
	}

	.alert-item {
		padding: 0.75rem 1rem;
		border-bottom: 1px solid var(--glass-border-subtle);
	}

	.alert-item:last-child {
		border-bottom: none;
	}

	.alert-item.severity-critical {
		background: rgba(239, 68, 68, 0.05);
	}

	.alert-item.severity-warning {
		background: rgba(234, 179, 8, 0.05);
	}

	.alert-header {
		display: flex;
		align-items: flex-start;
		gap: 0.5rem;
		margin-bottom: 0.25rem;
	}

	.alert-severity {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.625rem;
		font-weight: 600;
		flex-shrink: 0;
	}

	.alert-message {
		font-size: 0.875rem;
		color: var(--color-text-primary);
	}

	.alert-meta {
		font-size: 0.75rem;
		color: var(--color-text-tertiary);
		display: flex;
		align-items: center;
		gap: 0.375rem;
	}

	.alert-valet {
		text-transform: capitalize;
	}

	.alert-details {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
		margin-top: 0.375rem;
	}
</style>
