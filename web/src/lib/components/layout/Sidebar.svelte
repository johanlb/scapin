<script lang="ts">
	import { page } from '$app/stores';
	import { openCommandPalette } from '$lib/stores';

	interface NavItem {
		href: string;
		label: string;
		icon: string;
	}

	const navItems: NavItem[] = [
		{ href: '/', label: 'Briefing', icon: '☀️' },
		{ href: '/flux', label: 'Flux', icon: '📥' },
		{ href: '/notes', label: 'Notes', icon: '📝' },
		{ href: '/discussions', label: 'Discussions', icon: '💬' },
		{ href: '/journal', label: 'Journal', icon: '📖' },
		{ href: '/stats', label: 'Stats', icon: '📊' },
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
	class="fixed left-0 top-0 h-full bg-[var(--color-bg-secondary)] border-r border-[var(--color-border-light)] hidden md:flex flex-col transition-all duration-300 ease-out z-30
		{expanded ? 'w-56' : 'w-16'}"
	onmouseenter={() => expanded = true}
	onmouseleave={() => expanded = false}
	role="navigation"
>
	<!-- Logo -->
	<div class="p-3 border-b border-[var(--color-border-light)] flex items-center gap-3 h-14">
		<button
			type="button"
			onclick={toggleSidebar}
			class="w-10 h-10 flex items-center justify-center rounded-xl hover:bg-[var(--color-bg-tertiary)] transition-colors"
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
			class="group relative flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] hover:text-[var(--color-text-primary)] transition-all"
			title={!expanded ? 'Rechercher (⌘K)' : undefined}
		>
			<span class="text-lg flex-shrink-0 w-6 text-center">🔍</span>
			{#if expanded}
				<span class="font-medium text-sm whitespace-nowrap overflow-hidden flex-1">Rechercher</span>
				<kbd class="text-xs text-[var(--color-text-tertiary)] bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded">⌘K</kbd>
			{:else}
				<span class="absolute left-full ml-2 px-2 py-1 bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] text-xs font-medium rounded-lg shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
					Rechercher (⌘K)
				</span>
			{/if}
		</button>
	</div>

	<!-- Navigation -->
	<nav class="flex-1 p-2 space-y-1" aria-label="Navigation principale">
		{#each navItems as item}
			{@const active = isActive(item.href, $page.url.pathname)}
			<a
				href={item.href}
				aria-current={active ? 'page' : undefined}
				title={!expanded ? item.label : undefined}
				class="group relative flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all
                       {active
					? 'bg-[var(--color-accent)]/10 text-[var(--color-accent)]'
					: 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)] hover:text-[var(--color-text-primary)]'}"
			>
				<span class="text-lg flex-shrink-0 w-6 text-center" aria-hidden="true">{item.icon}</span>
				{#if expanded}
					<span class="font-medium text-sm whitespace-nowrap overflow-hidden">{item.label}</span>
				{:else}
					<!-- Tooltip on hover when collapsed -->
					<span class="absolute left-full ml-2 px-2 py-1 bg-[var(--color-bg-tertiary)] text-[var(--color-text-primary)] text-xs font-medium rounded-lg shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
						{item.label}
					</span>
				{/if}
			</a>
		{/each}
	</nav>

	<!-- Footer -->
	<div class="p-2 border-t border-[var(--color-border-light)]">
		{#if expanded}
			<p class="text-xs text-[var(--color-text-tertiary)] text-center">v0.8.0</p>
		{/if}
	</div>
</aside>
