<script lang="ts">
	import { page } from '$app/stores';
	import { openCommandPalette } from '$lib/stores';
	import { memoryCyclesStore } from '$lib/stores/memory-cycles.svelte';

	interface NavItem {
		href: string;
		label: string;
		icon: string;
		badge?: () => number;
	}

	const navItems: NavItem[] = [
		{ href: '/', label: 'Matinée', icon: '☀️' },
		{ href: '/peripeties', label: 'Péripéties', icon: '🎪' },
		{ href: '/drafts', label: 'Brouillons', icon: '✏️' },
		{ href: '/memoires', label: 'Mémoires', icon: '📝', badge: () => memoryCyclesStore.pendingQuestionsCount },
		{ href: '/discussions', label: 'Conversations', icon: '💬' },
		{ href: '/confessions', label: 'Confessions', icon: '📖' },
		{ href: '/valets', label: 'Valets', icon: '🎭' },
		{ href: '/comptes', label: 'Comptes', icon: '📊' },
		{ href: '/settings', label: 'Réglages', icon: '⚙️' }
	];

	let expanded = $state(false);

	function isActive(href: string, pathname: string): boolean {
		if (href === '/') {
			return pathname === '/';
		}
		return pathname.startsWith(href);
	}

	function toggleSidebar() {
		expanded = !expanded;
	}
</script>

<aside
	class="fixed left-0 top-0 h-full glass-prominent hidden md:flex flex-col z-30
		transition-[width] duration-[var(--transition-normal)] ease-[var(--spring-fluid)]
		{expanded ? 'w-56' : 'w-16'}"
	onmouseenter={() => expanded = true}
	onmouseleave={() => expanded = false}
	role="navigation"
	data-testid="sidebar"
>
	<!-- Logo -->
	<div class="p-3 border-b border-[var(--glass-border-subtle)] flex items-center gap-3 h-14">
		<button
			type="button"
			onclick={toggleSidebar}
			class="w-10 h-10 flex items-center justify-center rounded-xl
				hover:bg-[var(--glass-subtle)] hover:backdrop-blur-sm
				transition-all duration-[var(--transition-fast)] ease-[var(--spring-responsive)]
				liquid-press"
			aria-label={expanded ? 'Réduire le menu' : 'Étendre le menu'}
		>
			<span class="text-xl">🎭</span>
		</button>
		{#if expanded}
			<div class="overflow-hidden">
				<h1 class="text-base font-semibold text-[var(--color-text-primary)] whitespace-nowrap">Scapin</h1>
			</div>
		{/if}
	</div>

	<!-- Search Button -->
	<div class="p-2">
		<button
			type="button"
			onclick={openCommandPalette}
			class="group relative flex items-center gap-3 w-full px-3 py-2.5 rounded-xl
				text-[var(--color-text-secondary)]
				hover:bg-[var(--glass-subtle)] hover:text-[var(--color-text-primary)]
				transition-all duration-[var(--transition-fast)] ease-[var(--spring-responsive)]
				liquid-press"
			title={!expanded ? 'Rechercher (⌘K)' : undefined}
		>
			<span class="text-lg flex-shrink-0 w-6 text-center">🔍</span>
			{#if expanded}
				<span class="font-medium text-sm whitespace-nowrap overflow-hidden flex-1">Rechercher</span>
				<kbd class="text-xs text-[var(--color-text-tertiary)] glass-subtle px-1.5 py-0.5 rounded-lg">⌘K</kbd>
			{:else}
				<span class="absolute left-full ml-2 px-2 py-1 glass-prominent text-[var(--color-text-primary)] text-xs font-medium rounded-xl shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
					Rechercher (⌘K)
				</span>
			{/if}
		</button>
	</div>

	<!-- Navigation -->
	<nav class="flex-1 p-2 space-y-1" aria-label="Navigation principale">
		{#each navItems as item}
			{@const active = isActive(item.href, $page.url.pathname)}
			{@const badgeCount = item.badge ? item.badge() : 0}
			<a
				href={item.href}
				aria-current={active ? 'page' : undefined}
				title={!expanded ? item.label : undefined}
				class="group relative flex items-center gap-3 px-3 py-2.5 rounded-xl
					transition-all duration-[var(--transition-fast)] ease-[var(--spring-responsive)]
					liquid-press
					{active
					? 'glass-subtle text-[var(--color-accent)] shadow-[inset_0_0_0_1px_var(--color-accent)]/20'
					: 'text-[var(--color-text-secondary)] hover:bg-[var(--glass-subtle)] hover:text-[var(--color-text-primary)]'}"
			>
				<span class="text-lg flex-shrink-0 w-6 text-center relative" aria-hidden="true">
					{item.icon}
					{#if badgeCount > 0 && !expanded}
						<span class="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full"></span>
					{/if}
				</span>
				{#if expanded}
					<span class="font-medium text-sm whitespace-nowrap overflow-hidden flex-1">{item.label}</span>
					{#if badgeCount > 0}
						<span class="text-xs px-1.5 py-0.5 rounded-full bg-red-500/10 text-red-500 font-medium">
							{badgeCount}
						</span>
					{/if}
				{:else}
					<!-- Tooltip on hover when collapsed -->
					<span class="absolute left-full ml-2 px-2 py-1 glass-prominent text-[var(--color-text-primary)] text-xs font-medium rounded-xl shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
						{item.label}
						{#if badgeCount > 0}
							<span class="ml-1 text-red-500">({badgeCount})</span>
						{/if}
					</span>
				{/if}
			</a>
		{/each}
	</nav>

	<!-- Footer -->
	<div class="p-2 border-t border-[var(--glass-border-subtle)]">
		{#if expanded}
			<p class="text-xs text-[var(--color-text-tertiary)] text-center">v0.8.0</p>
		{/if}
	</div>
</aside>
