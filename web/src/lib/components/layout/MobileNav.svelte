<script lang="ts">
	import { page } from '$app/stores';
	import { haptic } from '$lib/utils/haptics';

	interface NavItem {
		href: string;
		label: string;
		icon: string;
	}

	const navItems: NavItem[] = [
		{ href: '/', label: 'Rapport', icon: '☀️' },
		{ href: '/flux', label: 'Courrier', icon: '📜' },
		{ href: '/notes', label: 'Carnets', icon: '📝' },
		{ href: '/chat', label: 'Scapin', icon: '🎭' },
		{ href: '/settings', label: 'Réglages', icon: '⚙️' }
	];

	function isActive(href: string, pathname: string): boolean {
		if (href === '/') {
			return pathname === '/';
		}
		return pathname.startsWith(href);
	}

	function handleClick() {
		haptic('light');
	}
</script>

<nav
	class="fixed bottom-0 left-0 right-0 glass-prominent border-t border-[var(--glass-border-subtle)] md:hidden z-50"
	style="padding-bottom: var(--safe-area-bottom);"
	aria-label="Navigation mobile"
	data-testid="mobile-nav"
>
	<div class="flex justify-around items-center h-16">
		{#each navItems as item}
			{@const active = isActive(item.href, $page.url.pathname)}
			<a
				href={item.href}
				onclick={handleClick}
				aria-current={active ? 'page' : undefined}
				class="flex flex-col items-center justify-center flex-1 py-2 touch-target liquid-press
					transition-all duration-[var(--transition-fast)] ease-[var(--spring-responsive)]
					{active
					? 'text-[var(--color-accent)]'
					: 'text-[var(--color-text-tertiary)] active:text-[var(--color-text-primary)]'}"
			>
				<span
					class="text-xl mb-0.5 transition-transform duration-[var(--transition-fast)] ease-[var(--spring-bouncy)]
						{active ? 'scale-110' : ''}"
					aria-hidden="true"
				>{item.icon}</span>
				<span class="text-[10px] font-medium">{item.label}</span>
				{#if active}
					<span class="absolute bottom-1 w-1 h-1 rounded-full bg-[var(--color-accent)]"></span>
				{/if}
			</a>
		{/each}
	</div>
</nav>
