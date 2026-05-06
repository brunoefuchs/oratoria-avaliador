import time

import mediapipe as mp
import numpy as np
import structlog

from contracts import WorkerResult
from workers._truth_contract_helpers import wrap_worker_result
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
    """Estima direcao do olhar usando landmarks de IRIS (gaze real).

    2026-05-04: refator B. Antes media inclinacao da CABECA (offset nariz vs
    olhos), o que falhava em selfie (camera abaixo dos olhos faz cabeca
    inclinar levemente, marcando falsos "baixo"). Agora usa posicao das iris
    (landmarks 468 esq, 473 dir) RELATIVA aos cantos do olho — mede pra onde
    os OLHOS estao olhando, nao pra onde a cabeca aponta.

    Retorna:
        direcao: 'camera', 'baixo', 'esquerda', 'direita', 'cima'
        centrado: bool
        gaze_x: float (-1 esquerda, 0 centro, +1 direita)
        gaze_y: float (-1 cima, 0 centro, +1 baixo)
    """
    lm = face_landmarks

    # Iris centers (MediaPipe Face Landmarker — refine_landmarks=True dá 478)
    iris_esq = np.array([lm[468].x, lm[468].y])
    iris_dir = np.array([lm[473].x, lm[473].y])

    # Cantos do olho esquerdo (do speaker): 33 outer, 133 inner
    olho_esq_outer = np.array([lm[33].x, lm[33].y])
    olho_esq_inner = np.array([lm[133].x, lm[133].y])
    olho_esq_top = np.array([lm[159].x, lm[159].y])
    olho_esq_bottom = np.array([lm[145].x, lm[145].y])

    # Cantos do olho direito: 362 inner, 263 outer
    olho_dir_inner = np.array([lm[362].x, lm[362].y])
    olho_dir_outer = np.array([lm[263].x, lm[263].y])
    olho_dir_top = np.array([lm[386].x, lm[386].y])
    olho_dir_bottom = np.array([lm[374].x, lm[374].y])

    def _iris_relative(iris, outer, inner, top, bottom):
        """Retorna (x_rel, y_rel) onde iris está dentro do bounding box do olho.
        x_rel: -1 = encostado outer, +1 = encostado inner (ou vice-versa)
        y_rel: -1 = topo, +1 = baixo
        """
        eye_center = (outer + inner + top + bottom) / 4
        eye_width = float(np.linalg.norm(outer - inner))
        eye_height = float(np.linalg.norm(top - bottom))
        if eye_width < 1e-6 or eye_height < 1e-6:
            return 0.0, 0.0
        offset = iris - eye_center
        # Normaliza pra metade do tamanho (offset máximo razoável)
        x_rel = float(offset[0]) / (eye_width / 2)
        y_rel = float(offset[1]) / (eye_height / 2)
        return x_rel, y_rel

    # Olho esquerdo: outer < inner em X (no speaker, esquerda do rosto)
    le_x, le_y = _iris_relative(
        iris_esq, olho_esq_outer, olho_esq_inner, olho_esq_top, olho_esq_bottom
    )
    re_x, re_y = _iris_relative(
        iris_dir, olho_dir_outer, olho_dir_inner, olho_dir_top, olho_dir_bottom
    )

    # Media dos 2 olhos (gaze é binocular)
    gaze_x = (le_x + re_x) / 2
    gaze_y = (le_y + re_y) / 2

    # 2026-05-04: Thresholds ASSIMETRICOS pra acomodar selfie.
    # Em selfie tipica, speaker olha pra propria face no preview (acima do
    # lens). Iris fica deslocada PRA CIMA dentro do olho (gaze_y negativo).
    # Threshold simetrico penalizava esse padrao normal de selfie.
    # GAZE_Y_DOWN: olhar pra baixo (notas/chao) é problema real, threshold
    # apertado (0.30). GAZE_Y_UP: olhar pra cima (preview da camera) é
    # selfie normal, threshold permissivo (0.55).
    # 2026-05-06: GAZE_X 0.30 -> 0.20 apos auditoria (audit_gaze.py).
    # Em 7 videos amostrados, threshold 0.30 marcava como "camera" frames com
    # gaze_x 0.20-0.30 que visualmente eram olhar lateral subtle. 0.20 mantem
    # videos calibrados (mentor 97% -> 95%) e penaliza corretamente quem tem
    # olhar disperso (aluna 88% -> 73%). Calibrado contra video caa04928
    # validado visualmente em 4 timestamps (7.7s, 27.4s, 42.8s, 51.8s).
    GAZE_X_THRESHOLD = 0.20  # apertado pra capturar olhar lateral subtle
    GAZE_Y_DOWN_THRESHOLD = 0.30  # olhar pra baixo = problema
    GAZE_Y_UP_THRESHOLD = 0.55  # olhar pra cima = selfie OK

    centrado = (
        abs(gaze_x) < GAZE_X_THRESHOLD
        and -GAZE_Y_UP_THRESHOLD < gaze_y < GAZE_Y_DOWN_THRESHOLD
    )

    if centrado:
        direcao = "camera"
    elif gaze_y > GAZE_Y_DOWN_THRESHOLD:
        direcao = "baixo"
    elif gaze_y < -GAZE_Y_UP_THRESHOLD:
        direcao = "cima"
    elif gaze_x > GAZE_X_THRESHOLD:
        direcao = "direita"
    else:
        direcao = "esquerda"

    if centrado:
        tipo_desvio = "nenhum"
    elif direcao == "baixo":
        tipo_desvio = "negativo"
    elif direcao == "cima":
        tipo_desvio = "positivo"
    else:
        tipo_desvio = "neutro"

    # Angulo vertical da cabeca (mantido pra debug, NAO usado pra decisao)
    queixo = np.array([lm[152].x, lm[152].y])
    testa = np.array([lm[10].x, lm[10].y])
    vetor_face = testa - queixo
    angulo_vertical = float(np.degrees(np.arctan2(vetor_face[0], vetor_face[1])))

    return {
        "direcao": direcao,
        "centrado": centrado,
        "tipo_desvio": tipo_desvio,
        "angulo_vertical": round(angulo_vertical, 1),
        "gaze_x": round(gaze_x, 3),
        "gaze_y": round(gaze_y, 3),
        "offset_x": round(gaze_x, 3),  # alias pra compat com codigo legado
        "offset_y": round(gaze_y, 3),
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
    desvio_neutro_frames = 0  # MP-1: lateral (scanning)
    direcoes_olhar = []  # historico de direcoes para medir distribuicao

    # Gestos detalhados
    duas_maos_count = 0
    uma_mao_count = 0
    zona_alta_count = 0
    zona_media_count = 0
    zona_baixa_count = 0
    posicoes_grid_vistas = set()  # vocabulario de posicoes (legado)
    posicoes_grid_freq: dict = {}  # frequencia de cada posicao (entropia)
    posicoes_grid_sequencia: list = []  # sequencia temporal pra bigramas
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
                posicoes_grid_freq[info["posicao_grid"]] = (
                    posicoes_grid_freq.get(info["posicao_grid"], 0) + 1
                )
                posicoes_grid_sequencia.append(info["posicao_grid"])
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

    # 2026-05-04: Entropia da distribuicao por zona (DIVERSIDADE real, nao
    # apenas cobertura). Speaker que passa 70% numa zona tem cobertura alta
    # mas entropia baixa = repetitivo. Speaker bem distribuido = entropia
    # alta. Range: 0 (concentrado) → 1 (perfeitamente distribuido entre 9
    # zonas do grid 3x3). Score multiplica vocabulario base.
    if posicoes_grid_freq:
        total_freq = sum(posicoes_grid_freq.values())
        probs_zonas = [c / total_freq for c in posicoes_grid_freq.values()]
        entropia_zonas = -sum(p * np.log2(p + 1e-10) for p in probs_zonas)
        # Max entropia = log2(9) = 3.17 (9 zonas igualmente distribuidas)
        max_entropia_zonas = np.log2(9)
        diversidade_gestos = round(
            float(entropia_zonas / (max_entropia_zonas + 1e-10)), 3
        )
    else:
        diversidade_gestos = 0.0

    # 2026-05-04: Entropia de BIGRAMAS (pares consecutivos) — captura ciclos
    # repetitivos que diversidade_gestos perde. Speaker A-B-A-B-A-B tem
    # entropia_zonas alta (50/50) mas entropia_bigramas baixa (so 2 pares
    # unicos: AB,BA). Speaker A-B-C-D-A-B tem ambas altas. Detecta "maos
    # batendo" cíclico que iniciantes ansiosos fazem.
    if len(posicoes_grid_sequencia) >= 3:
        bigramas: dict = {}
        for i in range(len(posicoes_grid_sequencia) - 1):
            par = (posicoes_grid_sequencia[i], posicoes_grid_sequencia[i + 1])
            bigramas[par] = bigramas.get(par, 0) + 1
        total_bigramas = sum(bigramas.values())
        probs_bigramas = [c / total_bigramas for c in bigramas.values()]
        entropia_bigramas = -sum(p * np.log2(p + 1e-10) for p in probs_bigramas)
        # Max teorico: 9 zonas × 9 zonas = 81 bigramas distintos
        # Pratico: limitado pelo total observado (frames_total - 1)
        max_bigramas_pratico = min(81, total_bigramas)
        max_entropia_bigramas = (
            np.log2(max_bigramas_pratico) if max_bigramas_pratico > 1 else 1
        )
        diversidade_bigramas = round(
            float(entropia_bigramas / (max_entropia_bigramas + 1e-10)), 3
        )
    else:
        diversidade_bigramas = 0.0

    # Diversidade composta: gargalo do mais fraco entre zonas e bigramas.
    # Speaker oscilando A-B-A-B → zonas alta, bigramas baixa → score baixo.
    # Speaker variado → ambas altas → score alto.
    diversidade_composta = round(min(diversidade_gestos, diversidade_bigramas), 3)

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
    # 2026-05-04: threshold superior ampliado 90% → 100%. Em selfie/
    # talking-head (formato dominante), olhar pra camera o tempo todo é
    # ENGAJAMENTO, nao fixacao. Penalty de excesso fazia sentido pra palco
    # (varrer audiencia) mas inverte logica em redes sociais.
    if 70 <= eye_contact_pct <= 100:
        contato_base = 100.0
    else:  # < 70
        contato_base = max(0.0, (eye_contact_pct / 70.0) * 100)
    # MP-1: penalizar só desvios negativos (evasivo). Positivos não penalizam.
    penalidade_desvio_negativo = min(30, desvio_negativo_pct * 0.8)
    contato_score = max(0, contato_base - penalidade_desvio_negativo)

    # 2. Gesticulacao com qualidade — peso 30%
    # 2026-05-04: banda ideal AMPLIADA para 40-85% (era 40-70). Mentor TEDx
    # engajado fica naturalmente em 70-90%. Threshold antigo punia speaker
    # energético e premiava aluno discreto. Tier acima de 85% = "engajado-alto"
    # (90 baseline). Acima de 95% = exagerado (decay).
    IDEAL_GESTURES_MIN = 40.0
    IDEAL_GESTURES_MAX = 85.0
    HIGH_GESTURES_MAX = 95.0
    if IDEAL_GESTURES_MIN <= gesticulation_pct <= IDEAL_GESTURES_MAX:
        gesto_base = 100.0
        gesto_zona = "ideal"
    elif gesticulation_pct < IDEAL_GESTURES_MIN:
        # Pouca variacao: 0% → 0, 40% → 100, linear
        gesto_base = max(0.0, (gesticulation_pct / IDEAL_GESTURES_MIN) * 100)
        gesto_zona = "pouca_variacao"
    elif gesticulation_pct <= HIGH_GESTURES_MAX:
        # Engajado-alto: 85% → 100, 95% → 90, decay leve
        gesto_base = max(0.0, 100 - (gesticulation_pct - IDEAL_GESTURES_MAX) * 1.0)
        gesto_zona = "engajado_alto"
    else:
        # Exagerado: 95% → 90, 100% → 60, decay forte
        gesto_base = max(0.0, 90 - (gesticulation_pct - HIGH_GESTURES_MAX) * 6)
        gesto_zona = "excesso"

    # Bonus vocabulario AGORA via DIVERSIDADE COMPOSTA (zonas + bigramas).
    # Composta = min(zonas, bigramas) — gargalo do mais fraco.
    # Speaker A-B-A-B (cíclico): zonas altas, bigramas baixas → composta baixa.
    # Speaker A-B-C-D-E (variado): ambas altas → composta alta.
    bonus_vocabulario = round(diversidade_composta * 25)
    # Penalidade repeticao — PROPORCIONAL ao unique_ratio (validado 2026-04-18
    # via Gemini Vision). Binario -15 tratava igual borderline (0.30) e severo
    # (0.15). Gradiente reflete severidade real do lock-in gestual.
    if unique_ratio >= 0.30:
        penalidade_repeticao = 0
    elif unique_ratio >= 0.25:
        penalidade_repeticao = 10  # mild: 5-6 unique gestos em 20 frames
    elif unique_ratio >= 0.15:
        penalidade_repeticao = 20  # claro: 3-4 unique gestos
    else:
        penalidade_repeticao = 30  # severo: lock-in em 1-2 gestos
    gesticulacao_score = max(0, min(100, gesto_base + bonus_vocabulario - penalidade_repeticao))

    # 3. Duas maos — peso 15%
    #    Duas maos = mais impacto visual, mais expressividade
    duas_maos_score = min(100, duas_maos_pct * 1.5)

    # 4. Zona dos gestos — peso 10% (reduzido per mentor)
    #    Gestos acima da cintura = zona de poder
    zona_score = min(100, zona_ideal_pct * 1.1)

    # 5. Distribuicao do olhar — peso 10%
    # 2026-05-05: refatorado pra SELFIE/talking-head.
    # Antes: entropia simples (5 direcoes) — premiava distribuicao alta,
    # punia speaker que fica 95% camera (que e o IDEAL pra selfie).
    # Agora: BELL CURVE pelo eye_contact_pct.
    # 100% camera (robotico, sem piscar/variar) = 70
    # 85-95% (engajado natural com micro-variacao) = 100
    # 70-85% = 80
    # <70% = perdendo conexao, decay linear
    if eye_contact_pct >= 100:
        distribuicao_score = 70  # robotico — total absence of variacao natural
    elif eye_contact_pct >= 85:
        distribuicao_score = 100  # sweet spot natural
    elif eye_contact_pct >= 70:
        distribuicao_score = 80
    else:
        distribuicao_score = max(0, eye_contact_pct * (80 / 70))

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
            "diversidade_gestos": diversidade_gestos,
            "diversidade_bigramas": diversidade_bigramas,
            "diversidade_composta": diversidade_composta,
            "zona_ideal_pct": zona_ideal_pct,
            "distribuicao_olhar": distribuicao_olhar,
            "gesto_repetitivo": gesto_repetitivo,
            "unique_ratio": round(unique_ratio, 3),
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


def analyze_gestures_legacy(video_path: str) -> dict:
    """Legacy path (TRUTH_CONTRACT_ENABLED=false)."""
    return _compute_gesture_metrics(video_path)


def analyze_gestures(video_path: str) -> "WorkerResult":
    """Truth Contract path (TRUTH_CONTRACT_ENABLED=true)."""
    return wrap_worker_result("gesture", _compute_gesture_metrics, video_path)
