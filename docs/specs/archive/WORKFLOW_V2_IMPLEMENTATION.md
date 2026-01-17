# Workflow v2.1 : Plan d'Implémentation

**Version** : 2.1.0
**Date** : 11 janvier 2026
**Référence** : [WORKFLOW_V2_SIMPLIFIED.md](WORKFLOW_V2_SIMPLIFIED.md)

---

## Résumé Exécutif

| Métrique | Valeur |
|----------|--------|
| **Nouveaux fichiers** | 6 |
| **Fichiers modifiés** | 4 |
| **Lignes de code** | ~880 |
| **Effort total** | ~4 semaines |
| **Coût API** | ~$36/mois |
| **Dépendances** | 0 nouvelles |

---

## 1. Fichiers à Créer

### 1.1 `src/core/models/v2_models.py` (~100 lignes)

```python
"""Modèles de données pour Workflow v2.1"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Extraction:
    """Une information extraite d'un événement"""
    info: str
    type: str  # decision, engagement, fait, deadline, relation
    importance: str  # haute, moyenne
    note_cible: str
    note_action: str  # enrichir, creer
    omnifocus: bool = False

@dataclass
class AnalysisResult:
    """Résultat de l'analyse d'un événement"""
    extractions: list[Extraction]
    action: str  # archive, flag, queue, rien
    confidence: float
    raisonnement: str
    model_used: str  # haiku, sonnet
    tokens_used: int
    duration_ms: float

@dataclass
class EnrichmentResult:
    """Résultat de l'application des extractions"""
    notes_updated: list[str]
    notes_created: list[str]
    tasks_created: list[str]
    errors: list[str]

@dataclass
class ContextNote:
    """Note de contexte pour le prompt"""
    title: str
    type: str
    content_summary: str
    relevance: float
```

**Effort** : 🟢 2h

---

### 1.2 `src/sancho/analyzer.py` (~150 lignes)

```python
"""Analyseur d'événements avec escalade Haiku → Sonnet"""

from src.core.events import PerceivedEvent
from src.core.models.v2_models import AnalysisResult, Extraction
from src.sancho.router import AIRouter
from src.sancho.templates import TemplateManager

class EventAnalyzer:
    """Analyse les événements avec l'API Claude"""

    def __init__(
        self,
        ai_router: AIRouter,
        template_manager: TemplateManager,
        config: WorkflowV2Config
    ):
        self.ai_router = ai_router
        self.templates = template_manager
        self.config = config

    async def analyze(
        self,
        event: PerceivedEvent,
        context_notes: list[ContextNote]
    ) -> AnalysisResult:
        """
        Analyse un événement avec escalade automatique.

        1. Essaie Haiku
        2. Si confidence < 0.7, escalade vers Sonnet
        """
        # Préparer le prompt
        prompt = self.templates.render(
            "v2/extraction",
            event=event,
            context=context_notes
        )

        # Essayer Haiku
        result = await self._call_model(
            prompt=prompt,
            model=self.config.default_model
        )

        # Escalader si nécessaire
        if result.confidence < self.config.escalation_threshold:
            result = await self._call_model(
                prompt=prompt,
                model=self.config.escalation_model
            )

        return result

    async def _call_model(
        self,
        prompt: str,
        model: str
    ) -> AnalysisResult:
        """Appelle l'API et parse la réponse"""
        response, usage = await self.ai_router.analyze_with_prompt(
            prompt=prompt,
            model=model,
            response_format="json"
        )

        return self._parse_response(response, model, usage)

    def _parse_response(
        self,
        response: str,
        model: str,
        usage: dict
    ) -> AnalysisResult:
        """Parse la réponse JSON de l'API"""
        import json
        data = json.loads(response)

        return AnalysisResult(
            extractions=[
                Extraction(**ext) for ext in data.get("extractions", [])
            ],
            action=data.get("action", "rien"),
            confidence=data.get("confidence", 0.5),
            raisonnement=data.get("raisonnement", ""),
            model_used=model,
            tokens_used=usage.get("total_tokens", 0),
            duration_ms=usage.get("duration_ms", 0)
        )
```

**Effort** : 🟡 4h

---

