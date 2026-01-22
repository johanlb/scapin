/**
 * Memory Cycles API Tests
 * Tests for Filage and Lecture API functions
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
	getFilage,
	startLecture,
	completeLecture,
	getLectureStats,
	getPendingQuestions,
	answerPendingQuestion,
	addToFilage,
	triggerRetouche,
	ApiError
} from '../client';

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('Memory Cycles API', () => {
	beforeEach(() => {
		mockFetch.mockReset();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	describe('getFilage', () => {
		it('should return filage with lectures on success', async () => {
			const mockFilage = {
				date: '2026-01-22',
				generated_at: '2026-01-22T08:00:00Z',
				lectures: [
					{
						note_id: 'note-1',
						note_title: 'Marie Dupont',
						note_type: 'personne',
						priority: 1,
						reason: 'Questions en attente',
						quality_score: 85,
						questions_pending: true,
						questions_count: 2
					},
					{
						note_id: 'note-2',
						note_title: 'Projet Alpha',
						note_type: 'projet',
						priority: 2,
						reason: 'SM-2 due',
						quality_score: null,
						questions_pending: false,
						questions_count: 0
					}
				],
				total_lectures: 2,
				events_today: 3,
				notes_with_questions: 1
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: mockFilage,
						error: null,
						timestamp: '2026-01-22T08:00:00Z'
					})
			});

			const result = await getFilage();

			expect(result).toEqual(mockFilage);
			expect(result.lectures).toHaveLength(2);
			expect(result.total_lectures).toBe(2);
			expect(mockFetch).toHaveBeenCalledWith(
				'/api/briefing/filage?max_lectures=20',
				expect.any(Object)
			);
		});

		it('should use custom maxLectures parameter', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: {
							date: '2026-01-22',
							generated_at: '2026-01-22T08:00:00Z',
							lectures: [],
							total_lectures: 0,
							events_today: 0,
							notes_with_questions: 0
						},
						error: null,
						timestamp: '2026-01-22T08:00:00Z'
					})
			});

			await getFilage(10);

			expect(mockFetch).toHaveBeenCalledWith(
				'/api/briefing/filage?max_lectures=10',
				expect.any(Object)
			);
		});

		it('should throw ApiError on failure', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 500,
				json: () => Promise.resolve({ detail: 'Service unavailable' })
			});

			try {
				await getFilage();
				expect.fail('Should have thrown');
			} catch (error) {
				expect(error).toBeInstanceOf(ApiError);
				expect((error as ApiError).status).toBe(500);
			}
		});
	});

	describe('startLecture', () => {
		it('should start a lecture session on success', async () => {
			const mockSession = {
				session_id: 'session-123',
				note_id: 'note-1',
				note_title: 'Marie Dupont',
				note_content: '# Marie Dupont\n\nContent here...',
				started_at: '2026-01-22T09:00:00Z',
				quality_score: 85,
				questions: ['Question 1?', 'Question 2?']
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: mockSession,
						error: null,
						timestamp: '2026-01-22T09:00:00Z'
					})
			});

			const result = await startLecture('note-1');

			expect(result).toEqual(mockSession);
			expect(result.session_id).toBe('session-123');
			expect(result.questions).toHaveLength(2);
			expect(mockFetch).toHaveBeenCalledWith(
				'/api/briefing/lecture/note-1/start',
				expect.objectContaining({ method: 'POST' })
			);
		});

		it('should encode noteId in URL', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: {
							session_id: 'session-123',
							note_id: 'note/special&chars',
							note_title: 'Test',
							note_content: 'Content',
							started_at: '2026-01-22T09:00:00Z',
							quality_score: null,
							questions: []
						},
						error: null,
						timestamp: '2026-01-22T09:00:00Z'
					})
			});

			await startLecture('note/special&chars');

			expect(mockFetch).toHaveBeenCalledWith(
				'/api/briefing/lecture/note%2Fspecial%26chars/start',
				expect.any(Object)
			);
		});

		it('should throw ApiError on 404', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: false,
				status: 404,
				json: () => Promise.resolve({ detail: 'Note not found' })
			});

			try {
				await startLecture('nonexistent');
				expect.fail('Should have thrown');
			} catch (error) {
				expect(error).toBeInstanceOf(ApiError);
				expect((error as ApiError).status).toBe(404);
				expect((error as ApiError).message).toBe('Note not found');
			}
		});
	});

	describe('completeLecture', () => {
		it('should complete a lecture session on success', async () => {
			const mockResult = {
				note_id: 'note-1',
				quality_rating: 4,
				next_lecture: '2026-01-25T09:00:00Z',
				interval_hours: 72,
				answers_recorded: 2,
				questions_remaining: 0,
				success: true
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: mockResult,
						error: null,
						timestamp: '2026-01-22T09:30:00Z'
					})
			});

			const result = await completeLecture('note-1', 4, { q1: 'Answer 1', q2: 'Answer 2' });

			expect(result).toEqual(mockResult);
			expect(result.success).toBe(true);
			expect(result.answers_recorded).toBe(2);
			expect(mockFetch).toHaveBeenCalledWith(
				'/api/briefing/lecture/note-1/complete',
				expect.objectContaining({
					method: 'POST',
					body: JSON.stringify({ quality: 4, answers: { q1: 'Answer 1', q2: 'Answer 2' } })
				})
			);
		});

		it('should complete without answers', async () => {
			const mockResult = {
				note_id: 'note-1',
				quality_rating: 3,
				next_lecture: '2026-01-24T09:00:00Z',
				interval_hours: 48,
				answers_recorded: 0,
				questions_remaining: 0,
				success: true
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: mockResult,
						error: null,
						timestamp: '2026-01-22T09:30:00Z'
					})
			});

			const result = await completeLecture('note-1', 3);

			expect(result.success).toBe(true);
			expect(result.answers_recorded).toBe(0);
		});
	});

	describe('getLectureStats', () => {
		it('should return lecture stats for a note', async () => {
			const mockStats = {
				note_id: 'note-1',
				total_lectures: 10,
				average_quality: 3.8,
				last_lecture: '2026-01-20T09:00:00Z',
				next_lecture: '2026-01-25T09:00:00Z',
				easiness_factor: 2.6,
				interval_hours: 120
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: mockStats,
						error: null,
						timestamp: '2026-01-22T09:00:00Z'
					})
			});

			const result = await getLectureStats('note-1');

			expect(result).toEqual(mockStats);
			expect(result.total_lectures).toBe(10);
			expect(result.average_quality).toBe(3.8);
			expect(mockFetch).toHaveBeenCalledWith(
				'/api/notes/note-1/lecture-stats',
				expect.any(Object)
			);
		});
	});

	describe('getPendingQuestions', () => {
		it('should return pending questions list', async () => {
			const mockQuestions = {
				questions: [
					{
						question_id: 'q-1',
						note_id: 'note-1',
						note_title: 'Marie Dupont',
						question_text: 'What is her role?',
						created_at: '2026-01-20T10:00:00Z',
						answered: false
					},
					{
						question_id: 'q-2',
						note_id: 'note-1',
						note_title: 'Marie Dupont',
						question_text: 'What project is she on?',
						created_at: '2026-01-20T10:00:00Z',
						answered: false
					}
				],
				total: 2,
				by_note: { 'note-1': 2 }
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: mockQuestions,
						error: null,
						timestamp: '2026-01-22T09:00:00Z'
					})
			});

			const result = await getPendingQuestions();

			expect(result).toEqual(mockQuestions);
			expect(result.questions).toHaveLength(2);
			expect(result.total).toBe(2);
			expect(mockFetch).toHaveBeenCalledWith(
				'/api/notes/questions/pending?limit=50',
				expect.any(Object)
			);
		});

		it('should use custom limit parameter', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: { questions: [], total: 0, by_note: {} },
						error: null,
						timestamp: '2026-01-22T09:00:00Z'
					})
			});

			await getPendingQuestions(10);

			expect(mockFetch).toHaveBeenCalledWith(
				'/api/notes/questions/pending?limit=10',
				expect.any(Object)
			);
		});
	});

	describe('answerPendingQuestion', () => {
		it('should answer a question successfully', async () => {
			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: { success: true },
						error: null,
						timestamp: '2026-01-22T09:30:00Z'
					})
			});

			const result = await answerPendingQuestion('q-1', 'She is the Product Manager');

			expect(result.success).toBe(true);
			expect(mockFetch).toHaveBeenCalledWith(
				'/api/notes/questions/q-1/answer',
				expect.objectContaining({
					method: 'POST',
					body: JSON.stringify({ answer: 'She is the Product Manager' })
				})
			);
		});
	});

	describe('addToFilage', () => {
		it('should add a note to filage successfully', async () => {
			const mockResponse = {
				note_id: 'note-5',
				success: true,
				message: 'Note added to today\'s Filage'
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: mockResponse,
						error: null,
						timestamp: '2026-01-22T09:00:00Z'
					})
			});

			const result = await addToFilage('note-5');

			expect(result.success).toBe(true);
			expect(result.note_id).toBe('note-5');
			expect(mockFetch).toHaveBeenCalledWith(
				'/api/briefing/filage/add/note-5',
				expect.objectContaining({ method: 'POST' })
			);
		});
	});

	describe('triggerRetouche', () => {
		it('should trigger AI retouche for a note', async () => {
			const mockResponse = {
				note_id: 'note-1',
				success: true,
				quality_before: 65,
				quality_after: 85,
				improvements_count: 3,
				message: 'Note improved successfully'
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: mockResponse,
						error: null,
						timestamp: '2026-01-22T09:30:00Z'
					})
			});

			const result = await triggerRetouche('note-1');

			expect(result.success).toBe(true);
			expect(result.quality_before).toBe(65);
			expect(result.quality_after).toBe(85);
			expect(result.improvements_count).toBe(3);
			expect(mockFetch).toHaveBeenCalledWith(
				'/api/briefing/retouche/note-1',
				expect.objectContaining({ method: 'POST' })
			);
		});

		it('should handle no improvements needed', async () => {
			const mockResponse = {
				note_id: 'note-1',
				success: true,
				quality_before: 95,
				quality_after: 95,
				improvements_count: 0,
				message: 'Note already high quality'
			};

			mockFetch.mockResolvedValueOnce({
				ok: true,
				json: () =>
					Promise.resolve({
						success: true,
						data: mockResponse,
						error: null,
						timestamp: '2026-01-22T09:30:00Z'
					})
			});

			const result = await triggerRetouche('note-1');

			expect(result.success).toBe(true);
			expect(result.improvements_count).toBe(0);
			expect(result.quality_before).toBe(result.quality_after);
		});
	});
});
