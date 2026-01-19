<script lang="ts">
	import { goto } from '$app/navigation';
	import type { PipelineStage } from '$lib/api/client';

	interface Props {
		stages: PipelineStage[];
		totalInPipeline: number;
		estimatedMinutes: number;
		bottleneckValet: string | null;
	}

	let { stages, totalInPipeline, estimatedMinutes, bottleneckValet }: Props = $props();

	function getStatusColor(status: string): string {
		switch (status) {
			case 'running':
				return '#22c55e';
			case 'idle':
				return 'var(--color-text-tertiary)';
			case 'paused':
				return '#eab308';
			case 'error':
				return '#ef4444';
			default:
				return 'var(--color-text-tertiary)';
		}
	}

	function handleNodeClick(valet: string) {
		goto(`/valets/${valet}`);
	}
</script>

<div class="workflow-diagram">
	<div class="workflow-header">
		<span class="workflow-title">Pipeline de traitement</span>
		<span class="workflow-stats">
			{totalInPipeline} en cours
			{#if estimatedMinutes > 0}
				&bull; ~{estimatedMinutes.toFixed(0)} min
			{/if}
		</span>
	</div>

	<div class="pipeline-container">
		<div class="pipeline-nodes">
			{#each stages as stage, i (stage.valet)}
				<div class="stage-wrapper">
					<button
						class="pipeline-node"
						class:running={stage.status === 'running'}
						class:bottleneck={stage.is_bottleneck}
						class:error={stage.status === 'error'}
						onclick={() => handleNodeClick(stage.valet)}
						title={stage.display_name}
					>
						<span class="node-icon">{stage.icon}</span>
						<span
							class="node-count"
							class:has-items={stage.items_processing + stage.items_queued > 0}
						>
							{stage.items_processing + stage.items_queued}
						</span>
						<span class="node-status" style="background: {getStatusColor(stage.status)}"></span>
					</button>

					<span class="stage-name">{stage.display_name}</span>

					{#if stage.is_bottleneck}
						<span class="bottleneck-badge">Goulot</span>
					{/if}
				</div>

				{#if i < stages.length - 1}
					<div class="pipeline-arrow">
						<svg width="24" height="12" viewBox="0 0 24 12">
							<path
								d="M0 6 L18 6 M14 2 L18 6 L14 10"
								fill="none"
								stroke="var(--color-text-tertiary)"
								stroke-width="1.5"
								stroke-linecap="round"
								stroke-linejoin="round"
							/>
						</svg>
					</div>
				{/if}
			{/each}
		</div>
	</div>

	{#if bottleneckValet}
		<div class="bottleneck-warning">
			<span class="warning-icon">&#9888;</span>
			<span class="warning-text">Goulot détecté sur {bottleneckValet}</span>
		</div>
	{/if}
</div>

<style>
	.workflow-diagram {
		background: var(--glass-bg);
		border: 1px solid var(--glass-border-subtle);
		border-radius: 0.75rem;
		padding: 1rem;
	}

	.workflow-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.workflow-title {
		font-weight: 600;
		color: var(--color-text-primary);
	}

	.workflow-stats {
		font-size: 0.75rem;
		color: var(--color-text-tertiary);
	}

	.pipeline-container {
		overflow-x: auto;
		padding: 0.5rem 0;
	}

	.pipeline-nodes {
		display: flex;
		align-items: flex-start;
		justify-content: center;
		gap: 0.25rem;
		min-width: max-content;
	}

	.stage-wrapper {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		position: relative;
	}

	.pipeline-node {
		width: 3.5rem;
		height: 3.5rem;
		border-radius: 0.75rem;
		background: var(--glass-tint);
		border: 2px solid var(--glass-border-subtle);
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		transition: all 0.2s;
		position: relative;
	}

	.pipeline-node:hover {
		background: var(--glass-bg);
		border-color: var(--color-accent);
		transform: scale(1.05);
	}

	.pipeline-node.running {
		border-color: #22c55e;
		animation: pulse 2s infinite;
	}

	.pipeline-node.bottleneck {
		border-color: #eab308;
		background: rgba(234, 179, 8, 0.1);
	}

	.pipeline-node.error {
		border-color: #ef4444;
		background: rgba(239, 68, 68, 0.1);
	}

	@keyframes pulse {
		0%,
		100% {
			box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.4);
		}
		50% {
			box-shadow: 0 0 0 4px rgba(34, 197, 94, 0);
		}
	}

	.node-icon {
		font-size: 1.25rem;
	}

	.node-count {
		font-size: 0.625rem;
		color: var(--color-text-tertiary);
		font-weight: 600;
	}

	.node-count.has-items {
		color: var(--color-text-primary);
	}

	.node-status {
		position: absolute;
		top: 0.25rem;
		right: 0.25rem;
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
	}

	.stage-name {
		font-size: 0.625rem;
		color: var(--color-text-tertiary);
		text-align: center;
		max-width: 4rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.bottleneck-badge {
		position: absolute;
		top: -0.5rem;
		right: -0.5rem;
		font-size: 0.5rem;
		padding: 0.125rem 0.25rem;
		background: #eab308;
		color: black;
		border-radius: 0.25rem;
		font-weight: 600;
	}

	.pipeline-arrow {
		display: flex;
		align-items: center;
		padding-top: 1rem;
	}

	.bottleneck-warning {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-top: 0.75rem;
		padding: 0.5rem 0.75rem;
		background: rgba(234, 179, 8, 0.1);
		border-radius: 0.5rem;
		border: 1px solid rgba(234, 179, 8, 0.3);
	}

	.warning-icon {
		color: #eab308;
	}

	.warning-text {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
	}
</style>
