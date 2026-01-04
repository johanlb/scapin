<script lang="ts">
	import { page } from '$app/stores';
	import { haptic } from '$lib/utils/haptics';

	interface NavItem {
		href: string;
		label: string;
		icon: string;
	}

	const navItems: NavItem[] = [
		{ href: '/', label: 'Briefing', icon: '☀️' },
		{ href: '/flux', label: 'Flux', icon: '📥' },
		{ href: '/notes', label: 'Notes', icon: '📝' },
		{ href: '/chat', label: 'Chat', icon: '💬' },
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
	class="fixed bottom-0 left-0 right-0 glass border-t border-[var(--glass-border)] md:hidden z-50"
	style="padding-bottom: var(--safe-area-bottom);"
	aria-label="Navigation mobile"
>
	<div class="flex justify-around items-center h-16">
		{#each navItems as item}
			{@const active = isActive(item.href, $page.url.pathname)}
			<a
				href={item.href}
				onclick={handleClick}
				aria-current={active ? 'page' : undefined}
				class="flex flex-col items-center justify-center flex-1 py-2 touch-target transition-all
                       {active ? 'text-[var(--color-accent)]' : 'text-[var(--color-text-tertiary)]'}"
			>
				<span class="text-xl mb-0.5" aria-hidden="true">{item.icon}</span>
				<span class="text-[10px] font-medium">{item.label}</span>
			</a>
		{/each}
	</div>
</nav>
