import time

import mediapipe as mp
import numpy as np
import structlog

from workers.posture_analyzer import extract_frames

logger = structlog.get_logger()

HAND_MODEL_PATH = "/tmp/mediapipe_models/hand_landmarker.task"
FACE_MODEL_PATH = "/tmp/mediapipe_models/face_landmarker.task"

# Limiar para considerar gaze centrado (nariz alinhado entre olhos)
# MP-1: reduzido de 0.35→0.22 pra captar desvios reais (era inflado a 100%)
GAZE_THRESHOLD = 0.22
# Duracao ideal de contato visual por "fixacao" (segundos entre frames a 2fps)
FIXACAO_MIN_FRAMES = 2  # 1s minimo
FIXACAO_MAX_FRAMES = 10  # 5s maximo antes de ficar desconfortavel


def _estimar_direcao_olhar(face_landmarks) -> dict:
    """Estima direcao do olhar com mais granularidade que apenas centrado/nao.

    Retorna:
        direcao: 'camera', 'baixo', 'esquerda', 'direita', 'cima'
        centrado: bool
        angulo_vertical: float (negativo = baixo, positivo = cima)
    """
    lm = face_landmarks
    olho_esq = np.array([lm[33].x, lm[33].y])
    olho_dir = np.array([lm[263].x, lm[263].y])
    nariz = np.array([lm[1].x, lm[1].y])
    queixo = np.array([lm[152].x, lm[152].y])
    testa = np.array([lm[10].x, lm[10].y])

    centro_olhos = (olho_esq + olho_dir) / 2
    offset = nariz - centro_olhos
    dist_olhos = np.linalg.norm(olho_dir - olho_esq)

    offset_normalizado_x = offset[0] / (dist_olhos + 1e-8)
    offset_normalizado_y = offset[1] / (dist_olhos + 1e-8)

    centrado = (
        abs(offset_normalizado_x) < GAZE_THRESHOLD
        and abs(offset_normalizado_y) < GAZE_THRESHOLD * 1.2
    )

    # Angulo vertical da cabeca (inclinacao)
    vetor_face = testa - queixo
    angulo_vertical = float(np.degrees(np.arctan2(vetor_face[0], vetor_face[1])))

    # Classificar direcao
    if centrado:
        direcao = "camera"
    elif offset_normalizado_y > GAZE_THRESHOLD * 1.2:
        direcao = "baixo"
    elif offset_normalizado_y < -GAZE_THRESHOLD:
        direcao = "cima"
    elif offset_normalizado_x > GAZE_THRESHOLD:
        direcao = "direita"
    else:
        direcao = "esquerda"

    # MP-1: Classificar tipo de desvio (positivo/negativo/neutro)
    if centrado:
        tipo_desvio = "nenhum"
    elif direcao == "baixo":
        tipo_desvio = "negativo"
    elif direcao == "cima":
        tipo_desvio = "positivo"
    else:
        tipo_desvio = "neutro"

    return {
        "direcao": direcao,
        "centrado": centrado,
        "tipo_desvio": tipo_desvio,
        "angulo_vertical": round(angulo_vertical, 1),
        "offset_x": round(float(offset_normalizado_x), 3),
        "offset_y": round(float(offset_normalizado_y), 3),
    }


def _classificar_posicao_mao(hand_landmarks) -> dict:
    """Classifica a posicao e gesto de uma mao detectada.

    Retorna zona (alta/media/baixa), abertura (aberta/fechada),
    e posicao relativa para medir vocabulario de gestos.
    """
    wrist = np.array([hand_landmarks[0].x, hand_landmarks[0].y])
    middle_tip = np.array([hand_landmarks[12].x, hand_landmarks[12].y])
    index_tip = np.array([hand_landmarks[8].x, hand_landmarks[8].y])
    pinky_tip = np.array([hand_landmarks[20].x, hand_landmarks[20].y])

    # Zona vertical — MP-3 fix: ampliada de 0.65→0.80 pra "media"
    # Em vídeos bust/portrait, mãos em posição natural caem em y=0.6-0.75
    if wrist[1] < 0.35:
        zona = "alta"
    elif wrist[1] < 0.80:
        zona = "media"
    else:
        zona = "baixa"

    # Abertura da mao (distancia entre dedos)
    spread = np.linalg.norm(index_tip - pinky_tip)
    aberta = spread > 0.08

    # Direcao do gesto (palma vs apontar)
    direcao_mao = middle_tip - wrist
    apontando = abs(direcao_mao[0]) > abs(direcao_mao[1]) * 0.8

    # Posicao quantizada para medir vocabulario (grid 3x3)
    pos_x = int(wrist[0] * 3)  # 0, 1, 2
    pos_y = int(wrist[1] * 3)  # 0, 1, 2
    posicao_grid = f"{pos_x}_{pos_y}"

    return {
        "zona": zona,
        "aberta": aberta,
        "apontando": apontando,
        "posicao_grid": posicao_grid,
        "wrist_y": float(wrist[1]),
    }


