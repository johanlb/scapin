/**
 * Haptic feedback utilities
 *
 * IMPORTANT: The Web Vibration API is NOT supported on iOS Safari.
 * This module provides a graceful no-op on unsupported platforms.
 *
 * For true haptic feedback on iOS, consider:
 * - Capacitor with @capacitor/haptics plugin
 * - Native app wrapper
 *
 * Currently, this serves as:
 * 1. A working implementation for Android devices
 * 2. A placeholder API for future iOS native integration
 * 3. Audio feedback fallback option (commented out)
 */

export type HapticStyle = 'light' | 'medium' | 'heavy' | 'success' | 'warning' | 'error';

const hapticPatterns: Record<HapticStyle, number[]> = {
	light: [10],
	medium: [20],
	heavy: [30],
	success: [10, 50, 10],
	warning: [20, 30, 20],
	error: [30, 50, 30, 50, 30]
};

/**
 * Check if haptic feedback is supported (Vibration API)
 * Note: Returns false on iOS Safari
 */
export function isHapticSupported(): boolean {
	if (typeof navigator === 'undefined') return false;
	if (!('vibrate' in navigator)) return false;

	// Test if vibrate actually works (some browsers have it but it's a no-op)
	try {
		return navigator.vibrate(0) !== false;
	} catch {
		return false;
	}
}

/**
 * Trigger haptic feedback if available
 *
 * On unsupported platforms (iOS Safari), this is a silent no-op.
 * For iOS haptics, integrate Capacitor's Haptics plugin.
 */
export function haptic(style: HapticStyle = 'light'): void {
	if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
		try {
			navigator.vibrate(hapticPatterns[style]);
		} catch {
			// Silently fail - haptics are nice-to-have, not critical
		}
	}
}

/**
 * Capacitor Haptics integration placeholder
 * Uncomment and implement when adding Capacitor to the project
 */
/*
import { Haptics, ImpactStyle } from '@capacitor/haptics';

const capacitorStyles: Record<HapticStyle, ImpactStyle> = {
	light: ImpactStyle.Light,
	medium: ImpactStyle.Medium,
	heavy: ImpactStyle.Heavy,
	success: ImpactStyle.Light,
	warning: ImpactStyle.Medium,
	error: ImpactStyle.Heavy
};

export async function hapticNative(style: HapticStyle = 'light'): Promise<void> {
	try {
		await Haptics.impact({ style: capacitorStyles[style] });
	} catch {
		// Fallback to web vibration
		haptic(style);
	}
}
*/
