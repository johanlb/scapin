import type { ScapinEvent } from '$lib/types';

export const mockEvents: ScapinEvent[] = [
    {
        id: '1',
        source: 'email',
        title: 'RE: Proposition commerciale Q1',
        summary: 'Client ABC demande une révision du budget avant vendredi',
        sender: 'Marie Dupont',
        occurred_at: new Date().toISOString(),
        status: 'pending',
        urgency: 'urgent',
        confidence: 'high',
        suggested_actions: [
            { id: '1', type: 'reply', label: 'Répondre', confidence: 0.95 },
            { id: '2', type: 'task', label: 'Créer tâche', confidence: 0.8 }
        ]
    },
    {
        id: '2',
        source: 'calendar',
        title: 'Réunion équipe produit',
        summary: "Point hebdomadaire avec l'équipe - salle Voltaire",
        occurred_at: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
        status: 'pending',
        urgency: 'high',
        confidence: 'high',
        suggested_actions: [{ id: '1', type: 'prepare', label: 'Préparer', confidence: 0.9 }]
    },
    {
        id: '3',
        source: 'teams',
        title: 'Message de Pierre Martin',
        summary: 'Question sur le déploiement de la v2.1',
        sender: 'Pierre Martin',
        occurred_at: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
        status: 'pending',
        urgency: 'medium',
        confidence: 'medium',
        suggested_actions: [{ id: '1', type: 'reply', label: 'Répondre', confidence: 0.85 }]
    }
];

export const mockStats = {
    emails_pending: 12,
    teams_unread: 5,
    meetings_today: 3,
    tasks_due: 7
};
