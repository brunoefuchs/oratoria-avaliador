"""Gerador de Plano de Coaching de 12 Semanas.

Principio: "Uma habilidade por semana. Grave, revise, ajuste.
Se mudou — otimo, passe para a proxima. Se nao mudou — repita."

O plano e personalizado com base no perfil do orador:
- Dimensoes mais fracas recebem mais semanas
- Exercicios sao especificos para cada deficiencia
- Progressao logica: fundamentos antes de refinamento
"""

import structlog

logger = structlog.get_logger()

# Banco de exercicios por dimensao e sub-habilidade
EXERCICIOS = {
    "velocidade_travada": {
        "titulo": "Marcador Verbal",
        "exercicio": "Leia um paragrafo em voz alta. Nos pontos mais importantes, reduza drasticamente a velocidade — como se estivesse grifando com a voz. Grave e compare o antes/depois.",
        "meta": "Conseguir identificar pelo menos 3 momentos de enfase com velocidade reduzida em 2 minutos de fala.",
    },
    "volume_travado": {
        "titulo": "Peaks and Troughs de Volume",
        "exercicio": "Conte uma historia simples. Nos momentos emocionais, REDUZA o volume ao inves de aumentar — o sussurro puxa a atencao. Pratique a transicao entre volume 7 e volume 2.",
        "meta": "Conseguir alternar entre pelo menos 3 niveis de volume numa narrativa de 2 minutos.",
    },
    "pitch_travado": {
        "titulo": "Melodia da Fala",
        "exercicio": "Faca 4 aulas de canto (nao para cantar bem, mas para expandir seu range vocal). Depois, leia um texto variando conscientemente entre tons altos e baixos.",
        "meta": "Range de pitch acima de 10 semitons na proxima avaliacao.",
    },
    "pausas_ausentes": {
        "titulo": "O Poder do Silencio",
        "exercicio": "Apos cada frase importante, conte mentalmente ate 2 antes de continuar. Grave 3 minutos e conte quantas pausas estrategicas voce fez.",
        "meta": "Pelo menos 2 pausas estrategicas por minuto sem que soem forcadas.",
    },
    "pausas_excessivas": {
        "titulo": "Fluidez sem Hesitacao",
        "exercicio": "Pratique falar sobre um tema por 2 minutos SEM pausar. Quando sentir vontade de hesitar, substitua o 'hum' por silencio completo. Grave e conte as hesitacoes.",
        "meta": "Reduzir hesitacoes para menos de 3 por minuto.",
    },
    "contato_visual": {
        "titulo": "Olhos que Conectam",
        "exercicio": "Em conversas do dia-a-dia, pratique manter contato visual por 3-5 segundos com cada pessoa antes de olhar para a proxima. Comece com ouvidos neutros (desconhecidos).",
        "meta": "Contato visual acima de 60% na proxima avaliacao.",
    },
    "olhar_baixo": {
        "titulo": "Cabeca Erguida",
        "exercicio": "Cole um post-it na altura dos olhos na parede. Pratique falar olhando para ele por 3 minutos. Se olhar para baixo, recomece a frase.",
        "meta": "Olhar para baixo em menos de 10% do tempo.",
    },
    "gestos_ausentes": {
        "titulo": "Vocabulario de Gestos",
        "exercicio": "Leia um livro infantil em voz alta, gesticulando CADA acao com as DUAS maos. Isso e exagerado de proposito — depois voce calibra para o contexto real.",
        "meta": "Gesticulacao visivel em pelo menos 40% do tempo de fala.",
    },
    "gestos_repetitivos": {
        "titulo": "Saia do Piloto Automatico",
        "exercicio": "Grave 2 minutos de fala. Assista sem som e conte quantas posicoes diferentes suas maos assumiram. Se foi menos que 5, pratique 3 posicoes novas no espelho.",
        "meta": "Vocabulario de pelo menos 6 posicoes diferentes.",
    },
    "duas_maos": {
        "titulo": "As Duas Maos Contam",
        "exercicio": "Coloque as duas maos na cintura. Toda vez que gesticular, use AMBAS as maos. Faca isso por 5 minutos todos os dias por uma semana.",
        "meta": "Usar duas maos em pelo menos 30% dos gestos.",
    },
    "postura_fechada": {
        "titulo": "Postura de Poder",
        "exercicio": "Antes de falar, fique 2 minutos em postura de poder (pes afastados na largura dos ombros, peito aberto, maos na cintura). Depois, mantenha essa abertura ao falar.",
        "meta": "Postura aberta em mais de 80% do tempo.",
    },
    "movimento_ansioso": {
        "titulo": "Plante os Pes",
        "exercicio": "Pratique falar com os pes firmemente no chao, largura dos ombros. Se precisar se mover, de 2-3 passos COM PROPOSITO e PARE. Nunca balance.",
        "meta": "Padrao de movimento classificado como 'plantado' ou 'proposital'.",
    },
    "rigidez": {
        "titulo": "Movimento com Intencao",
        "exercicio": "Divida seu espaco em 3 zonas. Pratique mover-se para uma nova zona a cada novo ponto que fizer. Pare, fale, mova-se, pare, fale.",
        "meta": "Pelo menos 3 deslocamentos propositais em 3 minutos de fala.",
    },
    "fillers_hesitacao": {
        "titulo": "Silencio ao Inves de Hum",
        "exercicio": "Grave 3 minutos de fala livre. Toda vez que ouvir 'eee', 'hum', 'aaa', anote. Na proxima gravacao, substitua cada hesitacao por um silencio limpo de 1 segundo.",
        "meta": "Menos de 3 hesitacoes por minuto.",
    },
    "fillers_muleta": {
        "titulo": "Consciencia das Muletas",
        "exercicio": "Peca para alguem contar suas muletas ('ne', 'tipo', 'entao') numa conversa de 5 minutos. So a consciencia ja reduz 30%. Depois, pratique pausar onde colocaria a muleta.",
        "meta": "Menos de 4 muletas por minuto.",
    },
    "arquetipo_lockin": {
        "titulo": "Troque o Canal",
        "exercicio": "Leia o MESMO paragrafo 4 vezes, cada vez num arquetipo diferente: 1) Professor calmo e autoritativo, 2) Treinador energico e direto, 3) Visionario inspirador, 4) Amigo contando uma historia. Grave todas.",
        "meta": "Usar pelo menos 3 arquetipos diferentes numa apresentacao de 5 minutos.",
    },
    "arquetipo_ausente": {
        "titulo": "Desbloqueie o Arquetipo {arquetipo}",
        "exercicio": "Assista 3 videos de referencia do arquetipo que esta faltando e imite o tom por 5 minutos. Nao precisa ser perfeito — precisa ser FAMILIAR.",
        "meta": "O arquetipo ausente aparecer em pelo menos 10% da proxima avaliacao.",
    },
}


