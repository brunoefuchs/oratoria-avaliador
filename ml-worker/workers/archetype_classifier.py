"""Classificador de Arquetipos Vocais.

Identifica qual dos 4 arquetipos vocais o orador esta usando em cada trecho:

- Educador: ritmo mais lento, pitch descendente no fim das frases,
  tom autoritativo e estruturado. Termina frases com entonacao BAIXA.
- Coach: staccato (palavras separadas), energia alta, tom diretivo.
  Pausas curtas entre palavras, volume acima da media.
- Motivador: legato (palavras fluem juntas), tom aspiracional e suave.
  Ritmo fluido, pitch ascendente, volume crescente.
- Amigo: ritmo casual, tom conversacional e relaxado.
  Variacao natural, volume moderado, humor no tom.

O objetivo nao e estar em um arquetipo "certo", mas CICLAR entre eles.
Ficar preso em um so = default = nao-funcional.
"""

import numpy as np
import parselmouth
import structlog

logger = structlog.get_logger()

JANELA_ARQUETIPO = 10  # Analisa blocos de 10 segundos


def _extrair_features_janela(sound: parselmouth.Sound, t_inicio: float, t_fim: float) -> dict:
    """Extrai features acusticas de uma janela temporal para classificacao."""
    try:
        trecho = sound.extract_part(from_time=t_inicio, to_time=t_fim)
    except Exception:
        return None

    if trecho.get_total_duration() < 0.5:
        return None

    # Pitch
    pitch = trecho.to_pitch()
    pitch_values = pitch.selected_array["frequency"]
    pitch_voiced = pitch_values[pitch_values > 0]

    if len(pitch_voiced) < 5:
        return None

    pitch_mean = float(np.mean(pitch_voiced))
    pitch_std = float(np.std(pitch_voiced))

    # Tendencia do pitch (subindo ou descendo?)
    if len(pitch_voiced) > 10:
        meio = len(pitch_voiced) // 2
        pitch_primeira_metade = np.mean(pitch_voiced[:meio])
        pitch_segunda_metade = np.mean(pitch_voiced[meio:])
        tendencia_pitch = float(pitch_segunda_metade - pitch_primeira_metade)
    else:
        tendencia_pitch = 0.0

    # Intensidade (volume)
    intensity = trecho.to_intensity()
    if intensity.get_number_of_frames() < 2:
        return None

    int_values = intensity.values[0]
    int_mean = float(np.mean(int_values))
    int_std = float(np.std(int_values))

    # Tendencia de volume
    if len(int_values) > 10:
        meio = len(int_values) // 2
        vol_primeira = np.mean(int_values[:meio])
        vol_segunda = np.mean(int_values[meio:])
        tendencia_volume = float(vol_segunda - vol_primeira)
    else:
        tendencia_volume = 0.0

    # Staccato vs Legato (variacao rapida de intensidade = staccato)
    if len(int_values) > 2:
        diffs = np.abs(np.diff(int_values))
        staccato_index = float(np.mean(diffs))
    else:
        staccato_index = 0.0

    # Ratio silencio nesta janela
    threshold = int_mean - 8
    speech_frames = np.sum(int_values > threshold)
    speech_ratio = speech_frames / len(int_values) if len(int_values) > 0 else 0.0

    return {
        "pitch_mean": pitch_mean,
        "pitch_std": pitch_std,
        "tendencia_pitch": tendencia_pitch,
        "volume_mean": int_mean,
        "volume_std": int_std,
        "tendencia_volume": tendencia_volume,
        "staccato_index": staccato_index,
        "speech_ratio": float(speech_ratio),
    }


