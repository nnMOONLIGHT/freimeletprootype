"""AI-стилист: анализ изображений и подбор направлений."""

import json
import numpy as np
from .features import extract_features
from .network import MLP

STYLES = [
    "минимализм",
    "streetwear",
    "винтаж",
    "бохо",
    "techwear",
    "классика",
    "спорт-шик",
    "арт-брут",
]

HOBBIES = [
    "дизайн и графика",
    "3D и цифровое",
    "fashion",
    "ремесло",
    "фото и видео",
    "тексты и музыка",
]

CLOTHING = {
    "минимализм": ["базовые футболки", "прямые брюки", "тонкие кольца", "минималистичные кроссовки"],
    "streetwear": ["оверсайз худи", "карго", "кепка", "chunky-кроссовки"],
    "винтаж": ["винтажные джинсы", "кожаная куртка", "шёлковый шарф", "ботинки на платформе"],
    "бохо": ["flowy-платье", "fringe-сумка", "сандалии", "украшения ручной работы"],
    "techwear": ["мембранная куртка", "тактические штаны", "crossbody-сумка", "монохромные кроссовки"],
    "классика": ["пиджак", "рубашка", "loafers", "структурированная сумка"],
    "спорт-шик": ["спортивный топ", "wide-leg", "кеды", "спортивная сумка"],
    "арт-брут": ["асимметричный верх", "statement-аксессуары", "custom-кроссовки", "handmade украшения"],
}

TYPOGRAPHY = {
    "минимализм": "Geometric Sans — Inter, Montserrat",
    "streetwear": "Bold Display — Bebas, Druk",
    "винтаж": "Serif — Playfair, Cormorant",
    "бохо": "Handwritten — Caveat, Pacifico",
    "techwear": "Mono + Sans — JetBrains Mono, IBM Plex",
    "классика": "Transitional Serif — Libre Baskerville",
    "спорт-шик": "Rounded Sans — Nunito, Quicksand",
    "арт-брут": "Experimental — Space Grotesk, Syne",
}


def _build_pretrained():
    """Веса, обученные на синтетических парах признак→метка."""
    input_dim = 24 + 15 + 9  # hist + dom + extra
    net = MLP(input_dim, (48, 24), len(STYLES) + len(HOBBIES))

    rng = np.random.default_rng(2024)
    for _ in range(120):
        vec = rng.random(input_dim).astype(np.float32)
        target = np.zeros(len(STYLES) + len(HOBBIES), dtype=np.float32)

        if vec[8] < 0.15:  # низкая насыщенность → минимализм
            target[0] = 1
            target[8] = 1
        elif vec[-2] > 0.3:  # тёплые тона → бохо/винтаж
            target[2 if vec[-1] < 0.4 else 3] = 1
            target[10] = 1
        elif vec[-3] > 0.5:  # высокая контрастность → streetwear
            target[1] = 1
            target[9] = 1
        elif vec[20] > 0.4:  # edge density → techwear
            target[4] = 1
            target[11] = 1
        else:
            idx = int(vec[0] * len(STYLES)) % len(STYLES)
            target[idx] = 1
            target[8 + int(vec[1] * len(HOBBIES)) % len(HOBBIES)] = 1

        net.backward(vec, target.reshape(1, -1), lr=0.08)

    return net


class StyleAnalyzer:
    _instance = None

    def __init__(self):
        self.net = _build_pretrained()

    @classmethod
    def shared(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def analyze(self, image_path):
        features = extract_features(image_path)
        raw = self.net.predict(features)

        style_scores = raw[: len(STYLES)]
        hobby_scores = raw[len(STYLES) :]

        top_styles = np.argsort(style_scores)[::-1][:3]
        top_hobbies = np.argsort(hobby_scores)[::-1][:2]

        main_style = STYLES[int(top_styles[0])]
        palette = self._palette_from_features(features)

        traits = self._visual_traits(features)
        clothing = CLOTHING.get(main_style, CLOTHING["минимализм"])
        typo = TYPOGRAPHY.get(main_style, "Sans-serif")

        return {
            "styles": [
                {"name": STYLES[i], "score": round(float(style_scores[i]) * 100)}
                for i in top_styles
            ],
            "hobbies": [
                {"name": HOBBIES[i], "score": round(float(hobby_scores[i]) * 100)}
                for i in top_hobbies
            ],
            "main_style": main_style,
            "typography": typo,
            "visual_traits": traits,
            "clothing": clothing,
            "palette": palette,
            "summary": self._summary(main_style, traits, HOBBIES[int(top_hobbies[0])]),
        }

    def _palette_from_features(self, f):
        dom_start = 24
        colors = []
        for i in range(5):
            r, g, b = f[dom_start + i * 3 : dom_start + i * 3 + 3]
            colors.append(
                {
                    "hex": "#{:02x}{:02x}{:02x}".format(
                        int(np.clip(r * 255, 0, 255)),
                        int(np.clip(g * 255, 0, 255)),
                        int(np.clip(b * 255, 0, 255)),
                    )
                }
            )
        return colors[:5]

    def _visual_traits(self, f):
        sat, val, _, edge, _, tex, _, warm, contrast = f[-9:].tolist()
        traits = []
        if val > 0.55:
            traits.append("светлая подача")
        elif val < 0.35:
            traits.append("тёмная подача")
        if sat < 0.25:
            traits.append("приглушённая палитра")
        elif sat > 0.45:
            traits.append("насыщенные цвета")
        if edge > 0.08:
            traits.append("чёткие контуры")
        if tex > 0.15:
            traits.append("выраженная фактура")
        if warm > 0.05:
            traits.append("тёплые оттенки")
        elif warm < -0.05:
            traits.append("холодные оттенки")
        if contrast > 0.45:
            traits.append("высокий контраст")
        return traits or ["сбалансированная композиция"]

    def _summary(self, style, traits, hobby):
        trait_str = ", ".join(traits[:3])
        return (
            f"Визуальный профиль: {trait_str}. "
            f"Основной стиль — {style}, близкое направление — {hobby}. "
            f"Рекомендуем опираться на эту эстетику в портфолио и подборе материалов."
        )

    def to_json(self, result):
        return json.dumps(result, ensure_ascii=False)
