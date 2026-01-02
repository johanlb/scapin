"""
Sganarelle Constants

Constantes centralisées pour tous les seuils, poids, timeouts, et valeurs
configurables du module Sganarelle.

Améliore la maintenabilité et facilite le tuning des paramètres.
"""

# ============================================================================
# FEEDBACK PROCESSOR CONSTANTS
# ============================================================================

# Poids pour le calcul de correctness score
EXPLICIT_FEEDBACK_WEIGHT = 0.7
IMPLICIT_FEEDBACK_WEIGHT = 0.3

# Scores de base pour approval
BASE_SCORE_REJECTED = 0.2  # Minimum car peut être faux négatif
BASE_SCORE_APPROVED = 0.7  # Good but not perfect

# Pénalités pour corrections
CORRECTION_PENALTY = 0.5  # Multiplier si correction fournie
MODIFICATION_PENALTY = 0.7  # Multiplier si modification nécessaire

# Scores d'action quality
ACTION_EXECUTED_SCORE = 0.8  # Actions exécutées → likely good
ACTION_NOT_EXECUTED_SCORE = 0.3  # Actions non exécutées → likely poor
ACTION_NO_ACTIONS_SCORE = 0.5  # Pas d'actions → neutral
ACTION_MODIFICATION_PENALTY = 0.6  # Multiplier si action modifiée
ACTION_APPROVAL_BOOST = 1.2  # Multiplier si approval
ACTION_REJECTION_PENALTY = 0.5  # Multiplier si rejection

# Seuils de confiance pour reasoning quality
CONFIDENCE_LOW_THRESHOLD = 0.7
CONFIDENCE_HIGH_THRESHOLD = 0.8
UNDERCONFIDENCE_BOOST = 1.3  # Boost si underconfident
OVERCONFIDENCE_PENALTY = 0.5  # Penalty si overconfident

# Bonus/pénalités passes
SINGLE_PASS_BONUS = 1.1  # Quick convergence
MANY_PASSES_PENALTY = 0.7  # Many passes but wrong (4+)
MANY_PASSES_THRESHOLD = 4

# Seuils de temps pour implicit quality
TIME_TO_ACTION_SLOW_THRESHOLD = 60  # Seconds
TIME_TO_ACTION_MEDIUM_THRESHOLD = 30  # Seconds
TIME_SLOW_PENALTY = 0.7
TIME_MEDIUM_PENALTY = 0.85
TIME_FAST_IMPLICIT_THRESHOLD = 30  # For actual_correctness boost
TIME_FAST_BOOST = 1.2

# Seuils de scores
CORRECTNESS_LOW_THRESHOLD = 0.5
CORRECTNESS_MEDIUM_THRESHOLD = 0.6
ACTION_QUALITY_LOW_THRESHOLD = 0.5
REASONING_QUALITY_LOW_THRESHOLD = 0.6
HIGH_SCORES_THRESHOLD = 0.7  # Pour détection désalignement
EXCELLENT_DECISION_THRESHOLD = 0.9

# Seuils pour learning trigger
LEARNING_CORRECTNESS_THRESHOLD = 0.6
LEARNING_CONFIDENCE_ERROR_THRESHOLD = 0.2
LEARNING_REASONING_QUALITY_THRESHOLD = 0.6
LEARNING_PERFECT_CONFIRMATION_SCORE = 0.9
LEARNING_PERFECT_TIME_THRESHOLD = 60  # Seconds

# ============================================================================
# KNOWLEDGE UPDATER CONSTANTS
# ============================================================================

# Limites mémoire
MAX_APPLIED_UPDATES = 1000  # deque maxlen
MAX_FAILED_UPDATES = 1000  # deque maxlen

# Seuils de confiance
DEFAULT_MIN_CONFIDENCE_THRESHOLD = 0.7
UPDATE_BATCH_SIZE_DEFAULT = 50

# Scoring pour updates
UPDATE_SCORE_BOOST_NEW_ENTITY = 0.1
UPDATE_SCORE_BOOST_MULTIPLE_SOURCES = 0.2
UPDATE_SCORE_HIGH_QUALITY_THRESHOLD = 0.8

# ============================================================================
# PATTERN STORE CONSTANTS
# ============================================================================

# Configuration par défaut
DEFAULT_MIN_OCCURRENCES = 3
DEFAULT_MIN_SUCCESS_RATE = 0.6
DEFAULT_MAX_AGE_DAYS = 90

# Pattern update
PATTERN_CONFIDENCE_SUCCESS_BOOST = 1.05
PATTERN_CONFIDENCE_FAILURE_PENALTY = 0.9

# Pattern pruning
PATTERN_PRUNE_MIN_OCCURRENCES_MULTIPLIER = 2  # occurrences >= min * 2
PATTERN_PRUNE_SUCCESS_RATE_THRESHOLD = 0.5  # 50% du min_success_rate