def _classificar_arquetipo(features: dict, media_global: dict) -> dict:
    """Classifica um trecho em um dos 4 arquetipos baseado nas features.

    Usa scoring por semelhanca com perfis prototipicos de cada arquetipo.
    """
    scores = {}

    # Normalizar features em relacao a media global
    pitch_rel = features["pitch_mean"] / (media_global["pitch_mean"] + 1e-8)
    vol_rel = features["volume_mean"] / (abs(media_global["volume_mean"]) + 1e-8)
    staccato_rel = features["staccato_index"] / (media_global["staccato_index"] + 1e-8)

    # EDUCADOR: pitch descendente, ritmo mais lento (mais pausas), volume estavel
    scores["educador"] = (
        max(0, -features["tendencia_pitch"] * 0.5)  # Pitch CAI no fim
        + max(0, (1.0 - features["speech_ratio"]) * 30)  # Mais pausas (explica)
        + max(0, (1.0 - staccato_rel) * 15)  # Menos staccato (fluido)
        + max(0, (1.0 - abs(vol_rel - 1.0)) * 20)  # Volume proximo da media
    )

    # COACH: staccato alto, volume acima da media, energia alta
    scores["coach"] = (
        max(0, (staccato_rel - 1.0) * 25)  # Mais staccato que a media
        + max(0, (vol_rel - 1.0) * 30)  # Volume acima da media
        + max(0, features["volume_std"] * 2)  # Variacao de volume (enfase)
        + max(0, features["speech_ratio"] * 15)  # Fala continua (diretivo)
    )

    # MOTIVADOR: pitch ascendente, volume crescente, legato
    scores["motivador"] = (
        max(0, features["tendencia_pitch"] * 0.5)  # Pitch SOBE
        + max(0, features["tendencia_volume"] * 3)  # Volume CRESCE
        + max(0, (1.0 - staccato_rel) * 20)  # Legato (fluido)
        + max(0, (pitch_rel - 1.0) * 15)  # Pitch acima da media
    )

    # AMIGO: volume moderado, pouca variacao, ritmo casual
    scores["amigo"] = (
        max(0, (1.0 - abs(vol_rel - 0.95)) * 25)  # Volume levemente abaixo
        + max(0, (1.0 - abs(features["pitch_std"] / (media_global["pitch_std"] + 1e-8) - 0.8)) * 15)
        + max(0, (1.0 - abs(staccato_rel - 0.9)) * 15)  # Staccato moderado
        + max(0, (1.0 - abs(features["speech_ratio"] - 0.75)) * 20)  # Ritmo casual
    )

    # Arquetipo dominante
    arquetipo = max(scores, key=scores.get)
    confianca = scores[arquetipo] / (sum(scores.values()) + 1e-8)

    return {
        "arquetipo": arquetipo,
        "confianca": round(float(confianca), 3),
        "scores": {k: round(float(v), 2) for k, v in scores.items()},
    }