def _selecionar_exercicios(aggregated: dict) -> list:
    """Seleciona exercicios relevantes baseado nas fraquezas detectadas."""
    dimension_scores = aggregated.get("dimension_scores", {})
    detailed = aggregated.get("detailed_metrics", {})
    exercicios_selecionados = []

    # Voz e variedade
    voice_metrics = detailed.get("voice", {})
    sub_scores_voz = voice_metrics.get("sub_scores", {})

    if sub_scores_voz.get("velocidade_score", 100) < 50:
        exercicios_selecionados.append(
            ("velocidade_travada", sub_scores_voz.get("velocidade_score", 0))
        )
    if sub_scores_voz.get("volume_score", 100) < 50:
        exercicios_selecionados.append(("volume_travado", sub_scores_voz.get("volume_score", 0)))
    if sub_scores_voz.get("pitch_score", 100) < 50:
        exercicios_selecionados.append(("pitch_travado", sub_scores_voz.get("pitch_score", 0)))
    if sub_scores_voz.get("pausa_score", 100) < 40:
        pausas = voice_metrics.get("pausas", {})
        if pausas.get("hesitacao_por_min", 0) > 4:
            exercicios_selecionados.append(
                ("pausas_excessivas", sub_scores_voz.get("pausa_score", 0))
            )
        else:
            exercicios_selecionados.append(
                ("pausas_ausentes", sub_scores_voz.get("pausa_score", 0))
            )

    # Gestual
    gesture_metrics = detailed.get("gesture", {})
    gesture_sub = gesture_metrics.get("sub_scores", {})

    if gesture_sub.get("contato_visual", 100) < 50:
        # Verificar se e olhar baixo ou falta de contato geral
        if gesture_metrics.get("olhar_baixo_pct", 0) > 20:
            exercicios_selecionados.append(("olhar_baixo", gesture_sub.get("contato_visual", 0)))
        else:
            exercicios_selecionados.append(("contato_visual", gesture_sub.get("contato_visual", 0)))

    if gesture_sub.get("gesticulacao", 100) < 50:
        if gesture_metrics.get("gesto_repetitivo", False):
            exercicios_selecionados.append(
                ("gestos_repetitivos", gesture_sub.get("gesticulacao", 0))
            )
        else:
            exercicios_selecionados.append(("gestos_ausentes", gesture_sub.get("gesticulacao", 0)))

    if gesture_sub.get("duas_maos", 100) < 40:
        exercicios_selecionados.append(("duas_maos", gesture_sub.get("duas_maos", 0)))

    # Postura
    posture_metrics = detailed.get("posture", {})
    posture_sub = posture_metrics.get("sub_scores", {})
    padrao = posture_metrics.get("padrao_movimento", "misto")

    if posture_sub.get("postura_aberta", 100) < 50:
        exercicios_selecionados.append(("postura_fechada", posture_sub.get("postura_aberta", 0)))
    if padrao == "ansioso":
        exercicios_selecionados.append(("movimento_ansioso", posture_sub.get("grounding", 0)))
    elif padrao == "rigido":
        exercicios_selecionados.append(("rigidez", posture_sub.get("movimento_proposital", 0)))

    # Fillers
    filler_metrics = detailed.get("fillers", {})
    por_categoria = filler_metrics.get("por_categoria", {})

    if por_categoria.get("hesitacao", 0) > 5:
        exercicios_selecionados.append(("fillers_hesitacao", dimension_scores.get("fillers", 0)))
    if (por_categoria.get("muleta_retorica", 0) + por_categoria.get("muleta_conexao", 0)) > 10:
        exercicios_selecionados.append(("fillers_muleta", dimension_scores.get("fillers", 0)))

    # Arquetipos
    arch_metrics = detailed.get("archetypes", {})
    if arch_metrics.get("lock_in", False):
        exercicios_selecionados.append(("arquetipo_lockin", dimension_scores.get("archetypes", 0)))
    ausentes = arch_metrics.get("ausentes", [])
    if ausentes:
        exercicios_selecionados.append(("arquetipo_ausente", dimension_scores.get("archetypes", 0)))

    # Ordenar por score (mais fraco primeiro = maior prioridade)
    exercicios_selecionados.sort(key=lambda x: x[1])

    return exercicios_selecionados


