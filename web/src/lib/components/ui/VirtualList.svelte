<!--
  VirtualList.svelte

  A high-performance virtualized list component using @tanstack/svelte-virtual.
  Only renders items that are visible in the viewport + overscan buffer.

  Features:
  - Infinite scroll with IntersectionObserver
  - Dynamic item heights support
  - Loading states
  - Customizable via snippets

  Usage:
  <VirtualList
    items={emails}
    estimatedItemHeight={120}
    onLoadMore={() => queueStore.loadMore()}
    hasMore={queueStore.hasMore}
    loading={queueStore.loading}
  >
    {#snippet item(email, index)}
      <EmailCard {email} />
    {/snippet}
  </VirtualList>
-->
<script lang="ts" generics="T">
	import { createVirtualizer, type VirtualItem } from '@tanstack/svelte-virtual';
	import { onMount, type Snippet } from 'svelte';

	// Props
	interface Props {
		/** Array of items to virtualize */
		items: T[];
		/** Estimated height of each item in pixels */
		estimatedItemHeight?: number;
		/** Number of items to render outside visible area */
		overscan?: number;
		/** Callback when more items should be loaded */
		onLoadMore?: () => void | Promise<void>;
		/** Whether more items are available */
		hasMore?: boolean;
		/** Whether currently loading more items */
		loading?: boolean;
		/** Threshold in pixels before bottom to trigger load */
		loadThreshold?: number;
		/** Height of the list container (CSS value) */
		height?: string;
		/** Key extractor function */
		getKey?: (item: T, index: number) => string | number;
		/** Snippet for rendering each item */
		item: Snippet<[T, number, VirtualItem]>;
		/** Snippet for empty state */
		empty?: Snippet;
		/** Snippet for loading indicator at bottom */
		loadingIndicator?: Snippet;
	}

	let {
		items,
		estimatedItemHeight = 100,
		overscan: overscanProp = 5,
		onLoadMore,
		hasMore = false,
		loading = false,
		loadThreshold = 200,
		height = '100%',
		getKey = (_item: T, index: number) => index,
		item: itemSnippet,
		empty: emptySnippet,
		loadingIndicator: loadingSnippet
	}: Props = $props();

	// Scroll container reference
	let scrollContainer: HTMLDivElement | null = $state(null);

	// Sentinel element for infinite scroll
	let sentinelRef: HTMLDivElement | null = $state(null);
	let observer: IntersectionObserver | null = null;

	// Guard against multiple rapid onLoadMore calls
	let isLoadingMore = $state(false);

	// Store the current items count reactively
	const itemsCount = $derived(items.length);

	// Create virtualizer store with initial options
	// Options are updated reactively via $effect (including overscan)
	const virtualizer = createVirtualizer<HTMLDivElement, HTMLDivElement>({
		count: 0,
		getScrollElement: () => scrollContainer,
		estimateSize: () => estimatedItemHeight
	});

	// Update virtualizer when items or options change
	$effect(() => {
		$virtualizer.setOptions({
			count: itemsCount,
			overscan: overscanProp,
			estimateSize: () => estimatedItemHeight,
			getItemKey: (index) => {
				const item = items[index];
				return item ? getKey(item, index) : index;
			}
		});
	});

	// Setup IntersectionObserver for infinite scroll
	onMount(() => {
		return () => {
			observer?.disconnect();
		};
	});

	// Handler for intersection - checks current values at call time
	async function handleIntersection(entries: IntersectionObserverEntry[]) {
		const entry = entries[0];
		if (!entry?.isIntersecting) return;

		// Check conditions at call time (not captured at observer creation)
		if (!hasMore || loading || isLoadingMore || !onLoadMore) return;

		// Guard against rapid multiple calls
		isLoadingMore = true;
		try {
			await onLoadMore();
		} finally {
			isLoadingMore = false;
		}
	}

	// Observe sentinel when it changes
	// Note: We only recreate observer when sentinel/container/threshold change
	// The callback reads hasMore/loading/onLoadMore at call time
	$effect(() => {
		if (sentinelRef && scrollContainer) {
			observer?.disconnect();

			observer = new IntersectionObserver(handleIntersection, {
				root: scrollContainer,
				rootMargin: `0px 0px ${loadThreshold}px 0px`,
				threshold: 0
			});

			observer.observe(sentinelRef);
		}
	});

	// Get virtual items from the store
	const virtualItems = $derived($virtualizer.getVirtualItems());
	const totalSize = $derived($virtualizer.getTotalSize());
</script>

<div
	bind:this={scrollContainer}
	class="virtual-list-container"
	style:height
	style:overflow="auto"
	style:position="relative"
	data-testid="virtual-list-container"
	aria-busy={loading}
	role="feed"
	aria-label="Liste virtualisée"
>
	{#if items.length === 0 && !loading}
		<!-- Empty state -->
		{#if emptySnippet}
			{@render emptySnippet()}
		{:else}
			<div class="empty-state">
				<p>Aucun élément à afficher</p>
			</div>
		{/if}
	{:else}
		<!-- Virtual list container with total height -->
		<div
			class="virtual-list-inner"
			style:height="{totalSize}px"
			style:width="100%"
			style:position="relative"
		>
			<!-- Rendered virtual items -->
			{#each virtualItems as virtualItem (virtualItem.key)}
				{@const itemData = items[virtualItem.index]}
				{#if itemData}
					<div
						class="virtual-list-item"
						style:position="absolute"
						style:top="0"
						style:left="0"
						style:width="100%"
						style:transform="translateY({virtualItem.start}px)"
						data-index={virtualItem.index}
						data-testid="virtual-list-item"
					>
						{@render itemSnippet(itemData, virtualItem.index, virtualItem)}
					</div>
				{/if}
			{/each}
		</div>

		<!-- Sentinel for infinite scroll (positioned after last item) -->
		<div
			bind:this={sentinelRef}
			class="virtual-list-sentinel"
			style:position="absolute"
			style:top="{totalSize}px"
			style:left="0"
			style:width="100%"
			style:height="1px"
			aria-hidden="true"
		></div>

		<!-- Loading indicator -->
		{#if loading}
			<div
				class="virtual-list-loading"
				style:position={totalSize > 0 ? 'absolute' : 'relative'}
				style:top={totalSize > 0 ? `${totalSize + 8}px` : 'auto'}
				style:padding-top={totalSize === 0 ? '2rem' : '0'}
				data-testid="virtual-list-loading"
				role="status"
				aria-live="polite"
			>
				{#if loadingSnippet}
					{@render loadingSnippet()}
				{:else}
					<div class="loading-spinner">
						<div class="spinner" aria-hidden="true"></div>
						<span>Chargement...</span>
					</div>
				{/if}
			</div>
		{/if}
	{/if}
</div>

<style>
	.virtual-list-container {
		scrollbar-width: thin;
		scrollbar-color: var(--color-border) transparent;
	}

	.virtual-list-container::-webkit-scrollbar {
		width: 6px;
	}

	.virtual-list-container::-webkit-scrollbar-track {
		background: transparent;
	}

	.virtual-list-container::-webkit-scrollbar-thumb {
		background-color: var(--color-border);
		border-radius: 3px;
	}

	.empty-state {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 100%;
		color: var(--color-text-secondary);
	}

	.loading-spinner {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 1rem;
		color: var(--color-text-secondary);
		font-size: 0.875rem;
	}

	.spinner {
		width: 1.25rem;
		height: 1.25rem;
		border: 2px solid var(--color-border);
		border-top-color: var(--color-accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Reduce motion preference */
	@media (prefers-reduced-motion: reduce) {
		.spinner {
			animation-duration: 1.5s;
		}
	}
</style>