### 1.3 `src/sancho/templates/v2/extraction.j2` (~80 lignes)

```jinja2
Tu es Scapin, assistant cognitif de Johan.

## ÉVÉNEMENT
Type: {{ event.event_type.value }}
De: {{ event.metadata.get('from_address', 'N/A') }}
Sujet: {{ event.title }}
Date: {{ event.timestamp.strftime('%Y-%m-%d %H:%M') }}

{{ event.content[:2000] }}

{% if context %}
## CONTEXTE (notes existantes)
{% for note in context[:3] %}
### {{ note.title }} ({{ note.type }})
{{ note.content_summary[:300] }}
---
{% endfor %}
{% endif %}

## RÈGLES D'EXTRACTION

Extrais UNIQUEMENT les informations PERMANENTES :

✅ EXTRAIRE :
- Décisions actées ("budget validé", "choix techno X")
- Engagements ("Marc s'engage à livrer lundi")
- Faits importants ("nouveau client signé", "Marie promue")
- Dates clés (deadlines, jalons) → omnifocus: true
- Relations ("Marc rejoint projet Alpha")

❌ NE PAS EXTRAIRE :
- Lieux/heures de réunion ponctuels
- Formules de politesse
- Confirmations simples ("OK", "Bien reçu")
- Détails logistiques temporaires

## FORMAT RÉPONSE (JSON strict)

{
  "extractions": [
    {
      "info": "Description concise",
      "type": "decision|engagement|fait|deadline|relation",
      "importance": "haute|moyenne",
      "note_cible": "Titre note",
      "note_action": "enrichir|creer",
      "omnifocus": false
    }
  ],
  "action": "archive|flag|queue|rien",
  "confidence": 0.0-1.0,
  "raisonnement": "Explication courte"
}

Si rien d'important à extraire, retourne "extractions": []
```

**Effort** : 🟢 2h

---

### 1.4 `src/passepartout/enricher.py` (~200 lignes)

```python
"""Applique les extractions au PKM"""

from src.core.models.v2_models import AnalysisResult, EnrichmentResult, Extraction
from src.passepartout.note_manager import NoteManager
from src.integrations.apple.omnifocus import OmniFocusClient

class PKMEnricher:
    """Enrichit le PKM avec les extractions"""

    def __init__(
        self,
        note_manager: NoteManager,
        omnifocus: OmniFocusClient,
        config: WorkflowV2Config
    ):
        self.notes = note_manager
        self.omnifocus = omnifocus
        self.config = config

    async def apply(
        self,
        result: AnalysisResult,
        event_id: str
    ) -> EnrichmentResult:
        """Applique les extractions au PKM"""

        notes_updated = []
        notes_created = []
        tasks_created = []
        errors = []

        for extraction in result.extractions:
            try:
                # Enrichir ou créer note
                note_result = await self._apply_to_note(extraction, event_id)
                if note_result.created:
                    notes_created.append(note_result.note_id)
                else:
                    notes_updated.append(note_result.note_id)

                # Créer tâche OmniFocus si demandé
                if extraction.omnifocus and self.config.omnifocus_enabled:
                    task_id = await self._create_task(extraction)
                    if task_id:
                        tasks_created.append(task_id)

            except Exception as e:
                errors.append(f"{extraction.note_cible}: {str(e)}")

        return EnrichmentResult(
            notes_updated=notes_updated,
            notes_created=notes_created,
            tasks_created=tasks_created,
            errors=errors
        )

    async def _apply_to_note(
        self,
        extraction: Extraction,
        event_id: str
    ) -> NoteResult:
        """Applique une extraction à une note"""

        # Chercher la note
        note = self.notes.get_by_title(extraction.note_cible)
        created = False

        # Créer si n'existe pas et demandé
        if note is None and extraction.note_action == "creer":
            note = await self.notes.create(
                title=extraction.note_cible,
                note_type=self._infer_type(extraction)
            )
            created = True

        if note is None:
            raise ValueError(f"Note '{extraction.note_cible}' non trouvée")

        # Ajouter l'information
        await self.notes.add_info(
            note_id=note.note_id,
            info=extraction.info,
            info_type=extraction.type,
            importance=extraction.importance,
            source_id=event_id
        )

        return NoteResult(note_id=note.note_id, created=created)

    async def _create_task(self, extraction: Extraction) -> Optional[str]:
        """Crée une tâche OmniFocus"""
        try:
            return await self.omnifocus.create_task(
                title=extraction.info,
                project=self.config.omnifocus_default_project,
                note=f"Lié à: {extraction.note_cible}"
            )
        except Exception as e:
            # Log mais ne pas bloquer
            logger.warning(f"OmniFocus error: {e}")
            return None

    def _infer_type(self, extraction: Extraction) -> str:
        """Infère le type de note à créer"""
        if extraction.type == "relation":
            return "personne"
        elif extraction.type in ("decision", "deadline"):
            return "projet"
        else:
            return "concept"
```