def generate_coaching_plan(aggregated: dict) -> list:
    """Gera plano de coaching de 12 semanas personalizado.

    Principio: uma habilidade por semana. Grave, revise, ajuste.
    As habilidades mais fracas vem primeiro.
    """
    logger.info("coaching_plan_generation_start")

    exercicios = _selecionar_exercicios(aggregated)

    if not exercicios:
        return [
            {
                "semana": "1-12",
                "foco": "Pratica de manutencao",
                "exercicio": "Continue gravando e revisando suas apresentacoes semanalmente. Mantenha a variedade em todas as dimensoes.",
                "meta": "Manter scores acima de 70 em todas as dimensoes.",
            }
        ]

    plano = []
    semana_atual = 1

    for i, (exercicio_key, score) in enumerate(exercicios):
        if semana_atual > 12:
            break

        exercicio_info = EXERCICIOS.get(exercicio_key, {})
        if not exercicio_info:
            continue

        # Dimensoes mais fracas recebem 2 semanas, outras 1
        semanas_dedicadas = 2 if score < 30 else 1

        semana_inicio = semana_atual
        semana_fim = min(12, semana_atual + semanas_dedicadas - 1)

        titulo = exercicio_info["titulo"]
        # Substituir placeholder de arquetipo se necessario
        if "{arquetipo}" in titulo:
            arch_metrics = aggregated.get("detailed_metrics", {}).get("archetypes", {})
            ausentes = arch_metrics.get("ausentes", ["motivador"])
            titulo = titulo.replace("{arquetipo}", ausentes[0] if ausentes else "motivador")

        exercicio_texto = exercicio_info["exercicio"]
        if "{arquetipo}" in exercicio_texto:
            arch_metrics = aggregated.get("detailed_metrics", {}).get("archetypes", {})
            ausentes = arch_metrics.get("ausentes", ["motivador"])
            exercicio_texto = exercicio_texto.replace(
                "{arquetipo}", ausentes[0] if ausentes else "motivador"
            )

        if semana_inicio == semana_fim:
            label_semana = f"{semana_inicio}"
        else:
            label_semana = f"{semana_inicio}-{semana_fim}"

        plano.append(
            {
                "semana": label_semana,
                "foco": titulo,
                "exercicio": exercicio_texto,
                "meta": exercicio_info["meta"],
            }
        )

        semana_atual = semana_fim + 1

    # Se sobrou espaco, preencher com pratica integrada
    if semana_atual <= 12:
        plano.append(
            {
                "semana": f"{semana_atual}-12",
                "foco": "Integracao e Pratica Completa",
                "exercicio": "Grave uma apresentacao de 5 minutos e revise com foco em TODAS as dimensoes trabalhadas. Uma dimensao por dia: segunda=voz, terca=gestual, quarta=postura, quinta=arquetipos, sexta=apresentacao completa.",
                "meta": "Conseguir manter todas as melhorias simultaneamente por 5 minutos sem perder naturalidade.",
            }
        )

    logger.info(
        "coaching_plan_generated",
        total_exercicios=len(plano),
        semanas_cobertas=min(12, semana_atual - 1),
    )

    return plano
