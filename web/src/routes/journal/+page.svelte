<script lang="ts">
	import { Card, Button, Badge } from '$lib/components/ui';
	import { getJournal, answerQuestion, completeJournal, type JournalEntry } from '$lib/api/client';

	// State
	let journal = $state<JournalEntry | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let activeTab = $state<'email' | 'teams' | 'calendar' | 'omnifocus' | 'questions'>('email');
	let selectedDate = $state(new Date().toISOString().split('T')[0]);
	let answeringQuestion = $state<string | null>(null);

	// Load journal on mount and when date changes
	$effect(() => {
		loadJournal(selectedDate);
	});

	async function loadJournal(date: string) {
		loading = true;
		error = null;
		try {
			journal = await getJournal(date, true);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Erreur de chargement';
			journal = null;
		} finally {
			loading = false;
		}
	}

	async function handleAnswer(questionId: string, answer: string) {
		if (!journal) return;
		answeringQuestion = questionId;
		try {
			journal = await answerQuestion(selectedDate, questionId, answer);
		} catch (e) {
			console.error('Failed to answer question:', e);
		} finally {
			answeringQuestion = null;
		}
	}

	async function handleComplete() {
		if (!journal) return;
		try {
			journal = await completeJournal(selectedDate);
		} catch (e) {
			console.error('Failed to complete journal:', e);
		}
	}

	function formatDate(isoString: string): string {
		return new Date(isoString).toLocaleDateString('fr-FR', {
			weekday: 'long',
			day: 'numeric',
			month: 'long'
		});
	}

	function formatTime(isoString: string): string {
		return new Date(isoString).toLocaleTimeString('fr-FR', {
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function getConfidenceColor(confidence: number): string {
		if (confidence >= 90) return 'var(--color-success)';
		if (confidence >= 70) return 'var(--color-warning)';
		return 'var(--color-error)';
	}

	function getStatusBadge(status: string): { label: string; color: string } {
		switch (status) {
			case 'completed':
				return { label: 'Terminé', color: 'var(--color-success)' };
			case 'in_progress':
				return { label: 'En cours', color: 'var(--color-warning)' };
			default:
				return { label: 'Brouillon', color: 'var(--color-text-secondary)' };
		}
	}

	function getTaskStatusColor(status: string): string {
		switch (status) {
			case 'completed':
				return 'var(--color-success)';
			case 'overdue':
				return 'var(--color-error)';
			default:
				return 'var(--color-text-secondary)';
		}
	}

	function getCategoryLabel(category: string): string {
		const labels: Record<string, string> = {
			low_confidence: 'Confiance basse',
			new_person: 'Nouveau contact',
			action_verify: 'Vérification',
			clarification: 'Clarification',
			pattern_confirm: 'Pattern détecté',
			preference_learn: 'Préférence',
			calibration_check: 'Calibration',
			priority_review: 'Priorité'
		};
		return labels[category] || category;
	}

	// Computed values
	let unansweredQuestions = $derived(journal?.questions.filter((q) => !q.answer) || []);

	let tabs = $derived([
		{ id: 'email', label: 'Emails', count: journal?.emails_count || 0, icon: '📧' },
		{ id: 'teams', label: 'Teams', count: journal?.teams_count || 0, icon: '💬' },
		{ id: 'calendar', label: 'Calendrier', count: journal?.calendar_count || 0, icon: '📅' },
		{ id: 'omnifocus', label: 'OmniFocus', count: journal?.omnifocus_count || 0, icon: '✅' },
		{ id: 'questions', label: 'Questions', count: unansweredQuestions.length, icon: '❓' }
	]);

	let statusBadge = $derived(journal ? getStatusBadge(journal.status) : null);
</script>

<div class="p-4 md:p-6 max-w-5xl mx-auto">
	<!-- Header -->
	<header class="mb-6">
		<div class="flex items-center justify-between mb-2">
			<h1 class="text-2xl md:text-3xl font-bold text-[var(--color-text-primary)]">Journal</h1>
			<input
				type="date"
				bind:value={selectedDate}
				class="px-3 py-2 rounded-lg bg-[var(--color-bg-secondary)] border border-[var(--color-border)] text-[var(--color-text-primary)]"
			/>
		</div>
		<p class="text-[var(--color-text-secondary)]">
			{formatDate(selectedDate)} — Scapin prend note pour vous
		</p>
	</header>

	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div
				class="animate-spin w-8 h-8 border-2 border-[var(--color-primary)] border-t-transparent rounded-full"
			></div>
		</div>
	{:else if error}
		<Card padding="lg">
			<div class="text-center py-8">
				<p class="text-[var(--color-error)] mb-4">{error}</p>
				<Button variant="primary" onclick={() => loadJournal(selectedDate)}>Réessayer</Button>
			</div>
		</Card>
	{:else if journal}
		<!-- Stats Bar -->
		<div class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
			<Card padding="sm">
				<div class="text-center">
					<div class="text-2xl font-bold text-[var(--color-text-primary)]">
						{journal.emails_count}
					</div>
					<div class="text-xs text-[var(--color-text-secondary)]">Emails</div>
				</div>
			</Card>
			<Card padding="sm">
				<div class="text-center">
					<div class="text-2xl font-bold text-[var(--color-text-primary)]">
						{journal.teams_count}
					</div>
					<div class="text-xs text-[var(--color-text-secondary)]">Teams</div>
				</div>
			</Card>
			<Card padding="sm">
				<div class="text-center">
					<div class="text-2xl font-bold text-[var(--color-text-primary)]">
						{journal.calendar_count}
					</div>
					<div class="text-xs text-[var(--color-text-secondary)]">Réunions</div>
				</div>
			</Card>
			<Card padding="sm">
				<div class="text-center">
					<div class="text-2xl font-bold text-[var(--color-text-primary)]">
						{journal.omnifocus_count}
					</div>
					<div class="text-xs text-[var(--color-text-secondary)]">Tâches</div>
				</div>
			</Card>
			<Card padding="sm">
				<div class="text-center">
					<div
						class="text-2xl font-bold"
						style="color: {getConfidenceColor(journal.average_confidence)}"
					>
						{journal.average_confidence.toFixed(0)}%
					</div>
					<div class="text-xs text-[var(--color-text-secondary)]">Confiance</div>
				</div>
			</Card>
		</div>

		<!-- Status and Actions -->
		<div class="flex items-center justify-between mb-6">
			<div class="flex items-center gap-3">
				{#if statusBadge}
					<span
						class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
						style="background: {statusBadge.color}20; color: {statusBadge.color}"
					>
						{statusBadge.label}
					</span>
				{/if}
				{#if unansweredQuestions.length > 0}
					<span class="text-sm text-[var(--color-warning)]">
						{unansweredQuestions.length} question(s) en attente
					</span>
				{/if}
			</div>
			{#if journal.status !== 'completed' && unansweredQuestions.length === 0}
				<Button variant="primary" onclick={handleComplete}>Terminer le journal</Button>
			{/if}
		</div>

		<!-- Tabs -->
		<div class="flex gap-1 mb-4 overflow-x-auto pb-2">
			{#each tabs as tab}
				<button
					class="flex items-center gap-2 px-4 py-2 rounded-lg whitespace-nowrap transition-colors {activeTab ===
					tab.id
						? 'bg-[var(--color-primary)] text-white'
						: 'bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-tertiary)]'}"
					onclick={() => (activeTab = tab.id as typeof activeTab)}
				>
					<span>{tab.icon}</span>
					<span>{tab.label}</span>
					{#if tab.count > 0}
						<span
							class="px-1.5 py-0.5 text-xs rounded-full {activeTab === tab.id
								? 'bg-white/20'
								: 'bg-[var(--color-bg-tertiary)]'}"
						>
							{tab.count}
						</span>
					{/if}
				</button>
			{/each}
		</div>

		<!-- Tab Content -->
		<div class="space-y-3">
			{#if activeTab === 'email'}
				{#if journal.emails_processed.length === 0}
					<Card padding="lg">
						<p class="text-center text-[var(--color-text-secondary)]">Aucun email traité</p>
					</Card>
				{:else}
					{#each journal.emails_processed as email (email.email_id)}
						<Card padding="md">
							<div class="flex items-start gap-3">
								<div
									class="w-10 h-10 rounded-full bg-[var(--color-bg-tertiary)] flex items-center justify-center text-lg"
								>
									📧
								</div>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 mb-1">
										<span class="font-medium text-[var(--color-text-primary)] truncate">
											{email.from_name || email.from_address}
										</span>
										<Badge variant="default">{email.action}</Badge>
										<span
											class="text-xs px-2 py-0.5 rounded"
											style="background: {getConfidenceColor(
												email.confidence
											)}20; color: {getConfidenceColor(email.confidence)}"
										>
											{email.confidence}%
										</span>
									</div>
									<p class="text-sm text-[var(--color-text-primary)] truncate">{email.subject}</p>
									<p class="text-xs text-[var(--color-text-tertiary)] mt-1">
										{email.category} • {formatTime(email.processed_at)}
									</p>
								</div>
							</div>
						</Card>
					{/each}
				{/if}
			{:else if activeTab === 'teams'}
				{#if journal.teams_messages.length === 0}
					<Card padding="lg">
						<p class="text-center text-[var(--color-text-secondary)]">Aucun message Teams</p>
					</Card>
				{:else}
					{#each journal.teams_messages as msg (msg.message_id)}
						<Card padding="md">
							<div class="flex items-start gap-3">
								<div
									class="w-10 h-10 rounded-full bg-[var(--color-bg-tertiary)] flex items-center justify-center text-lg"
								>
									💬
								</div>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 mb-1">
										<span class="font-medium text-[var(--color-text-primary)]">{msg.sender}</span>
										<span class="text-xs text-[var(--color-text-tertiary)]"
											>dans {msg.chat_name}</span
										>
									</div>
									<p class="text-sm text-[var(--color-text-secondary)] line-clamp-2">
										{msg.preview}
									</p>
									<div class="flex items-center gap-2 mt-1">
										<Badge variant="default">{msg.action}</Badge>
										<span class="text-xs text-[var(--color-text-tertiary)]"
											>{formatTime(msg.processed_at)}</span
										>
									</div>
								</div>
							</div>
						</Card>
					{/each}
				{/if}
			{:else if activeTab === 'calendar'}
				{#if journal.calendar_events.length === 0}
					<Card padding="lg">
						<p class="text-center text-[var(--color-text-secondary)]">Aucun événement calendrier</p>
					</Card>
				{:else}
					{#each journal.calendar_events as event (event.event_id)}
						<Card padding="md">
							<div class="flex items-start gap-3">
								<div
									class="w-10 h-10 rounded-full bg-[var(--color-bg-tertiary)] flex items-center justify-center text-lg"
								>
									📅
								</div>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 mb-1">
										<span class="font-medium text-[var(--color-text-primary)]">{event.title}</span>
										{#if event.is_online}
											<Badge variant="default">En ligne</Badge>
										{/if}
									</div>
									<p class="text-sm text-[var(--color-text-secondary)]">
										{formatTime(event.start_time)} - {formatTime(event.end_time)}
									</p>
									{#if event.attendees.length > 0}
										<p class="text-xs text-[var(--color-text-tertiary)] mt-1">
											{event.attendees.length} participant(s)
										</p>
									{/if}
									{#if event.location}
										<p class="text-xs text-[var(--color-text-tertiary)]">{event.location}</p>
									{/if}
								</div>
							</div>
						</Card>
					{/each}
				{/if}
			{:else if activeTab === 'omnifocus'}
				{#if journal.omnifocus_items.length === 0}
					<Card padding="lg">
						<p class="text-center text-[var(--color-text-secondary)]">Aucune activité OmniFocus</p>
					</Card>
				{:else}
					{#each journal.omnifocus_items as task (task.task_id)}
						<Card padding="md">
							<div class="flex items-start gap-3">
								<div
									class="w-10 h-10 rounded-full flex items-center justify-center text-lg {task.status ===
									'completed'
										? 'bg-[var(--color-success)]/10'
										: 'bg-[var(--color-bg-tertiary)]'}"
								>
									{task.status === 'completed' ? '✅' : task.flagged ? '🚩' : '⏳'}
								</div>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 mb-1">
										<span
											class="font-medium text-[var(--color-text-primary)] {task.status ===
											'completed'
												? 'line-through opacity-60'
												: ''}"
										>
											{task.title}
										</span>
										<span
											class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
											style="background: {getTaskStatusColor(
												task.status
											)}20; color: {getTaskStatusColor(task.status)}"
										>
											{task.status}
										</span>
									</div>
									{#if task.project}
										<p class="text-sm text-[var(--color-text-secondary)]">{task.project}</p>
									{/if}
									<div class="flex items-center gap-2 mt-1 flex-wrap">
										{#each task.tags as tag}
											<span class="text-xs px-2 py-0.5 bg-[var(--color-bg-tertiary)] rounded"
												>{tag}</span
											>
										{/each}
										{#if task.estimated_minutes}
											<span class="text-xs text-[var(--color-text-tertiary)]"
												>{task.estimated_minutes}min</span
											>
										{/if}
									</div>
								</div>
							</div>
						</Card>
					{/each}
				{/if}
			{:else if activeTab === 'questions'}
				{#if journal.questions.length === 0}
					<Card padding="lg">
						<p class="text-center text-[var(--color-text-secondary)]">Aucune question</p>
					</Card>
				{:else}
					{#each journal.questions as question (question.question_id)}
						<Card padding="md" class={question.answer ? 'opacity-60' : ''}>
							<div class="space-y-3">
								<div class="flex items-start gap-3">
									<div
										class="w-10 h-10 rounded-full bg-[var(--color-primary)]/10 flex items-center justify-center text-lg"
									>
										❓
									</div>
									<div class="flex-1">
										<div class="flex items-center gap-2 mb-2">
											<Badge>{getCategoryLabel(question.category)}</Badge>
											{#if question.answer}
												<span
													class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[var(--color-success)]/10 text-[var(--color-success)]"
												>
													Répondu
												</span>
											{/if}
										</div>
										<p class="font-medium text-[var(--color-text-primary)]">
											{question.question_text}
										</p>
										{#if question.context}
											<p class="text-sm text-[var(--color-text-secondary)] mt-1">
												{question.context}
											</p>
										{/if}
									</div>
								</div>

								{#if question.answer}
									<div class="ml-13 pl-3 border-l-2 border-[var(--color-success)]">
										<p class="text-sm text-[var(--color-text-primary)]">
											<span class="text-[var(--color-text-tertiary)]">Réponse:</span>
											{question.answer}
										</p>
									</div>
								{:else}
									<div class="flex flex-wrap gap-2 ml-13">
										{#each question.options as option}
											<Button
												variant="secondary"
												size="sm"
												disabled={answeringQuestion === question.question_id}
												onclick={() => handleAnswer(question.question_id, option)}
											>
												{answeringQuestion === question.question_id ? '...' : option}
											</Button>
										{/each}
									</div>
								{/if}
							</div>
						</Card>
					{/each}
				{/if}
			{/if}
		</div>
	{/if}
</div>

<style>
	.ml-13 {
		margin-left: 3.25rem;
	}
</style>
