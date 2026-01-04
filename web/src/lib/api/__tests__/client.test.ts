/**
 * API Client Tests
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getHealth, getStats, getMorningBriefing, ApiError } from '../client';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('API Client', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	describe('getHealth', () => {
		it('should return health status on success', async () => {
			const mockHealth = {
				status: 'healthy',
				version: '0.7.0',
				checks: [{ name: 'config', status: 'ok', message: 'OK' }],
				uptime_seconds: 100
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: mockHealth,
						error: null,
						timestamp: '2026-01-04T00:00:00Z'
					})
			});

			const result = await getHealth();

			expect(result).toEqual(mockHealth);
			expect(mockFetch).toHaveBeenCalledWith('/api/health', expect.any(Object));
		});

		it('should throw ApiError on HTTP error', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 500,
				json: () => Promise.resolve({ detail: 'Internal Server Error' })
			});

			try {
				await getHealth();
				expect.fail('Should have thrown');
			} catch (error) {
				expect(error).toBeInstanceOf(ApiError);
				expect((error as ApiError).status).toBe(500);
				expect((error as ApiError).message).toBe('Internal Server Error');
			}
		});

		it('should throw ApiError when success is false', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: false,
						data: null,
						error: 'Configuration error',
						timestamp: '2026-01-04T00:00:00Z'
					})
			});

			try {
				await getHealth();
				expect.fail('Should have thrown');
			} catch (error) {
				expect(error).toBeInstanceOf(ApiError);
				expect((error as ApiError).status).toBe(500);
				expect((error as ApiError).message).toBe('Configuration error');
			}
		});

		it('should throw ApiError when data is null', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: null,
						error: null,
						timestamp: '2026-01-04T00:00:00Z'
					})
			});

			try {
				await getHealth();
				expect.fail('Should have thrown');
			} catch (error) {
				expect(error).toBeInstanceOf(ApiError);
				expect((error as ApiError).message).toBe('API returned null data');
			}
		});

		it('should throw ApiError on network error', async () => {
			mockFetch.mockRejectedValueOnce(new Error('Network failure'));

			try {
				await getHealth();
				expect.fail('Should have thrown');
			} catch (error) {
				expect(error).toBeInstanceOf(ApiError);
				expect((error as ApiError).status).toBe(0);
				expect((error as ApiError).message).toBe('Network failure');
			}
		});
	});

	describe('getStats', () => {
		it('should return stats on success', async () => {
			const mockStats = {
				emails_processed: 10,
				teams_messages: 5,
				calendar_events: 3,
				queue_size: 2,
				uptime_seconds: 1000,
				last_activity: '2026-01-04T00:00:00Z'
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: mockStats,
						error: null,
						timestamp: '2026-01-04T00:00:00Z'
					})
			});

			const result = await getStats();

			expect(result).toEqual(mockStats);
			expect(mockFetch).toHaveBeenCalledWith('/api/stats', expect.any(Object));
		});
	});

	describe('getMorningBriefing', () => {
		it('should return briefing on success', async () => {
			const mockBriefing = {
				date: '2026-01-04',
				generated_at: '2026-01-04T08:00:00Z',
				urgent_count: 2,
				meetings_today: 3,
				total_items: 10,
				urgent_items: [],
				calendar_today: [],
				emails_pending: [],
				teams_unread: [],
				ai_summary: 'A busy day ahead',
				key_decisions: []
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: mockBriefing,
						error: null,
						timestamp: '2026-01-04T00:00:00Z'
					})
			});

			const result = await getMorningBriefing();

			expect(result).toEqual(mockBriefing);
			expect(mockFetch).toHaveBeenCalledWith('/api/briefing/morning', expect.any(Object));
		});
	});

	describe('ApiError', () => {
		it('should have correct properties', () => {
			const error = new ApiError(404, 'Not found');

			expect(error.status).toBe(404);
			expect(error.message).toBe('Not found');
			expect(error.name).toBe('ApiError');
			expect(error instanceof Error).toBe(true);
		});
	});
});
