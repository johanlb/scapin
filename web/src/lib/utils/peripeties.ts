import type { ProposedNote, ProposedTask } from '../api';

export const AUTO_APPLY_THRESHOLD_REQUIRED = 0.8;
export const AUTO_APPLY_THRESHOLD_OPTIONAL = 0.85;
export const DAYS_THRESHOLD = 90;

/**
 * Check if a note will be applied based on its confidence, required status, and manual override.
 */
export function willNoteBeAutoApplied(note: ProposedNote): boolean {
    if (note.manually_approved === true) return true;
    if (note.manually_approved === false) return false;
    const threshold = note.required ? AUTO_APPLY_THRESHOLD_REQUIRED : AUTO_APPLY_THRESHOLD_OPTIONAL;
    return note.confidence >= threshold;
}

/**
 * Check if a task will be auto-applied based on its confidence.
 */
export function willTaskBeAutoApplied(task: ProposedTask): boolean {
    return task.confidence >= AUTO_APPLY_THRESHOLD_OPTIONAL;
}

/**
 * Filter proposed notes to only show ones that will be auto-applied.
 */
export function filterNotes(notes: ProposedNote[] | undefined, showAll: boolean): ProposedNote[] {
    if (!notes) return [];
    return notes.filter((note) => {
        const hasValidTitle =
            note.title && note.title.toLowerCase() !== 'general' && note.title.trim() !== '';
        return showAll || (hasValidTitle && willNoteBeAutoApplied(note));
    });
}

/**
 * Filter proposed notes to show only ones that will NOT be applied (skipped/rejected).
 */
export function filterSkippedNotes(notes: ProposedNote[] | undefined): ProposedNote[] {
    if (!notes) return [];
    return notes.filter((note) => {
        const hasValidTitle =
            note.title && note.title.toLowerCase() !== 'general' && note.title.trim() !== '';
        return hasValidTitle && !willNoteBeAutoApplied(note);
    });
}

/**
 * Filter proposed tasks to show only ones that will NOT be applied (skipped/rejected).
 */
export function filterSkippedTasks(tasks: ProposedTask[] | undefined): ProposedTask[] {
    if (!tasks) return [];
    return tasks.filter((task) => !willTaskBeAutoApplied(task));
}

/**
 * Filter proposed tasks to only show ones that will be auto-applied.
 */
export function filterTasks(tasks: ProposedTask[] | undefined, showAll: boolean): ProposedTask[] {
    if (!tasks) return [];
    const ninetyDaysAgo = new Date(Date.now() - DAYS_THRESHOLD * 24 * 60 * 60 * 1000);
    return tasks.filter((task) => {
        let hasValidDueDate = true;
        if (task.due_date) {
            const dueDate = new Date(task.due_date);
            hasValidDueDate = !isNaN(dueDate.getTime()) && dueDate >= ninetyDaysAgo;
        }
        return showAll || (willTaskBeAutoApplied(task) && hasValidDueDate);
    });
}

/**
 * Check if a date is in the past.
 */
export function isDatePast(dateStr: string | null | undefined): boolean {
    if (!dateStr) return false;
    const date = new Date(dateStr);
    return !isNaN(date.getTime()) && date < new Date();
}

/**
 * Check if a date is obsolete (> 90 days in the past).
 */
export function isDateObsolete(dateStr: string | null | undefined): boolean {
    if (!dateStr) return false;
    const date = new Date(dateStr);
    const ninetyDaysAgo = new Date(Date.now() - DAYS_THRESHOLD * 24 * 60 * 60 * 1000);
    return !isNaN(date.getTime()) && date < ninetyDaysAgo;
}
