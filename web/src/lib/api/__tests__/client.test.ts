/**
 * API Client Tests
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
	getHealth,
	getStats,
	getMorningBriefing,
	getNoteVersions,
	getNoteVersionContent,
	diffNoteVersions,
	restoreNoteVersion,
	globalSearch,
	getRecentSearches,
	getStatsOverview,
	getStatsBySource,
	ApiError
} from '../client';

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

	describe('Notes Versioning API', () => {
		describe('getNoteVersions', () => {
			it('should return versions list on success', async () => {
				const mockVersions = {
					note_id: 'note-123',
					versions: [
						{
							version_id: 'abc1234',
							full_hash: 'abc1234567890',
							message: 'Update note',
							timestamp: '2026-01-05T10:00:00Z',
							author: 'Johan'
						}
					],
					total: 1
				};

				mockFetch.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							success: true,
							data: mockVersions,
							error: null,
							timestamp: '2026-01-05T10:00:00Z'
						})
				});

				const result = await getNoteVersions('note-123');

				expect(result).toEqual(mockVersions);
				expect(mockFetch).toHaveBeenCalledWith(
					'/api/notes/note-123/versions?limit=50',
					expect.any(Object)
				);
			});

			it('should use custom limit parameter', async () => {
				mockFetch.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							success: true,
							data: { note_id: 'note-123', versions: [], total: 0 },
							error: null,
							timestamp: '2026-01-05T10:00:00Z'
						})
				});

				await getNoteVersions('note-123', 10);

				expect(mockFetch).toHaveBeenCalledWith(
					'/api/notes/note-123/versions?limit=10',
					expect.any(Object)
				);
			});
		});

		describe('getNoteVersionContent', () => {
			it('should return version content on success', async () => {
				const mockContent = {
					note_id: 'note-123',
					version_id: 'abc1234',
					content: '# My Note\n\nContent here',
					timestamp: '2026-01-05T10:00:00Z'
				};

				mockFetch.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							success: true,
							data: mockContent,
							error: null,
							timestamp: '2026-01-05T10:00:00Z'
						})
				});

				const result = await getNoteVersionContent('note-123', 'abc1234');

				expect(result).toEqual(mockContent);
				expect(mockFetch).toHaveBeenCalledWith(
					'/api/notes/note-123/versions/abc1234',
					expect.any(Object)
				);
			});
		});

		describe('diffNoteVersions', () => {
			it('should return diff between two versions', async () => {
				const mockDiff = {
					note_id: 'note-123',
					from_version: 'abc1234',
					to_version: 'def5678',
					additions: 5,
					deletions: 2,
					diff_text: '--- a/note\n+++ b/note\n@@ -1,3 +1,4 @@\n # Title\n-old line\n+new line\n+added line'
				};

				mockFetch.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							success: true,
							data: mockDiff,
							error: null,
							timestamp: '2026-01-05T10:00:00Z'
						})
				});

				const result = await diffNoteVersions('note-123', 'abc1234', 'def5678');

				expect(result).toEqual(mockDiff);
				expect(mockFetch).toHaveBeenCalledWith(
					'/api/notes/note-123/diff?v1=abc1234&v2=def5678',
					expect.any(Object)
				);
			});
		});

		describe('restoreNoteVersion', () => {
			it('should restore a version and return updated note', async () => {
				const mockNote = {
					note_id: 'note-123',
					title: 'My Note',
					content: '# Restored content',
					excerpt: 'Restored content',
					path: '/notes',
					tags: [],
					entities: [],
					created_at: '2026-01-01T00:00:00Z',
					updated_at: '2026-01-05T10:00:00Z',
					pinned: false,
					metadata: {}
				};

				mockFetch.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							success: true,
							data: mockNote,
							error: null,
							timestamp: '2026-01-05T10:00:00Z'
						})
				});

				const result = await restoreNoteVersion('note-123', 'abc1234');

				expect(result).toEqual(mockNote);
				expect(mockFetch).toHaveBeenCalledWith(
					'/api/notes/note-123/restore/abc1234',
					expect.objectContaining({ method: 'POST' })
				);
			});
		});
	});

	describe('Global Search API', () => {
		describe('globalSearch', () => {
			it('should return search results on success', async () => {
				const mockSearchResponse = {
					query: 'test query',
					results: {
						notes: [
							{
								id: 'note-1',
								type: 'note',
								title: 'Test Note',
								excerpt: 'This is a test note',
								score: 0.95,
								timestamp: '2026-01-05T10:00:00Z',
								metadata: {},
								path: '/notes/test',
								tags: ['test']
							}
						],
						emails: [
							{
								id: 'email-1',
								type: 'email',
								title: 'Test Email',
								excerpt: 'Email content',
								score: 0.85,
								timestamp: '2026-01-05T09:00:00Z',
								metadata: {},
								from_address: 'test@example.com',
								from_name: 'Test User',
								status: 'pending'
							}
						],
						calendar: [],
						teams: []
					},
					total: 2,
					counts: { notes: 1, emails: 1, calendar: 0, teams: 0 },
					search_time_ms: 42
				};

				mockFetch.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							success: true,
							data: mockSearchResponse,
							error: null,
							timestamp: '2026-01-05T10:00:00Z'
						})
				});

				const result = await globalSearch('test query');

				expect(result).toEqual(mockSearchResponse);
				expect(result.total).toBe(2);
				expect(result.results.notes).toHaveLength(1);
				expect(result.results.emails).toHaveLength(1);
				expect(mockFetch).toHaveBeenCalledWith('/api/search?q=test+query', expect.any(Object));
			});

			it('should pass optional parameters', async () => {
				mockFetch.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							success: true,
							data: {
								query: 'test',
								results: { notes: [], emails: [], calendar: [], teams: [] },
								total: 0,
								counts: { notes: 0, emails: 0, calendar: 0, teams: 0 },
								search_time_ms: 10
							},
							error: null,
							timestamp: '2026-01-05T10:00:00Z'
						})
				});

				await globalSearch('test', {
					types: ['note', 'email'],
					limit: 5,
					dateFrom: '2026-01-01',
					dateTo: '2026-01-05'
				});

				expect(mockFetch).toHaveBeenCalledWith(
					'/api/search?q=test&types=note%2Cemail&limit=5&date_from=2026-01-01&date_to=2026-01-05',
					expect.any(Object)
				);
			});

			it('should throw ApiError on search failure', async () => {
				mockFetch.mockResolvedValueOnce({
					ok: false,
					status: 400,
					json: () => Promise.resolve({ detail: 'Invalid query' })
				});

				try {
					await globalSearch('');
					expect.fail('Should have thrown');
				} catch (error) {
					expect(error).toBeInstanceOf(ApiError);
					expect((error as ApiError).status).toBe(400);
				}
			});
		});

		describe('getRecentSearches', () => {
			it('should return recent searches on success', async () => {
				const mockRecentSearches = {
					searches: [
						{ query: 'previous search', timestamp: '2026-01-05T09:00:00Z', result_count: 5 },
						{ query: 'older search', timestamp: '2026-01-04T15:00:00Z', result_count: 3 }
					],
					total: 2
				};

				mockFetch.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							success: true,
							data: mockRecentSearches,
							error: null,
							timestamp: '2026-01-05T10:00:00Z'
						})
				});

				const result = await getRecentSearches();

				expect(result).toEqual(mockRecentSearches);
				expect(result.searches).toHaveLength(2);
				expect(mockFetch).toHaveBeenCalledWith('/api/search/recent?limit=20', expect.any(Object));
			});

			it('should use custom limit parameter', async () => {
				mockFetch.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							success: true,
							data: { searches: [], total: 0 },
							error: null,
							timestamp: '2026-01-05T10:00:00Z'
						})
				});

				await getRecentSearches(10);

				expect(mockFetch).toHaveBeenCalledWith(
					'/api/search/recent?limit=10',
					expect.any(Object)
				);
			});
		});
	});

	describe('Stats API', () => {
		describe('getStatsOverview', () => {
			it('should return stats overview on success', async () => {
				const mockOverview = {
					total_processed: 100,
					total_pending: 10,
					sources_active: 3,
					uptime_seconds: 3600.0,
					last_activity: '2026-01-05T10:00:00Z',
					email_processed: 50,
					email_queued: 5,
					teams_messages: 30,
					teams_unread: 3,
					calendar_events_today: 3,
					calendar_events_week: 10,
					notes_due: 15,
					notes_reviewed_today: 5
				};

				mockFetch.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							success: true,
							data: mockOverview,
							error: null,
							timestamp: '2026-01-05T10:00:00Z'
						})
				});

				const result = await getStatsOverview();

				expect(result).toEqual(mockOverview);
				expect(result.total_processed).toBe(100);
				expect(result.sources_active).toBe(3);
				expect(mockFetch).toHaveBeenCalledWith('/api/stats/overview', expect.any(Object));
			});

			it('should throw ApiError on failure', async () => {
				mockFetch.mockResolvedValueOnce({
					ok: false,
					status: 500,
					json: () => Promise.resolve({ detail: 'Service unavailable' })
				});

				try {
					await getStatsOverview();
					expect.fail('Should have thrown');
				} catch (error) {
					expect(error).toBeInstanceOf(ApiError);
					expect((error as ApiError).status).toBe(500);
				}
			});
		});

		describe('getStatsBySource', () => {
			it('should return stats by source on success', async () => {
				const mockBySource = {
					email: {
						emails_processed: 100,
						emails_auto_executed: 80,
						emails_archived: 60,
						emails_deleted: 10,
						emails_queued: 5,
						emails_skipped: 5,
						tasks_created: 10,
						average_confidence: 0.85,
						processing_mode: 'cognitive'
					},
					teams: {
						total_chats: 20,
						unread_chats: 3,
						messages_processed: 50,
						messages_flagged: 5,
						last_poll: '2026-01-05T09:00:00Z'
					},
					calendar: null,
					queue: {
						total: 5,
						by_status: { pending: 3, approved: 2 },
						by_account: { work: 3, personal: 2 },
						oldest_item: null,
						newest_item: null
					},
					notes: {
						total_notes: 200,
						by_type: { projet: 50, personne: 30 },
						by_importance: { high: 20, medium: 100 },
						total_due: 15,
						reviewed_today: 5,
						avg_easiness_factor: 2.5
					}
				};

				mockFetch.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							success: true,
							data: mockBySource,
							error: null,
							timestamp: '2026-01-05T10:00:00Z'
						})
				});

				const result = await getStatsBySource();

				expect(result).toEqual(mockBySource);
				expect(result.email?.emails_processed).toBe(100);
				expect(result.teams?.total_chats).toBe(20);
				expect(result.calendar).toBeNull();
				expect(result.notes?.total_notes).toBe(200);
				expect(mockFetch).toHaveBeenCalledWith('/api/stats/by-source', expect.any(Object));
			});

			it('should handle all null sources', async () => {
				const mockBySource = {
					email: null,
					teams: null,
					calendar: null,
					queue: null,
					notes: null
				};

				mockFetch.mockResolvedValueOnce({
					ok: true,
					json: () =>
						Promise.resolve({
							success: true,
							data: mockBySource,
							error: null,
							timestamp: '2026-01-05T10:00:00Z'
						})
				});

				const result = await getStatsBySource();

				expect(result.email).toBeNull();
				expect(result.teams).toBeNull();
				expect(result.calendar).toBeNull();
				expect(result.queue).toBeNull();
				expect(result.notes).toBeNull();
			});
		});
	});
});