def _compute_gesture_metrics(video_path: str) -> dict:
    """Analisa gestos, contato visual e linguagem corporal das maos."""
    start = time.time()
    logger.info("gesture_analysis_start", video_path=video_path)

    frames = extract_frames(video_path, fps=2)
    if not frames:
        return {"score": 0, "confidence": "failed", "metrics": {}}

    BaseOptions = mp.tasks.BaseOptions
    HandLandmarker = mp.tasks.vision.HandLandmarker
    HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
    FaceLandmarker = mp.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    hand_options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=HAND_MODEL_PATH),
        running_mode=VisionRunningMode.IMAGE,
        num_hands=2,
    )

    face_options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=FACE_MODEL_PATH),
        running_mode=VisionRunningMode.IMAGE,
        num_faces=1,
    )

    total_frames = len(frames)

    # Contadores basicos
    hand_detected_count = 0
    face_detected_count = 0

    # Contato visual detalhado
    contato_visual_frames = 0
    olhar_baixo_frames = 0
    desvio_positivo_frames = 0  # MP-1: reflexivo (cima)
    desvio_negativo_frames = 0  # MP-1: evasivo (baixo)
    desvio_neutro_frames = 0    # MP-1: lateral (scanning)
    direcoes_olhar = []  # historico de direcoes para medir distribuicao

    # Gestos detalhados
    duas_maos_count = 0
    uma_mao_count = 0
    zona_alta_count = 0
    zona_media_count = 0
    zona_baixa_count = 0
    posicoes_grid_vistas = set()  # vocabulario de posicoes
    maos_abertas_count = 0
    maos_fechadas_count = 0
    frames_com_mao_detectada = 0  # maos visiveis no frame
    frames_com_gesto_ativo = 0  # maos COM MOVIMENTO significativo

    # Tracking de posicao para medir MOVIMENTO real (nao so presenca)
    prev_wrist_positions = []  # posicoes do frame anterior
    GESTO_MOVEMENT_THRESHOLD = 0.02  # deslocamento minimo para contar como gesto ativo

    # Consistencia temporal do gesto (mesmo gesto repetido = default)
    ultimas_posicoes = []

    hand_landmarker = HandLandmarker.create_from_options(hand_options)
    face_landmarker = FaceLandmarker.create_from_options(face_options)

    for frame_path in frames:
        image = mp.Image.create_from_file(frame_path)

        # --- DETECCAO DE MAOS ---
        hand_results = hand_landmarker.detect(image)
        num_maos_no_frame = 0

        if hand_results.hand_landmarks and len(hand_results.hand_landmarks) > 0:
            hand_detected_count += 1
            frames_com_mao_detectada += 1
            num_maos_no_frame = len(hand_results.hand_landmarks)

            if num_maos_no_frame >= 2:
                duas_maos_count += 1
            else:
                uma_mao_count += 1

            # Coletar posicoes dos pulsos para medir MOVIMENTO
            current_wrist_positions = []
            for hand_lm in hand_results.hand_landmarks:
                info = _classificar_posicao_mao(hand_lm)
                current_wrist_positions.append(info["wrist_y"])

                if info["zona"] == "alta":
                    zona_alta_count += 1
                elif info["zona"] == "media":
                    zona_media_count += 1
                else:
                    zona_baixa_count += 1

                if info["aberta"]:
                    maos_abertas_count += 1
                else:
                    maos_fechadas_count += 1

                posicoes_grid_vistas.add(info["posicao_grid"])
                ultimas_posicoes.append(info["posicao_grid"])

            # Medir MOVIMENTO real: comparar posicao com frame anterior
            if prev_wrist_positions:
                max_displacement = 0.0
                for curr_y in current_wrist_positions:
                    for prev_y in prev_wrist_positions:
                        displacement = abs(curr_y - prev_y)
                        max_displacement = max(max_displacement, displacement)
                if max_displacement > GESTO_MOVEMENT_THRESHOLD:
                    frames_com_gesto_ativo += 1
            else:
                # Primeiro frame com maos — nao conta como gesto ativo
                pass

            prev_wrist_positions = current_wrist_positions
        else:
            prev_wrist_positions = []  # reset se maos saem do frame

        # --- DETECCAO DE ROSTO / OLHAR ---
        face_results = face_landmarker.detect(image)
        if face_results.face_landmarks and len(face_results.face_landmarks) > 0:
            face_detected_count += 1
            olhar = _estimar_direcao_olhar(face_results.face_landmarks[0])
            direcoes_olhar.append(olhar["direcao"])

            if olhar["centrado"]:
                contato_visual_frames += 1
            if olhar["direcao"] == "baixo":
                olhar_baixo_frames += 1
            # MP-1: track deviation types
            if olhar.get("tipo_desvio") == "positivo":
                desvio_positivo_frames += 1
            elif olhar.get("tipo_desvio") == "negativo":
                desvio_negativo_frames += 1
            elif olhar.get("tipo_desvio") == "neutro":
                desvio_neutro_frames += 1

    hand_landmarker.close()
    face_landmarker.close()

    # =============================================
    # METRICAS CALCULADAS
    # =============================================

    # gesticulation_pct mede MOVIMENTO ATIVO das maos, nao apenas deteccao/presenca
    gesticulation_pct = (
        round(frames_com_gesto_ativo / max(1, total_frames) * 100, 1) if total_frames > 0 else 0.0
    )
    hand_visible_pct = round(frames_com_mao_detectada / max(1, total_frames) * 100, 1)
    eye_contact_pct = round(contato_visual_frames / max(1, face_detected_count) * 100, 1)
    olhar_baixo_pct = round(olhar_baixo_frames / max(1, face_detected_count) * 100, 1)
    desvio_positivo_pct = round(desvio_positivo_frames / max(1, face_detected_count) * 100, 1)
    desvio_negativo_pct = round(desvio_negativo_frames / max(1, face_detected_count) * 100, 1)
    desvio_neutro_pct = round(desvio_neutro_frames / max(1, face_detected_count) * 100, 1)
    duas_maos_pct = round(duas_maos_count / max(1, frames_com_mao_detectada) * 100, 1)

    # Vocabulario de gestos (quantas posicoes diferentes usa)
    vocabulario_gestos = len(posicoes_grid_vistas)

    # Distribuicao do olhar (entropia — quao bem distribui entre direcoes)
    if direcoes_olhar:
        from collections import Counter

        contagem_direcoes = Counter(direcoes_olhar)
        total_direcoes = len(direcoes_olhar)
        probs = [c / total_direcoes for c in contagem_direcoes.values()]
        entropia_olhar = -sum(p * np.log2(p + 1e-10) for p in probs)
        max_entropia = np.log2(max(len(contagem_direcoes), 2))
        distribuicao_olhar = round(entropia_olhar / (max_entropia + 1e-10), 3)
    else:
        distribuicao_olhar = 0.0

    # Zona dos gestos
    total_gestos_zona = zona_alta_count + zona_media_count + zona_baixa_count
    zona_ideal_pct = round(
        (zona_alta_count + zona_media_count) / max(1, total_gestos_zona) * 100, 1
    )

    # Repeticao de gesto (ultimas 20 posicoes — muita repeticao = default)
    if len(ultimas_posicoes) >= 4:
        ultimas = ultimas_posicoes[-20:]
        unique_ratio = len(set(ultimas)) / len(ultimas)
        gesto_repetitivo = unique_ratio < 0.3  # menos de 30% unicas = repetitivo
    else:
        unique_ratio = 1.0
        gesto_repetitivo = False

    # =============================================
    # SCORE DE GESTUAL (0-100) — FORMULA MELHORADA
    # =============================================

    # 1. Contato visual com qualidade — peso 35%
    # Story 7.1 AC-3: bell curve com banda ideal 70-90%.
    # 100% contato continuo e penalizado como "staring" (~50).
    # 85% = 100 (zona ideal). 40% = ~57. 0% = 0.
    if 70 <= eye_contact_pct <= 90:
        contato_base = 100.0
    elif eye_contact_pct < 70:
        contato_base = max(0.0, (eye_contact_pct / 70.0) * 100)
    else:  # > 90
        contato_base = max(0.0, 100 - (eye_contact_pct - 90) * 5)
    # MP-1: penalizar só desvios negativos (evasivo). Positivos não penalizam.
    penalidade_desvio_negativo = min(30, desvio_negativo_pct * 0.8)
    contato_score = max(0, contato_base - penalidade_desvio_negativo)

    # 2. Gesticulacao com qualidade — peso 30%
    # Story 7.1 AC-4: bidirectional bell curve. Pouco gesto E excesso sao ruins.
    # Banda ideal: 40-70% do tempo gesticulando (calibrado em 2026-04 com video
    # de referencia — ajustar se feedback do user divergir).
    IDEAL_GESTURES_MIN = 40.0
    IDEAL_GESTURES_MAX = 70.0
    if IDEAL_GESTURES_MIN <= gesticulation_pct <= IDEAL_GESTURES_MAX:
        gesto_base = 100.0
        gesto_zona = "ideal"
    elif gesticulation_pct < IDEAL_GESTURES_MIN:
        # Pouca variacao: 0% → 0, 40% → 100, linear
        gesto_base = max(0.0, (gesticulation_pct / IDEAL_GESTURES_MIN) * 100)
        gesto_zona = "pouca_variacao"
    else:
        # Excesso: 70% → 100, 100% → ~50, linear decay
        gesto_base = max(0.0, 100 - (gesticulation_pct - IDEAL_GESTURES_MAX) * (50 / 30))
        gesto_zona = "excesso"

    # Bonus vocabulario (mais posicoes = mais expressivo)
    bonus_vocabulario = min(20, vocabulario_gestos * 3)
    # Penalidade repeticao
    penalidade_repeticao = 15 if gesto_repetitivo else 0
    gesticulacao_score = max(0, min(100, gesto_base + bonus_vocabulario - penalidade_repeticao))

    # 3. Duas maos — peso 15%
    #    Duas maos = mais impacto visual, mais expressividade
    duas_maos_score = min(100, duas_maos_pct * 1.5)

    # 4. Zona dos gestos — peso 10% (reduzido per mentor)
    #    Gestos acima da cintura = zona de poder
    zona_score = min(100, zona_ideal_pct * 1.1)

    # 5. Distribuicao do olhar — peso 10% (reduzido per mentor)
    #    Olhar bem distribuido = conecta com toda a audiencia
    #    Floor: contato visual alto com camera unica nao deve zerar distribuicao
    distribuicao_score = min(100, distribuicao_olhar * 100)
    if eye_contact_pct >= 80 and distribuicao_score < 50:
        distribuicao_score = 50

    gesture_score = round(
        contato_score * 0.35
        + gesticulacao_score * 0.30
        + duas_maos_score * 0.15
        + zona_score * 0.10
        + distribuicao_score * 0.10
    )
    gesture_score = max(0, min(100, gesture_score))

    # Confianca
    detection_rate = (
        (hand_detected_count + face_detected_count) / (total_frames * 2) if total_frames > 0 else 0
    )
    if detection_rate > 0.5:
        confidence = "high"
    elif detection_rate > 0.25:
        confidence = "medium"
    else:
        confidence = "low"

    elapsed = time.time() - start
    logger.info(
        "gesture_analysis_complete",
        score=gesture_score,
        gesticulation_pct=gesticulation_pct,
        eye_contact_pct=eye_contact_pct,
        vocabulario_gestos=vocabulario_gestos,
        duas_maos_pct=duas_maos_pct,
        duration_seconds=round(elapsed, 2),
    )

    return {
        "score": gesture_score,
        "confidence": confidence,
        "metrics": {
            "gesticulation_pct": gesticulation_pct,
            "hand_visible_pct": hand_visible_pct,
            "eye_contact_pct": eye_contact_pct,
            "olhar_baixo_pct": olhar_baixo_pct,
            "desvio_positivo_pct": desvio_positivo_pct,
            "desvio_negativo_pct": desvio_negativo_pct,
            "desvio_neutro_pct": desvio_neutro_pct,
            "duas_maos_pct": duas_maos_pct,
            "vocabulario_gestos": vocabulario_gestos,
            "zona_ideal_pct": zona_ideal_pct,
            "distribuicao_olhar": distribuicao_olhar,
            "gesto_repetitivo": gesto_repetitivo,
            "gesto_zona": gesto_zona,  # Story 7.1 AC-4: ideal | pouca_variacao | excesso
            "hand_detected_frames": hand_detected_count,
            "face_detected_frames": face_detected_count,
            "total_frames": total_frames,
            "sub_scores": {
                "contato_visual": round(contato_score),
                "gesticulacao": round(gesticulacao_score),
                "duas_maos": round(duas_maos_score),
                "zona": round(zona_score),
                "distribuicao_olhar": round(distribuicao_score),
            },
        },
    }


# Story 8.2 — Truth Contract
from workers._truth_contract_helpers import wrap_worker_result


def analyze_gestures_legacy(video_path: str) -> dict:
    """Legacy path (TRUTH_CONTRACT_ENABLED=false)."""
    return _compute_gesture_metrics(video_path)


def analyze_gestures(video_path: str) -> "WorkerResult":
    """Truth Contract path (TRUTH_CONTRACT_ENABLED=true)."""
    return wrap_worker_result("gesture", _compute_gesture_metrics, video_path)
