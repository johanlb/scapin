<script lang="ts">
	import '../app.css';
	import { Sidebar, MobileNav, ChatPanel, NotificationsPanel } from '$lib/components/layout';
	import {
		CommandPalette,
		ToastContainer,
		KeyboardShortcutsHelp,
		QuickActionsMenu
	} from '$lib/components/ui';
	import {
		showCommandPalette,
		openCommandPalette,
		closeCommandPalette,
		authStore,
		wsStore,
		notificationStore,
		notificationCenterStore,
		getQuickActions
	} from '$lib/stores';
	import {
		initializeShortcuts,
		isHelpVisible,
		registerShortcut
	} from '$lib/utils/keyboard-shortcuts';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';

	// Reactive state for help visibility
	let helpVisible = $state(false);

	// Reactive quick actions based on current page
	const quickActions = $derived(browser ? getQuickActions() : []);

	// Update help visibility reactively
	$effect(() => {
		if (browser) {
			const checkHelp = () => {
				helpVisible = isHelpVisible();
			};
			const interval = setInterval(checkHelp, 100);
			return () => clearInterval(interval);
		}
	});

	let { children } = $props();

	// Check if current route is login page
	const isLoginPage = $derived($page.url.pathname === '/login');

	// Cleanup functions for keyboard shortcuts
	let cleanupShortcuts: (() => void) | null = null;
	let unregisterSearch: (() => void) | null = null;

	// Initialize auth, service worker, notifications, and shortcuts
	onMount(() => {
		// Async initialization
		(async () => {
			// Initialize auth state
			await authStore.initialize();

			// Register service worker for PWA
			if (browser && 'serviceWorker' in navigator) {
				navigator.serviceWorker
					.register('/sw.js')
					.then((registration) => {
						console.log('[PWA] Service worker registered:', registration.scope);
					})
					.catch((error) => {
						console.error('[PWA] Service worker registration failed:', error);
					});
			}

			// Initialize push notifications and setup event listener
			await notificationStore.initialize();
			notificationStore.setupEventListener();

			// Initialize in-app notification center
			await notificationCenterStore.initialize();
		})();

		// Initialize keyboard shortcuts system (sync)
		cleanupShortcuts = initializeShortcuts();

		// Register global shortcuts
		unregisterSearch = registerShortcut({
			id: 'global-search',
			key: 'k',
			ctrl: true,
			description: 'Recherche globale',
			handler: openCommandPalette,
			global: true
		});

		// Cleanup on unmount
		return () => {
			cleanupShortcuts?.();
			unregisterSearch?.();
		};
	});

	// Auth guard: redirect to login if needed
	// Access state directly for proper Svelte 5 reactive tracking
	let lastRedirectTime = 0;
	$effect(() => {
		// Access state object directly for reactive tracking
		const authState = authStore.state;
		const shouldRedirect =
			browser &&
			authState.initialized &&
			authState.authRequired &&
			!authState.isAuthenticated &&
			!isLoginPage;
		console.log('[Layout] Auth effect:', {
			browser,
			initialized: authState.initialized,
			authRequired: authState.authRequired,
			isAuthenticated: authState.isAuthenticated,
			isLoginPage,
			shouldRedirect
		});
		if (shouldRedirect) {
			// Prevent redirect loops by checking if we just redirected
			const now = Date.now();
			if (now - lastRedirectTime < 1000) {
				console.warn('[Layout] Preventing redirect loop (too fast)');
				return;
			}
			lastRedirectTime = now;
			console.log('[Layout] Redirecting to /login');
			goto('/login');
		}
	});

	// Connect WebSocket when authenticated
	$effect(() => {
		const authState = authStore.state;
		if (browser && authState.initialized && authState.isAuthenticated && !isLoginPage) {
			wsStore.connect();
		}
	});

	// Cleanup WebSocket on unmount
	$effect(() => {
		return () => {
			if (browser) {
				wsStore.disconnect();
			}
		};
	});

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
	<meta name="description" content="Scapin - Votre valet de l'esprit, gardien cognitif personnel" />
	<link rel="manifest" href="/manifest.json" />
	<title>Scapin</title>
</svelte:head>

<!-- Show loading state while auth is initializing -->
{#if !authStore.state.initialized}
	<div
		class="min-h-screen min-h-[100dvh] bg-[var(--color-bg-primary)] flex items-center justify-center"
	>
		<div class="text-center">
			<div class="spinner mx-auto mb-4"></div>
			<p class="text-[var(--color-text-secondary)]">Chargement...</p>
		</div>
	</div>
	<!-- Login page has its own layout -->
{:else if isLoginPage}
	<div class="min-h-screen min-h-[100dvh] bg-[var(--color-bg-primary)] overflow-x-hidden relative">
		<!-- Ambient Background Gradient -->
		<div
			class="fixed inset-0 pointer-events-none opacity-30 dark:opacity-20"
			style="background: radial-gradient(ellipse 80% 50% at 50% -20%, var(--color-accent), transparent),
				radial-gradient(ellipse 60% 40% at 100% 100%, var(--color-event-omnifocus), transparent);"
		></div>
		{@render children()}
	</div>
	<!-- Main app layout -->
{:else}
	<div class="min-h-screen min-h-[100dvh] bg-[var(--color-bg-primary)] overflow-x-hidden relative">
		<!-- Ambient Background Gradient (Liquid Glass ambiance) -->
		<div
			class="fixed inset-0 pointer-events-none opacity-30 dark:opacity-20"
			style="background: radial-gradient(ellipse 80% 50% at 50% -20%, var(--color-accent), transparent),
				radial-gradient(ellipse 60% 40% at 100% 100%, var(--color-event-omnifocus), transparent);"
		></div>

		<!-- Desktop Sidebar (collapsed by default: w-16, expanded: w-56) -->
		<div class="layout-sidebar">
			<Sidebar />
		</div>

		<!-- Main Content - adapts to sidebar and chat panel -->
		<main
			class="layout-main md:ml-16 lg:mr-72 pb-20 md:pb-0 transition-[margin] duration-[var(--transition-normal)] ease-[var(--spring-fluid)] relative z-10"
		>
			{@render children()}
		</main>

		<!-- Desktop Chat Panel -->
		<div class="layout-chat-panel">
			<ChatPanel />
		</div>

		<!-- Notifications Panel (Desktop: slide-in from right, Mobile: slide-up) -->
		<NotificationsPanel />

		<!-- Mobile Bottom Nav -->
		<div class="layout-mobile-nav">
			<MobileNav />
		</div>

		<!-- Global Command Palette (Cmd+K) -->
		{#if $showCommandPalette}
			<CommandPalette onclose={closeCommandPalette} onselect={handleSearchSelect} />
		{/if}

		<!-- Toast Notifications -->
		<ToastContainer position="top-right" />

		<!-- Keyboard Shortcuts Help -->
		<KeyboardShortcutsHelp visible={helpVisible} />

		<!-- Quick Actions FAB (mobile only - desktop has sidebar) -->
		<div class="md:hidden">
			<QuickActionsMenu actions={quickActions} position="bottom-right" trigger="click" />
		</div>
	</div>
{/if}

<style>
	.spinner {
		width: 32px;
		height: 32px;
		border: 3px solid var(--color-border);
		border-top-color: var(--color-primary);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
