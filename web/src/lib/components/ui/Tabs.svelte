<script lang="ts">
	/**
	 * Tabs Component
	 * Tab navigation with animated indicator and keyboard support
	 */
	import { haptic } from '$lib/utils/haptics';
	import type { Snippet } from 'svelte';

	interface Tab {
		id: string;
		label: string;
		icon?: string;
		badge?: number | string;
		disabled?: boolean;
	}

	interface Props {
		tabs: Tab[];
		activeTab?: string;
		variant?: 'default' | 'pills' | 'underline';
		size?: 'sm' | 'md' | 'lg';
		fullWidth?: boolean;
		onchange?: (tabId: string) => void;
		class?: string;
		children?: Snippet<[string]>;
	}

	let {
		tabs,
		activeTab = $bindable(tabs[0]?.id ?? ''),
		variant = 'default',
		size = 'md',
		fullWidth = false,
		onchange,
		class: className = '',
		children
	}: Props = $props();

	const sizeClasses = {
		sm: 'text-sm px-3 py-1.5',
		md: 'text-base px-4 py-2',
		lg: 'text-lg px-5 py-2.5'
	};

	const variantClasses = {
		default: {
			container: 'bg-[var(--glass-subtle)] rounded-xl p-1',
			tab: 'rounded-lg',
			active: 'bg-[var(--color-bg-primary)] shadow-sm',
			inactive: 'hover:bg-[var(--glass-tint)]'
		},
		pills: {
			container: 'gap-2',
			tab: 'rounded-full',
			active: 'bg-[var(--color-accent)] text-white',
			inactive: 'hover:bg-[var(--glass-subtle)]'
		},
		underline: {
			container: 'border-b border-[var(--color-border)]',
			tab: '',
			active: 'border-b-2 border-[var(--color-accent)] text-[var(--color-accent)]',
			inactive: 'hover:text-[var(--color-text-primary)] hover:border-b-2 hover:border-[var(--color-border)]'
		}
	};

	const config = $derived(variantClasses[variant]);

	function handleTabClick(tabId: string) {
		if (tabs.find((t) => t.id === tabId)?.disabled) return;

		haptic('light');
		activeTab = tabId;
		onchange?.(tabId);
	}

	let tablistRef = $state<HTMLDivElement | null>(null);

	function handleKeydown(e: KeyboardEvent, index: number) {
		const enabledTabs = tabs.filter((t) => !t.disabled);
		const currentEnabledIndex = enabledTabs.findIndex((t) => t.id === tabs[index].id);

		let newIndex = -1;
		if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
			e.preventDefault();
			newIndex = (currentEnabledIndex + 1) % enabledTabs.length;
		} else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
			e.preventDefault();
			newIndex = (currentEnabledIndex - 1 + enabledTabs.length) % enabledTabs.length;
		} else if (e.key === 'Home') {
			e.preventDefault();
			newIndex = 0;
		} else if (e.key === 'End') {
			e.preventDefault();
			newIndex = enabledTabs.length - 1;
		}

		if (newIndex >= 0) {
			const newTab = enabledTabs[newIndex];
			handleTabClick(newTab.id);
			// Focus the new tab button (scoped to this component)
			const tabButton = tablistRef?.querySelector(`#tab-${newTab.id}`) as HTMLButtonElement | null;
			tabButton?.focus();
		}
	}
</script>

<div class="tabs-component {className}">
	<!-- Tab List -->
	<div
		bind:this={tablistRef}
		class="flex {fullWidth ? 'w-full' : 'w-fit'} {config.container}"
		role="tablist"
		aria-orientation="horizontal"
	>
		{#each tabs as tab, index (tab.id)}
			<button
				type="button"
				role="tab"
				id="tab-{tab.id}"
				aria-selected={activeTab === tab.id}
				aria-controls="panel-{tab.id}"
				aria-disabled={tab.disabled}
				tabindex={activeTab === tab.id ? 0 : -1}
				class="
					{fullWidth ? 'flex-1' : ''}
					{sizeClasses[size]}
					{config.tab}
					flex items-center justify-center gap-2
					font-medium
					transition-all duration-[var(--transition-fast)] ease-[var(--spring-responsive)]
					{tab.disabled
						? 'opacity-40 cursor-not-allowed'
						: activeTab === tab.id
							? config.active + ' text-[var(--color-text-primary)]'
							: config.inactive + ' text-[var(--color-text-secondary)]'}
				"
				onclick={() => handleTabClick(tab.id)}
				onkeydown={(e) => handleKeydown(e, index)}
			>
				{#if tab.icon}
					<span class="text-current">{tab.icon}</span>
				{/if}
				<span>{tab.label}</span>
				{#if tab.badge !== undefined}
					<span
						class="px-1.5 py-0.5 text-xs rounded-full bg-[var(--color-accent)]/10 text-[var(--color-accent)]"
					>
						{tab.badge}
					</span>
				{/if}
			</button>
		{/each}
	</div>

	<!-- Tab Panels -->
	{#if children}
		{#each tabs as tab (tab.id)}
			<div
				role="tabpanel"
				id="panel-{tab.id}"
				aria-labelledby="tab-{tab.id}"
				hidden={activeTab !== tab.id}
				tabindex={activeTab === tab.id ? 0 : -1}
				class="mt-4"
			>
				{#if activeTab === tab.id}
					{@render children(tab.id)}
				{/if}
			</div>
		{/each}
	{/if}
</div>
