/**
 * Retouche Actions Hook
 * Provides functions to approve/reject retouche actions with undo support.
 */

import {
	approveRetoucheAction,
	rejectRetoucheAction,
	rollbackRetoucheAction
} from '$lib/api';
import { toastStore } from '$lib/stores/toast.svelte';
import type { PendingRetoucheAction } from '$lib/api';

interface ActionCallbacks {
	onSuccess?: () => void;
	onError?: (error: Error) => void;
}

/**
 * Get action label for toast messages
 */
function getActionLabel(actionType: string): string {
	switch (actionType) {
		case 'flag_obsolete':
			return 'marquée obsolète';
		case 'merge_into':
			return 'fusionnée';
		case 'move_to_folder':
			return 'déplacée';
		default:
			return 'modifiée';
	}
}

/**
 * Approve a retouche action with undo support
 */
export async function approveWithUndo(
	action: PendingRetoucheAction,
	callbacks: ActionCallbacks = {}
): Promise<boolean> {
	try {
		const result = await approveRetoucheAction(action.action_id, action.note_id, true);

		if (result.success) {
			// Show undo toast if rollback is available
			if (result.rollback_available && result.rollback_token) {
				const token = result.rollback_token;
				const noteId = action.note_id;
				const actionLabel = getActionLabel(action.action_type);

				toastStore.undo(
					`Note ${actionLabel} : ${action.note_title}`,
					async () => {
						await rollbackRetoucheAction(token, noteId);
					},
					{
						title: 'Action effectuée',
						itemId: action.action_id,
						countdownSeconds: 15
					}
				);
			} else {
				toastStore.success(result.message);
			}

			callbacks.onSuccess?.();
			return true;
		} else {
			toastStore.error(result.message);
			return false;
		}
	} catch (error) {
		toastStore.error("Erreur lors de l'approbation");
		callbacks.onError?.(error as Error);
		return false;
	}
}

/**
 * Reject a retouche action
 */
export async function rejectAction(
	action: PendingRetoucheAction,
	reason?: string,
	callbacks: ActionCallbacks = {}
): Promise<boolean> {
	try {
		const result = await rejectRetoucheAction(action.action_id, action.note_id, reason);

		if (result.success) {
			toastStore.info('Action rejetée');
			callbacks.onSuccess?.();
			return true;
		} else {
			toastStore.error(result.message);
			return false;
		}
	} catch (error) {
		toastStore.error('Erreur lors du rejet');
		callbacks.onError?.(error as Error);
		return false;
	}
}