def classify_archetypes(audio_path: str) -> dict:
    """Classifica arquetipos vocais ao longo do audio.

    Analisa janelas de JANELA_ARQUETIPO segundos e identifica:
    - Arquetipo dominante geral
    - Cycling entre arquetipos
    - Lock-in (preso em um so)
    - Mapa temporal de arquetipos
    """
    logger.info("archetype_classification_start", audio_path=audio_path)

    sound = parselmouth.Sound(audio_path)
    duracao = sound.get_total_duration()
    # N janelas uniformes cobrindo 100% da duracao (alvo ~10s cada)
    num_janelas = max(1, round(duracao / JANELA_ARQUETIPO))
    janela_dur = duracao / num_janelas

    # Primeira passada: extrair features de todas as janelas
    features_por_janela = []
    for j in range(num_janelas):
        t_inicio = j * janela_dur
        t_fim = (j + 1) * janela_dur
        features = _extrair_features_janela(sound, t_inicio, t_fim)
        if features:
            features["t_inicio"] = t_inicio
            features["t_fim"] = t_fim
            features_por_janela.append(features)

    if not features_por_janela:
        return {
            "score": 0,
            "confidence": "failed",
            "metrics": {},
        }

    # Calcular medias globais para normalizacao
    media_global = {
        "pitch_mean": float(np.mean([f["pitch_mean"] for f in features_por_janela])),
        "pitch_std": float(np.mean([f["pitch_std"] for f in features_por_janela])),
        "volume_mean": float(np.mean([f["volume_mean"] for f in features_por_janela])),
        "staccato_index": float(np.mean([f["staccato_index"] for f in features_por_janela])),
    }

    # Segunda passada: classificar cada janela
    classificacoes = []
    for features in features_por_janela:
        resultado = _classificar_arquetipo(features, media_global)
        resultado["t_inicio"] = features["t_inicio"]
        resultado["t_fim"] = features["t_fim"]
        classificacoes.append(resultado)

    # =============================================
    # METRICAS DE ARQUETIPOS
    # =============================================

    from collections import Counter

    arquetipos_usados = [c["arquetipo"] for c in classificacoes]
    contagem = Counter(arquetipos_usados)
    total = len(arquetipos_usados)

    # Distribuicao percentual
    distribuicao = {arq: round(count / total * 100, 1) for arq, count in contagem.items()}

    # Garantir todos os 4 presentes
    for arq in ["educador", "coach", "motivador", "amigo"]:
        if arq not in distribuicao:
            distribuicao[arq] = 0.0

    # Arquetipo dominante (default)
    arquetipo_dominante = contagem.most_common(1)[0][0] if contagem else "indefinido"
    pct_dominante = distribuicao.get(arquetipo_dominante, 0)

    # Arquetipos acessiveis (>10%) vs ausentes (<5%)
    acessiveis = [arq for arq, pct in distribuicao.items() if pct >= 10]
    ausentes = [arq for arq, pct in distribuicao.items() if pct < 5]

    # Cycling: quantas trocas de arquetipo ao longo do tempo
    trocas = 0
    for i in range(1, len(arquetipos_usados)):
        if arquetipos_usados[i] != arquetipos_usados[i - 1]:
            trocas += 1

    trocas_por_minuto = round(trocas / (duracao / 60), 1) if duracao > 0 else 0
    num_arquetipos_unicos = len(set(arquetipos_usados))

    # Lock-in: >70% em um unico arquetipo
    lock_in = pct_dominante > 70

    # =============================================
    # SCORE DE ARQUETIPOS (0-100)
    # =============================================

    # 1. Diversidade de arquetipos — peso 40%
    # Story 7.1 AC-1: combina cobertura (quantos dos 4 arquetipos foram usados)
    # com evenness (quao equilibrado e o uso entre os usados).
    #   1 arquetipo em 100%  = 0
    #   2 em 50/50           = ~50
    #   4 igualmente (25%)   = 100
    #   2 em 80/20           = ~36 (penalizado por desequilibrio interno)
    if num_arquetipos_unicos <= 1:
        diversidade_score = 0.0
    else:
        valores_norm = [pct / 100.0 for pct in distribuicao.values() if pct > 0]
        entropy = -sum(v * np.log(v) for v in valores_norm)
        # Max entropy = log(N) onde N = arquetipos usados (uso equilibrado entre eles).
        # Isso isola "evenness interna" da "cobertura".
        max_entropy = np.log(num_arquetipos_unicos)
        evenness = entropy / max_entropy if max_entropy > 0 else 0
        diversidade_score = (num_arquetipos_unicos / 4) * evenness * 100

    # 2. Cycling (trocas por minuto) — peso 30%
    #    Ideal: 2-5 trocas/min
    if trocas_por_minuto < 1:
        cycling_score = 20  # Quase nao troca
    elif trocas_por_minuto <= 2:
        cycling_score = 50 + (trocas_por_minuto - 1) * 30
    elif trocas_por_minuto <= 5:
        cycling_score = 80 + (trocas_por_minuto - 2) * 7
    else:
        cycling_score = max(
            60, 100 - (trocas_por_minuto - 5) * 10
        )  # Demais trocas = inconsistencia

    # 3. Anti-lock-in — peso 30%
    #    Penaliza concentracao excessiva em um arquetipo
    if pct_dominante > 80:
        lockin_score = 10
    elif pct_dominante > 70:
        lockin_score = 30
    elif pct_dominante > 50:
        lockin_score = 60
    elif pct_dominante > 35:
        lockin_score = 90
    else:
        lockin_score = 100  # Distribuicao equilibrada

    archetype_score = round(diversidade_score * 0.40 + cycling_score * 0.30 + lockin_score * 0.30)
    archetype_score = max(0, min(100, archetype_score))

    logger.info(
        "archetype_classification_complete",
        score=archetype_score,
        dominante=arquetipo_dominante,
        lock_in=lock_in,
        trocas_por_min=trocas_por_minuto,
        num_unicos=num_arquetipos_unicos,
    )

    return {
        "score": archetype_score,
        "confidence": "high" if len(features_por_janela) >= 3 else "medium",
        "metrics": {
            "arquetipo_dominante": arquetipo_dominante,
            "distribuicao": distribuicao,
            "acessiveis": acessiveis,
            "ausentes": ausentes,
            "lock_in": lock_in,
            "pct_dominante": pct_dominante,
            "trocas_por_minuto": trocas_por_minuto,
            "num_arquetipos_usados": num_arquetipos_unicos,
            "total_janelas": len(classificacoes),
            "mapa_temporal": [
                {
                    "inicio": c["t_inicio"],
                    "fim": c["t_fim"],
                    "arquetipo": c["arquetipo"],
                    "confianca": c["confianca"],
                }
                for c in classificacoes
            ],
            "sub_scores": {
                "diversidade": round(diversidade_score),
                "cycling": round(cycling_score),
                "anti_lockin": round(lockin_score),
            },
        },
    }
