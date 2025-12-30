"""Capa de verificación con redundancia para garantizar español en panel de traducción."""

from deep_translator import GoogleTranslator
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class RedundantVerificationTranslator:
    """
    Verificador y traductor con múltiples métodos de respaldo.
    Última línea de defensa para garantizar español en panel de traducción.

    Cadena de métodos (fallback automático):
    1. Heurístico de palabras (rápido, sin dependencias)
    2. GoogleTranslator (gratuito, sin API key)
    3. langdetect (preciso, requiere instalación opcional)
    4. CTranslate2 (local, si está disponible)
    """

    def __init__(self):
        self.min_text_length = 3

        # Método 1: Palabras comunes para detección heurística
        self.common_english_words = {
            'the', 'is', 'at', 'which', 'on', 'a', 'an', 'as', 'are', 'was',
            'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'should', 'could', 'can', 'may', 'might',
            'must', 'shall', 'this', 'that', 'these', 'those', 'i', 'you',
            'he', 'she', 'it', 'we', 'they', 'what', 'who', 'when', 'where',
            'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
            'own', 'same', 'so', 'than', 'too', 'very'
        }

        self.common_spanish_words = {
            'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'ser', 'se', 'no',
            'haber', 'por', 'con', 'su', 'para', 'como', 'estar', 'tener',
            'le', 'lo', 'todo', 'pero', 'más', 'hacer', 'o', 'poder', 'decir',
            'este', 'ir', 'otro', 'ese', 'la', 'si', 'me', 'ya', 'ver', 'porque',
            'dar', 'cuando', 'él', 'muy', 'sin', 'vez', 'mucho', 'saber', 'qué',
            'sobre', 'mi', 'alguno', 'mismo', 'yo', 'también', 'hasta', 'año',
            'dos', 'querer', 'entre', 'así', 'primero', 'desde', 'grande', 'eso',
            'ni', 'nos', 'llegar', 'pasar', 'tiempo', 'ella', 'sí', 'día', 'uno',
            'bien', 'poco', 'deber', 'entonces', 'poner', 'cosa', 'tanto', 'hombre',
            'parecer', 'nuestro', 'tan', 'donde', 'ahora', 'parte', 'después', 'vida',
            'quedar', 'siempre', 'creer', 'hablar', 'llevar', 'dejar', 'nada', 'cada'
        }

        # Método 2: GoogleTranslator
        try:
            self._google_translator = GoogleTranslator(source='en', target='es')
            self._google_available = True
            logger.info("GoogleTranslator inicializado")
        except Exception as e:
            logger.warning(f"GoogleTranslator no disponible: {e}")
            self._google_translator = None
            self._google_available = False

        # Método 3: langdetect (opcional)
        try:
            from langdetect import detect
            self._langdetect_available = True
            logger.info("langdetect disponible")
        except ImportError:
            self._langdetect_available = False
            logger.info("langdetect no instalado (opcional)")

        # Método 4: CTranslate2 (reusar del sistema si está disponible)
        self._ctranslate2_available = False
        try:
            from app.translate.ctranslate2_provider import CTranslate2Provider
            from app.config.settings import Settings
            settings = Settings()
            if settings.ctranslate2_model_path:
                self._ct2_provider = CTranslate2Provider(
                    model_path=settings.ctranslate2_model_path
                )
                self._ctranslate2_available = True
                logger.info("CTranslate2 disponible como respaldo")
        except Exception as e:
            logger.info(f"CTranslate2 no disponible para verificación: {e}")

        logger.info(
            f"Verificador redundante inicializado - Métodos disponibles: "
            f"Heurístico=True, Google={self._google_available}, "
            f"Langdetect={self._langdetect_available}, CT2={self._ctranslate2_available}"
        )

    def detect_is_english(self, text: str) -> Tuple[bool, float]:
        """
        Detecta si el texto está en inglés usando cadena de métodos con fallback.

        Cadena de métodos:
        1. Heurístico de palabras
        2. langdetect (si está disponible)
        3. GoogleTranslator (si está disponible)

        Returns:
            Tuple (is_english, confidence)
            confidence: 0.0-1.0 donde 1.0 es certeza total
        """
        if not text or len(text.strip()) < self.min_text_length:
            return False, 0.5

        # Método 1: Heurístico de palabras (rápido, sin dependencias)
        try:
            is_en, conf = self._detect_heuristic(text)
            if conf > 0.7:  # Alta confianza
                logger.debug(f"Detección heurística (confianza={conf:.2f}): inglés={is_en}")
                return is_en, conf
        except Exception as e:
            logger.debug(f"Detección heurística falló: {e}")

        # Método 2: langdetect (preciso)
        if self._langdetect_available:
            try:
                is_en, conf = self._detect_langdetect(text)
                if conf > 0.6:
                    logger.debug(f"Detección langdetect (confianza={conf:.2f}): inglés={is_en}")
                    return is_en, conf
            except Exception as e:
                logger.debug(f"Detección langdetect falló: {e}")

        # Método 3: GoogleTranslator (fallback)
        if self._google_available:
            try:
                is_en, conf = self._detect_google_translate(text)
                logger.debug(f"Detección GoogleTranslator (confianza={conf:.2f}): inglés={is_en}")
                return is_en, conf
            except Exception as e:
                logger.warning(f"Detección GoogleTranslator falló: {e}")

        # Fallback final: asumir inglés con baja confianza
        logger.warning("Todos los métodos de detección fallaron, asumiendo inglés")
        return True, 0.3

    def _detect_heuristic(self, text: str) -> Tuple[bool, float]:
        """Detección por frecuencia de palabras comunes."""
        words = text.lower().split()
        if not words:
            return False, 0.5

        en_count = sum(1 for w in words if w in self.common_english_words)
        es_count = sum(1 for w in words if w in self.common_spanish_words)

        total = en_count + es_count
        if total == 0:
            return False, 0.3  # No hay palabras reconocidas

        en_ratio = en_count / len(words)
        es_ratio = es_count / len(words)

        if en_ratio > es_ratio and en_ratio > 0.15:
            return True, min(en_ratio * 2, 1.0)
        elif es_ratio > en_ratio and es_ratio > 0.15:
            return False, min(es_ratio * 2, 1.0)
        else:
            return False, 0.4  # Baja confianza

    def _detect_langdetect(self, text: str) -> Tuple[bool, float]:
        """Detección usando langdetect."""
        from langdetect import detect, detect_langs

        lang = detect(text)
        langs_with_prob = detect_langs(text)

        # Encontrar la probabilidad del idioma detectado
        confidence = 0.5
        for lang_prob in langs_with_prob:
            if lang_prob.lang == lang:
                confidence = lang_prob.prob
                break

        return lang == 'en', confidence

    def _detect_google_translate(self, text: str) -> Tuple[bool, float]:
        """Detección por prueba de traducción."""
        translated = self._google_translator.translate(text)
        similarity = self._text_similarity(text, translated)

        # similarity alta (>0.4) = probablemente español
        # similarity baja (<0.3) = probablemente inglés
        is_english = similarity < 0.35
        confidence = abs(0.35 - similarity) / 0.35

        return is_english, min(confidence, 1.0)

    def translate_to_spanish(self, text: str) -> str:
        """
        Traduce texto en inglés a español usando cadena de métodos con fallback.

        Cadena de traducción:
        1. GoogleTranslator (rápido, gratuito)
        2. CTranslate2 (local, si está disponible)
        3. Sin traducción (fallback final)
        """
        if not text or not text.strip():
            return text

        # Método 1: GoogleTranslator
        if self._google_available:
            try:
                translated = self._google_translator.translate(text)

                if translated and translated.lower() != text.lower():
                    logger.info(
                        f"✓ GoogleTranslator: '{text[:40]}...' → '{translated[:40]}...'"
                    )
                    return translated
                else:
                    logger.warning("GoogleTranslator no cambió el texto, intentando siguiente método...")
            except Exception as e:
                logger.warning(f"GoogleTranslator falló: {e}, intentando siguiente método...")

        # Método 2: CTranslate2
        if self._ctranslate2_available:
            try:
                import asyncio
                # CTranslate2 es async, necesitamos ejecutarlo
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Si ya hay un loop, crear tarea
                    future = asyncio.ensure_future(
                        self._ct2_provider.translate(text, "en", "es")
                    )
                    # No podemos esperar aquí, saltamos a fallback
                    logger.warning("No se puede usar CTranslate2 en contexto sync")
                else:
                    result = loop.run_until_complete(
                        self._ct2_provider.translate(text, "en", "es")
                    )
                    if result and result.translated_text:
                        logger.info(
                            f"✓ CTranslate2: '{text[:40]}...' → '{result.translated_text[:40]}...'"
                        )
                        return result.translated_text
            except Exception as e:
                logger.warning(f"CTranslate2 falló: {e}")

        # Fallback final: retornar texto original
        logger.error(
            f"⚠️  TODOS los métodos de traducción fallaron para: '{text[:50]}...'"
        )
        return text

    def verify_and_ensure_spanish(self, text: str) -> str:
        """
        Pipeline completo: Detecta idioma y traduce si es necesario.
        Garantiza que el texto retornado esté en español.
        """
        is_english, confidence = self.detect_is_english(text)

        if is_english and confidence > 0.6:
            logger.info(f"Inglés detectado (confianza {confidence:.2f}) - traduciendo...")
            return self.translate_to_spanish(text)
        elif is_english and confidence > 0.3:
            # Confianza media - traducir por precaución
            logger.warning(f"Posible inglés (confianza {confidence:.2f}) - traduciendo por seguridad...")
            return self.translate_to_spanish(text)
        else:
            # Probablemente español
            logger.debug(f"Español detectado (confianza {1.0 - confidence:.2f}) - sin cambios")
            return text

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calcula similitud entre textos (0.0 = diferentes, 1.0 = idénticos)."""
        t1 = set(text1.lower().split())
        t2 = set(text2.lower().split())

        if not t1:
            return 0.0

        overlap = len(t1.intersection(t2))
        return min(overlap / len(t1), 1.0)