**Effort** : 🟡 6h

---

### 1.5 `src/integrations/apple/omnifocus.py` (~150 lignes)

```python
"""Client OmniFocus via AppleScript"""

import subprocess
from typing import Optional

class OmniFocusClient:
    """Interaction avec OmniFocus via AppleScript"""

    async def create_task(
        self,
        title: str,
        project: Optional[str] = None,
        due_date: Optional[str] = None,
        note: Optional[str] = None
    ) -> Optional[str]:
        """
        Crée une tâche dans OmniFocus.

        Returns:
            ID de la tâche créée, ou None si échec
        """
        script = self._build_create_script(title, project, due_date, note)
        return await self._execute(script)

    async def complete_task(self, task_id: str) -> bool:
        """Marque une tâche comme complète"""
        script = f'''
        tell application "OmniFocus"
            tell default document
                set theTask to first flattened task whose id is "{task_id}"
                set completed of theTask to true
            end tell
        end tell
        '''
        result = await self._execute(script)
        return result is not None

    def _build_create_script(
        self,
        title: str,
        project: Optional[str],
        due_date: Optional[str],
        note: Optional[str]
    ) -> str:
        """Construit le script AppleScript"""

        # Échapper les guillemets
        title = title.replace('"', '\\"')
        note = (note or "").replace('"', '\\"')

        script = f'''
        tell application "OmniFocus"
            tell default document
                set newTask to make new inbox task with properties {{name:"{title}"}}
        '''

        if note:
            script += f'''
                set note of newTask to "{note}"
            '''

        if project:
            project = project.replace('"', '\\"')
            script += f'''
                set theProject to first flattened project whose name is "{project}"
                move newTask to end of tasks of theProject
            '''

        if due_date:
            script += f'''
                set due date of newTask to date "{due_date}"
            '''

        script += '''
                return id of newTask
            end tell
        end tell
        '''

        return script

    async def _execute(self, script: str) -> Optional[str]:
        """Exécute un script AppleScript"""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.error(f"OmniFocus error: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error("OmniFocus timeout")
            return None
        except Exception as e:
            logger.error(f"OmniFocus exception: {e}")
            return None
```

**Effort** : 🟡 4h

---

### 1.6 `tests/unit/test_v2_workflow.py` (~200 lignes)

