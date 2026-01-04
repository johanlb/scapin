<script lang="ts">
	import { goto } from '$app/navigation';
	import { authStore } from '$lib/stores';

	let pin = $state('');
	let showPin = $state(false);
	let inputRef: HTMLInputElement;

	async function handleSubmit(e: Event) {
		e.preventDefault();
		const success = await authStore.login(pin);
		if (success) {
			goto('/');
		}
	}

	function handleKeypadPress(digit: string) {
		if (pin.length < 6) {
			pin += digit;
		}
	}

	function handleBackspace() {
		pin = pin.slice(0, -1);
	}

	function handleClear() {
		pin = '';
	}

	// Focus input on mount
	$effect(() => {
		if (inputRef) {
			inputRef.focus();
		}
	});
</script>

<svelte:head>
	<title>Connexion - Scapin</title>
</svelte:head>

<div class="login-container">
	<div class="login-card">
		<!-- Logo / Title -->
		<div class="login-header">
			<div class="logo">
				<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
					<path d="M12 2L2 7l10 5 10-5-10-5z"/>
					<path d="M2 17l10 5 10-5"/>
					<path d="M2 12l10 5 10-5"/>
				</svg>
			</div>
			<h1>Scapin</h1>
			<p class="subtitle">Gardien cognitif personnel</p>
		</div>

		<!-- Error message -->
		{#if authStore.error}
			<div class="error-message">
				{authStore.error}
				<button type="button" class="error-dismiss" onclick={() => authStore.clearError()} aria-label="Fermer l'erreur">
					<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M18 6L6 18M6 6l12 12"/>
					</svg>
				</button>
			</div>
		{/if}

		<!-- PIN Form -->
		<form onsubmit={handleSubmit}>
			<div class="pin-input-wrapper">
				<input
					bind:this={inputRef}
					type={showPin ? 'text' : 'password'}
					bind:value={pin}
					maxlength={6}
					minlength={4}
					pattern="[0-9]*"
					inputmode="numeric"
					autocomplete="off"
					placeholder="PIN (4-6 chiffres)"
					class="pin-input"
					disabled={authStore.loading}
				/>
				<button
					type="button"
					class="toggle-visibility"
					onclick={() => showPin = !showPin}
					aria-label={showPin ? 'Masquer le PIN' : 'Afficher le PIN'}
				>
					{#if showPin}
						<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
							<line x1="1" y1="1" x2="23" y2="23"/>
						</svg>
					{:else}
						<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
							<circle cx="12" cy="12" r="3"/>
						</svg>
					{/if}
				</button>
			</div>

			<!-- PIN dots indicator -->
			<div class="pin-dots">
				{#each Array(6) as _, i}
					<div class="dot" class:filled={i < pin.length}></div>
				{/each}
			</div>

			<!-- Keypad for mobile -->
			<div class="keypad">
				{#each ['1', '2', '3', '4', '5', '6', '7', '8', '9'] as digit}
					<button
						type="button"
						class="keypad-btn"
						onclick={() => handleKeypadPress(digit)}
						disabled={authStore.loading}
					>
						{digit}
					</button>
				{/each}
				<button type="button" class="keypad-btn action" onclick={handleClear} disabled={authStore.loading}>
					C
				</button>
				<button
					type="button"
					class="keypad-btn"
					onclick={() => handleKeypadPress('0')}
					disabled={authStore.loading}
				>
					0
				</button>
				<button type="button" class="keypad-btn action" onclick={handleBackspace} disabled={authStore.loading} aria-label="Effacer">
					<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M21 4H8l-7 8 7 8h13a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2z"/>
						<line x1="18" y1="9" x2="12" y2="15"/>
						<line x1="12" y1="9" x2="18" y2="15"/>
					</svg>
				</button>
			</div>

			<!-- Submit button -->
			<button type="submit" class="submit-btn" disabled={pin.length < 4 || authStore.loading}>
				{#if authStore.loading}
					<span class="spinner"></span>
					Connexion...
				{:else}
					Entrer
				{/if}
			</button>
		</form>
	</div>
</div>

<style>
	.login-container {
		min-height: 100dvh;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
		background: linear-gradient(135deg, var(--color-bg) 0%, var(--color-surface) 100%);
	}

	.login-card {
		width: 100%;
		max-width: 360px;
		padding: 2rem;
		background: var(--color-surface);
		border-radius: 1.5rem;
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
	}

	.login-header {
		text-align: center;
		margin-bottom: 2rem;
	}

	.logo {
		display: inline-flex;
		padding: 1rem;
		background: var(--color-primary);
		color: white;
		border-radius: 1rem;
		margin-bottom: 1rem;
	}

	h1 {
		margin: 0;
		font-size: 1.75rem;
		font-weight: 600;
		color: var(--color-text);
	}

	.subtitle {
		margin: 0.5rem 0 0;
		font-size: 0.875rem;
		color: var(--color-text-secondary);
	}

	.error-message {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		margin-bottom: 1rem;
		background: var(--color-error-bg, #fef2f2);
		color: var(--color-error, #dc2626);
		border-radius: 0.5rem;
		font-size: 0.875rem;
	}

	.error-dismiss {
		background: none;
		border: none;
		padding: 0.25rem;
		cursor: pointer;
		color: inherit;
		opacity: 0.7;
	}

	.error-dismiss:hover {
		opacity: 1;
	}

	.pin-input-wrapper {
		position: relative;
		margin-bottom: 1rem;
	}

	.pin-input {
		width: 100%;
		padding: 1rem;
		padding-right: 3rem;
		font-size: 1.5rem;
		letter-spacing: 0.5rem;
		text-align: center;
		border: 2px solid var(--color-border);
		border-radius: 0.75rem;
		background: var(--color-bg);
		color: var(--color-text);
		transition: border-color 0.2s;
	}

	.pin-input:focus {
		outline: none;
		border-color: var(--color-primary);
	}

	.pin-input::placeholder {
		letter-spacing: normal;
		font-size: 1rem;
	}

	.toggle-visibility {
		position: absolute;
		right: 0.75rem;
		top: 50%;
		transform: translateY(-50%);
		background: none;
		border: none;
		padding: 0.5rem;
		cursor: pointer;
		color: var(--color-text-secondary);
	}

	.toggle-visibility:hover {
		color: var(--color-text);
	}

	.pin-dots {
		display: flex;
		justify-content: center;
		gap: 0.75rem;
		margin-bottom: 1.5rem;
	}

	.dot {
		width: 12px;
		height: 12px;
		border-radius: 50%;
		border: 2px solid var(--color-border);
		transition: all 0.2s;
	}

	.dot.filled {
		background: var(--color-primary);
		border-color: var(--color-primary);
	}

	.keypad {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0.75rem;
		margin-bottom: 1.5rem;
	}

	.keypad-btn {
		padding: 1rem;
		font-size: 1.25rem;
		font-weight: 500;
		border: none;
		border-radius: 0.75rem;
		background: var(--color-bg);
		color: var(--color-text);
		cursor: pointer;
		transition: all 0.2s;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.keypad-btn:hover:not(:disabled) {
		background: var(--color-primary);
		color: white;
	}

	.keypad-btn:active:not(:disabled) {
		transform: scale(0.95);
	}

	.keypad-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.keypad-btn.action {
		background: var(--color-surface);
		color: var(--color-text-secondary);
	}

	.keypad-btn.action:hover:not(:disabled) {
		background: var(--color-bg);
		color: var(--color-text);
	}

	.submit-btn {
		width: 100%;
		padding: 1rem;
		font-size: 1rem;
		font-weight: 600;
		border: none;
		border-radius: 0.75rem;
		background: var(--color-primary);
		color: white;
		cursor: pointer;
		transition: all 0.2s;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
	}

	.submit-btn:hover:not(:disabled) {
		filter: brightness(1.1);
	}

	.submit-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.spinner {
		width: 16px;
		height: 16px;
		border: 2px solid transparent;
		border-top-color: currentColor;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Hide keypad on desktop when input is focused */
	@media (min-width: 640px) {
		.keypad {
			display: none;
		}
	}
</style>
