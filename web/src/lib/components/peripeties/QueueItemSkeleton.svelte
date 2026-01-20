<script lang="ts">
	/**
	 * QueueItemSkeleton Component (v2.4)
	 * Skeleton placeholder for queue item cards during loading
	 */
	import { Skeleton, Card } from '$lib/components/ui';
</script>

<div class="pb-3">
	<Card padding="md">
		<div class="flex items-start gap-3">
			<!-- Action icon skeleton -->
			<Skeleton variant="rectangular" width="40px" height="40px" class="rounded-lg shrink-0" />

			<div class="flex-1 min-w-0">
				<!-- Subject skeleton -->
				<Skeleton variant="text" width="70%" height="1.25rem" class="mb-2" />

				<!-- Sender and date skeleton -->
				<Skeleton variant="text" width="50%" height="0.75rem" class="mb-2" />

				<!-- Summary skeleton (2 lines) -->
				<Skeleton variant="text" lines={2} height="0.75rem" />
			</div>
		</div>
	</Card>
</div>