```python
"""Tests pour Workflow v2.1"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.models.v2_models import Extraction, AnalysisResult
from src.sancho.analyzer import EventAnalyzer
from src.passepartout.enricher import PKMEnricher


class TestEventAnalyzer:
    """Tests pour EventAnalyzer"""

    @pytest.fixture
    def analyzer(self):
        router = AsyncMock()
        templates = MagicMock()
        config = MagicMock(
            default_model="haiku",
            escalation_model="sonnet",
            escalation_threshold=0.7
        )
        return EventAnalyzer(router, templates, config)

    async def test_analyze_haiku_confident(self, analyzer):
        """Haiku confiant → pas d'escalade"""
        analyzer.ai_router.analyze_with_prompt.return_value = (
            '{"extractions": [], "action": "archive", "confidence": 0.9, "raisonnement": "Newsletter"}',
            {"total_tokens": 500}
        )

        result = await analyzer.analyze(MagicMock(), [])

        assert result.model_used == "haiku"
        assert result.confidence == 0.9
        assert analyzer.ai_router.analyze_with_prompt.call_count == 1

    async def test_analyze_escalation(self, analyzer):
        """Haiku pas confiant → escalade Sonnet"""
        analyzer.ai_router.analyze_with_prompt.side_effect = [
            ('{"extractions": [], "action": "queue", "confidence": 0.5, "raisonnement": "Incertain"}',
             {"total_tokens": 500}),
            ('{"extractions": [], "action": "archive", "confidence": 0.85, "raisonnement": "OK"}',
             {"total_tokens": 800})
        ]

        result = await analyzer.analyze(MagicMock(), [])

        assert result.model_used == "sonnet"
        assert result.confidence == 0.85
        assert analyzer.ai_router.analyze_with_prompt.call_count == 2


class TestPKMEnricher:
    """Tests pour PKMEnricher"""

    @pytest.fixture
    def enricher(self):
        notes = MagicMock()
        omnifocus = AsyncMock()
        config = MagicMock(omnifocus_enabled=True)
        return PKMEnricher(notes, omnifocus, config)

    async def test_apply_enrichir_note(self, enricher):
        """Enrichit une note existante"""
        enricher.notes.get_by_title.return_value = MagicMock(note_id="note_123")

        result = AnalysisResult(
            extractions=[
                Extraction(
                    info="Budget validé 50k€",
                    type="decision",
                    importance="haute",
                    note_cible="Projet Alpha",
                    note_action="enrichir",
                    omnifocus=False
                )
            ],
            action="archive",
            confidence=0.9,
            raisonnement="",
            model_used="haiku",
            tokens_used=500,
            duration_ms=1000
        )

        enrichment = await enricher.apply(result, "event_123")

        assert "note_123" in enrichment.notes_updated
        assert len(enrichment.notes_created) == 0
        enricher.notes.add_info.assert_called_once()

    async def test_apply_create_note(self, enricher):
        """Crée une nouvelle note"""
        enricher.notes.get_by_title.return_value = None
        enricher.notes.create.return_value = MagicMock(note_id="note_new")

        result = AnalysisResult(
            extractions=[
                Extraction(
                    info="Nouveau projet",
                    type="fait",
                    importance="haute",
                    note_cible="Projet Beta",
                    note_action="creer",
                    omnifocus=False
                )
            ],
            action="archive",
            confidence=0.9,
            raisonnement="",
            model_used="haiku",
            tokens_used=500,
            duration_ms=1000
        )

        enrichment = await enricher.apply(result, "event_123")

        assert "note_new" in enrichment.notes_created
        enricher.notes.create.assert_called_once()

    async def test_apply_omnifocus(self, enricher):
        """Crée une tâche OmniFocus"""
        enricher.notes.get_by_title.return_value = MagicMock(note_id="note_123")
        enricher.omnifocus.create_task.return_value = "task_456"

        result = AnalysisResult(
            extractions=[
                Extraction(
                    info="Livrer rapport lundi",
                    type="deadline",
                    importance="haute",
                    note_cible="Projet Alpha",
                    note_action="enrichir",
                    omnifocus=True
                )
            ],
            action="archive",
            confidence=0.9,
            raisonnement="",
            model_used="haiku",
            tokens_used=500,
            duration_ms=1000
        )

        enrichment = await enricher.apply(result, "event_123")

        assert "task_456" in enrichment.tasks_created
        enricher.omnifocus.create_task.assert_called_once()
```

**Effort** : 🟡 4h

---

## 2. Fichiers à Modifier

### 2.1 `src/core/config_manager.py`

```python
# Ajouter après les autres configs

class WorkflowV2Config(BaseSettings):
    """Configuration Workflow v2.1"""

    model_config = SettingsConfigDict(env_prefix="WORKFLOW_V2_")

    # Activation
    enabled: bool = True

    # Modèles
    default_model: str = "haiku"
    escalation_model: str = "sonnet"
    escalation_threshold: float = 0.7

    # Contexte
    context_notes_count: int = 3
    context_note_max_chars: int = 300
    event_content_max_chars: int = 2000

    # Application
    auto_apply_threshold: float = 0.85
    notify_threshold: float = 0.7

    # OmniFocus
    omnifocus_enabled: bool = True
    omnifocus_default_project: str = "Inbox"
```

