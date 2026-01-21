<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Button, Tabs } from '$lib/components/ui';
	import { queueStore } from '$lib/stores';
	import { queueWsStore } from '$lib/stores/queueWebsocket.svelte';
	import { toastStore } from '$lib/stores/toast.svelte';
	import { processInbox, approveQueueItem, reanalyzeQueueItem } from '$lib/api';
	import type { QueueItem, ActionOption } from '$lib/api';
	import QueueItemFocusView from '$lib/components/peripeties/QueueItemFocusView.svelte';
	import QueueItemListView from '$lib/components/peripeties/QueueItemListView.svelte';

	type TabFilter = 'to_process' | 'in_progress' | 'snoozed' | 'history' | 'errors';
	let activeTab = $state<TabFilter>('to_process');
	let currentIndex = $state(0);
	let selectedItemId = $state<string | null>(null);
	let isFetching = $state(false);
	let showDetails = $state(false);

	const tabs = $derived([
		{
			id: 'to_process',
			label: 'À traiter',
			icon: '📥',
			badge: queueStore.stats?.by_tab?.to_process
		},
		{
			id: 'in_progress',
			label: 'En cours',
			icon: '⏳',
			badge: queueStore.stats?.by_tab?.in_progress
		},
		{ id: 'snoozed', label: 'Attente', icon: '⏰', badge: queueStore.stats?.by_tab?.snoozed },
		{ id: 'history', label: 'Historique', icon: '📜', badge: queueStore.stats?.by_tab?.history },
		{ id: 'errors', label: 'Erreurs', icon: '⚠️', badge: queueStore.stats?.by_tab?.errors }
	]);

	const currentItem = $derived(
		activeTab === 'to_process'
			? queueStore.items[currentIndex] || null
			: queueStore.items.find((i) => i.id === selectedItemId) || null
	);

	onMount(async () => {
		await loadTab(activeTab);
		await queueStore.fetchStats();
		queueWsStore.connect();
	});

	onDestroy(() => {
		queueWsStore.disconnect();
	});

	async function loadTab(tab: TabFilter) {
		currentIndex = 0;
		selectedItemId = null;
		await queueStore.fetchQueueByTab(tab);
	}

	async function handleTabChange(tabId: string) {
		activeTab = tabId as TabFilter;
		await loadTab(activeTab);
	}

	async function handleFetch() {
		isFetching = true;
		try {
			await processInbox(20, false);
			await loadTab(activeTab);
			await queueStore.fetchStats();
			toastStore.success('Emails récupérés');
		} catch (e) {
			toastStore.error('Erreur de récupération');
		} finally {
			isFetching = false;
		}
	}

	async function handleSelectOption(item: QueueItem, option: ActionOption) {
		if (activeTab === 'to_process') {
			queueStore.removeFromList(item.id);
		}
		try {
			await approveQueueItem(item.id, option.action);
			toastStore.success('Action effectuée');
			await queueStore.fetchStats();
		} catch (e) {
			if (activeTab === 'to_process') {
				queueStore.restoreItem(item);
			}
			toastStore.error('Erreur');
		}
	}

	function handleSkip() {
		currentIndex = (currentIndex + 1) % queueStore.items.length;
	}

	function handleSelectItem(item: QueueItem) {
		selectedItemId = item.id;
	}

	function handleBackToList() {
		selectedItemId = null;
	}
</script>

<div class="p-4 md:p-6 max-w-4xl mx-auto min-h-screen">
	<header class="flex justify-between items-center mb-6">
		<h1
			class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60"
		>
			Péripéties
		</h1>
		<Button variant="secondary" size="sm" onclick={handleFetch} disabled={isFetching}>
			{isFetching ? '...' : '📥 Récupérer'}
		</Button>
	</header>

	<div class="mb-8 overflow-x-auto no-scrollbar pb-2">
		<Tabs {tabs} bind:activeTab variant="pills" size="sm" onchange={(id) => handleTabChange(id)} />
	</div>

	{#if queueStore.loading && queueStore.items.length === 0}
		<div class="flex flex-col items-center justify-center p-24 gap-4">
			<div
				class="w-12 h-12 border-4 border-[var(--color-accent)]/20 border-t-[var(--color-accent)] rounded-full animate-spin"
			></div>
			<p class="text-sm opacity-50 animate-pulse">Chargement des péripéties...</p>
		</div>
	{:else if queueStore.items.length === 0}
		<div class="text-center p-16 glass rounded-[2rem] border border-white/5">
			<p class="text-5xl mb-6">✨</p>
			<h2 class="text-xl font-bold mb-2">Tout est calme</h2>
			<p class="text-sm opacity-50 max-w-xs mx-auto">
				Il n'y a aucune péripétie dans cette catégorie pour le moment.
			</p>
		</div>
	{:else if activeTab === 'to_process'}
		{#if currentItem}
			<QueueItemFocusView
				item={currentItem}
				{showDetails}
				onSelectOption={handleSelectOption}
				onDelete={(item: QueueItem) => handleSelectOption(item, { action: 'delete' } as any)}
				onReanalyze={(item: QueueItem) => reanalyzeQueueItem(item.id)}
				onSkip={handleSkip}
			/>
			<div
				class="mt-6 flex justify-center text-[10px] opacity-30 font-mono tracking-widest uppercase"
			>
				{currentIndex + 1} / {queueStore.items.length} ELÉMENTS
			</div>
		{/if}
	{:else if currentItem}
		<div class="mb-6">
			<Button variant="ghost" size="sm" onclick={handleBackToList} class="mb-4">
				← Retour à la liste
			</Button>
			<QueueItemFocusView
				item={currentItem}
				{showDetails}
				onSelectOption={handleSelectOption}
				onDelete={(item: QueueItem) => handleSelectOption(item, { action: 'delete' } as any)}
				onReanalyze={(item: QueueItem) => reanalyzeQueueItem(item.id)}
				onSkip={handleBackToList}
			/>
		</div>
	{:else}
		<QueueItemListView items={queueStore.items} onSelectItem={handleSelectItem} />
	{/if}
</div>