# Relevance scoring
RELEVANCE_BASE_WEIGHT = 0.5
RELEVANCE_RECENCY_WEIGHT = 0.3
RELEVANCE_OCCURRENCE_WEIGHT = 0.2
RELEVANCE_RECENCY_MIN_FACTOR = 0.5
RELEVANCE_OCCURRENCE_MULTIPLIER = 5  # occurrences / (min * 5)

# ============================================================================
# PROVIDER TRACKER CONSTANTS
# ============================================================================

# Limites mémoire
MAX_HISTORY_PER_PROVIDER = 10000  # deque maxlen

# Configuration par défaut
DEFAULT_MAX_HISTORY_DAYS = 30
PRUNE_FREQUENCY = 100  # Prune every N calls

# Percentile calculation
P95_MIN_SAMPLES = 20  # Minimum samples for p95
P95_QUANTILE_INDEX = 18  # quantiles(n=20)[18] = p95

# Get best provider
MIN_CALLS_FOR_BEST = 10

# Scoring weights pour "balanced" mode
BEST_PROVIDER_QUALITY_WEIGHT = 0.4
BEST_PROVIDER_SPEED_WEIGHT = 0.3
BEST_PROVIDER_COST_WEIGHT = 0.3

# ============================================================================
# CONFIDENCE CALIBRATOR CONSTANTS
# ============================================================================

# Configuration par défaut
DEFAULT_NUM_BINS = 10
DEFAULT_MIN_SAMPLES_PER_BIN = 5
DEFAULT_SMOOTHING_FACTOR = 0.1
MAX_SAMPLES_PER_BIN = 1000  # deque maxlen

# Expected Calibration Error (ECE)
ECE_WELL_CALIBRATED_THRESHOLD = 0.1

# Auto-save frequency
CALIBRATOR_SAVE_FREQUENCY = 10  # Save every N samples

# Temperature scaling
TEMPERATURE_MIN_OBSERVATIONS = 5
TEMPERATURE_TEST_VALUES = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

# ============================================================================
# LEARNING ENGINE CONSTANTS
# ============================================================================

# Configuration par défaut
DEFAULT_ENABLE_KNOWLEDGE_UPDATES = True
DEFAULT_ENABLE_PATTERN_LEARNING = True
DEFAULT_ENABLE_PROVIDER_TRACKING = True
DEFAULT_ENABLE_CONFIDENCE_CALIBRATION = True
DEFAULT_MIN_CONFIDENCE_FOR_UPDATES = 0.7

# Pattern learning
PATTERN_SUCCESS_THRESHOLD = 0.7  # Minimum correctness for pattern
PATTERN_MATCHING_MIN_CONFIDENCE = 0.5
PATTERN_SUGGESTION_MIN_CONFIDENCE = 0.7

# Provider quality fallback
PROVIDER_QUALITY_SUCCESS_FALLBACK = 0.8
PROVIDER_QUALITY_FAILURE_FALLBACK = 0.3

# Success determination
PATTERN_SUCCESS_CORRECTNESS_THRESHOLD = 0.6

# ============================================================================
# CONVERSION CONSTANTS
# ============================================================================

# Rating scale conversion (1-5 → 0.0-1.0)
RATING_MIN = 1
RATING_MAX = 5
RATING_RANGE = RATING_MAX - RATING_MIN  # 4.0

# ============================================================================
# TYPE VALIDATION CONSTANTS
# ============================================================================

# UserFeedback
FEEDBACK_RATING_MIN = 1
FEEDBACK_RATING_MAX = 5

# ProviderScore
PROVIDER_SCORE_MIN_CONFIDENCE = 0.0
PROVIDER_SCORE_MAX_CONFIDENCE = 1.0

# General score bounds
SCORE_MIN = 0.0
SCORE_MAX = 1.0

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def clamp(value: float, min_val: float = SCORE_MIN, max_val: float = SCORE_MAX) -> float:
    """Clamp value to [min_val, max_val]"""
    return max(min_val, min(max_val, value))


def rating_to_score(rating: int) -> float:
    """Convert rating (1-5) to score (0.0-1.0)"""
    if not (RATING_MIN <= rating <= RATING_MAX):
        raise ValueError(f"Rating must be {RATING_MIN}-{RATING_MAX}, got {rating}")
    return (rating - RATING_MIN) / RATING_RANGE


def score_to_rating(score: float) -> int:
    """Convert score (0.0-1.0) to rating (1-5)"""
    if not (SCORE_MIN <= score <= SCORE_MAX):
        raise ValueError(f"Score must be {SCORE_MIN}-{SCORE_MAX}, got {score}")
    return int(score * RATING_RANGE) + RATING_MIN