**Effort** : 🟢 1h

---

### 2.2 `src/trivelin/processor.py`

```python
# Dans EmailProcessor.__init__, ajouter:
from src.sancho.analyzer import EventAnalyzer
from src.passepartout.enricher import PKMEnricher

self.analyzer = EventAnalyzer(...)
self.enricher = PKMEnricher(...)

# Dans process_email, remplacer le pipeline cognitif par:
async def process_email(self, email: EmailMessage) -> ProcessingResult:
    # 1. Perception (existant)
    perceived = self.perceive(email)

    # 2. Contexte
    context = await self.context_engine.get_context(perceived)

    # 3. Analyse v2
    if self.config.workflow_v2.enabled:
        analysis = await self.analyzer.analyze(perceived, context)

        # 4. Application (si confiance suffisante)
        if analysis.confidence >= self.config.workflow_v2.auto_apply_threshold:
            enrichment = await self.enricher.apply(analysis, perceived.event_id)
            await self._execute_action(analysis.action, perceived)
        else:
            await self._queue_for_review(perceived, analysis)

        return ProcessingResult(
            event_id=perceived.event_id,
            analysis=analysis,
            enrichment=enrichment
        )

    # Fallback v1
    return await self._process_v1(perceived)
```

**Effort** : 🟡 3h

---

### 2.3 `src/passepartout/note_manager.py`

```python
# Ajouter méthode:

async def add_info(
    self,
    note_id: str,
    info: str,
    info_type: str,
    importance: str,
    source_id: str
) -> bool:
    """
    Ajoute une information à une note existante.

    Format dans la note:
    - **2026-01-11** : {info} — [source](scapin://event/{source_id})
    """
    note = self.get_note(note_id)
    if not note:
        return False

    # Trouver ou créer la section appropriée
    section = self._get_or_create_section(note, info_type)

    # Formatter l'entrée
    date = datetime.now().strftime("%Y-%m-%d")
    entry = f"- **{date}** : {info} — [source](scapin://event/{source_id})"

    # Ajouter à la section
    section.content += f"\n{entry}"

    # Sauvegarder
    await self.update_note(note)

    return True

def _get_or_create_section(self, note: Note, info_type: str) -> Section:
    """Trouve ou crée une section selon le type d'info"""
    section_names = {
        "decision": "Décisions",
        "engagement": "Engagements",
        "fait": "Faits",
        "deadline": "Jalons",
        "relation": "Relations"
    }
    section_name = section_names.get(info_type, "Informations")
    # ... logique pour trouver/créer section
```

**Effort** : 🟡 3h

---

### 2.4 `src/jeeves/api/routers/queue.py`

Modifications mineures pour supporter les nouveaux types de queue items.

**Effort** : 🟢 1h

---

## 3. Récapitulatif

### 3.1 Effort Total

| Composant | Effort |
|-----------|--------|
| v2_models.py | 2h |
| analyzer.py | 4h |
| extraction.j2 | 2h |
| enricher.py | 6h |
| omnifocus.py | 4h |
| test_v2_workflow.py | 4h |
| config_manager.py | 1h |
| processor.py | 3h |
| note_manager.py | 3h |
| queue.py | 1h |
| **TOTAL** | **30h (~4 jours)** |

### 3.2 Ordre d'Implémentation

```
Jour 1: Fondations
├── v2_models.py
├── config_manager.py
└── Tests modèles

Jour 2: Analyse
├── extraction.j2
├── analyzer.py
└── Tests analyzer (mocks)

Jour 3: Application
├── note_manager.py (add_info)
├── enricher.py
├── omnifocus.py
└── Tests enricher

Jour 4: Intégration
├── processor.py
├── queue.py
├── Tests intégration
└── Documentation
```

---

## 4. Risques et Mitigations

| Risque | Mitigation |
|--------|------------|
| OmniFocus AppleScript fragile | Fallback: créer note "À faire" |
| Haiku qualité insuffisante | Seuil escalade ajustable |
| Coûts API plus élevés que prévu | Monitoring + réduction contexte |
| Conflits enrichissement | Queue pour validation |

---

*Plan d'implémentation du 11 janvier 2026*
