<script lang="ts">
	import '../app.css';
	import { Sidebar, MobileNav, ChatPanel } from '$lib/components/layout';
	import { CommandPalette } from '$lib/components/ui';
	import { showCommandPalette, openCommandPalette, closeCommandPalette } from '$lib/stores';
	import { goto } from '$app/navigation';

	let { children } = $props();

	function handleKeydown(event: KeyboardEvent) {
		// Cmd+K (Mac) or Ctrl+K (Windows/Linux)
		if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
			event.preventDefault();
			openCommandPalette();
		}
	}

	function handleSearchSelect(result: { id: string; type: string; title: string }) {
		// Navigate based on result type
		const routes: Record<string, string> = {
			note: '/notes',
			email: '/flux',
			event: '/flux',
			task: '/',
			discussion: '/discussions'
		};
		const route = routes[result.type] || '/';
		goto(`${route}?id=${result.id}`);
		console.log('Selected:', result);
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<svelte:head>
	<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
	<meta name="theme-color" content="#000000" media="(prefers-color-scheme: dark)" />
	<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)" />
	<meta name="apple-mobile-web-app-capable" content="yes" />
	<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
	<title>Scapin</title>
</svelte:head>

<div class="min-h-screen min-h-[100dvh] bg-[var(--color-bg-primary)] overflow-x-hidden relative">
	<!-- Ambient Background Gradient (Liquid Glass ambiance) -->
	<div
		class="fixed inset-0 pointer-events-none opacity-30 dark:opacity-20"
		style="background: radial-gradient(ellipse 80% 50% at 50% -20%, var(--color-accent), transparent),
			radial-gradient(ellipse 60% 40% at 100% 100%, var(--color-event-omnifocus), transparent);"
	></div>

	<!-- Desktop Sidebar (collapsed by default: w-16, expanded: w-56) -->
	<Sidebar />

	<!-- Main Content - adapts to sidebar and chat panel -->
	<main class="md:ml-16 lg:mr-72 pb-20 md:pb-0 transition-[margin] duration-[var(--transition-normal)] ease-[var(--spring-fluid)] relative z-10">
		{@render children()}
	</main>

	<!-- Desktop Chat Panel -->
	<ChatPanel />

	<!-- Mobile Bottom Nav -->
	<MobileNav />

	<!-- Global Command Palette (Cmd+K) -->
	{#if $showCommandPalette}
		<CommandPalette
			onclose={closeCommandPalette}
			onselect={handleSearchSelect}
		/>
	{/if}
</div>
