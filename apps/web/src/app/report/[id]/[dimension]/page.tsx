"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchDimensionDetail } from "@/lib/api-client";
import { AppShell } from "@/components/app-shell";
import { ZONA_LABELS } from "@/lib/report-labels";

const DIAGNOSTIC_LABELS: Record<string, string> = {
  // identity
  identidade_firme:
    "Identidade firme: você sustenta uma persona coerente e usa linguagem de autoridade. Quem assiste percebe consistência entre quem você diz ser e como fala.",
  identidade_fragil:
    "Identidade frágil: a persona oscila ao longo da fala. Em alguns trechos você soa autoridade; em outros, dúvida ou justificativa. Trabalhar essa coerência fortalece percepção.",
  identidade_bloqueada:
    "Identidade bloqueada: linguagem de vítima ou vícios emocionais dominam, e isso se sobrepõe ao conteúdo. É o que mais corrói credibilidade — prioridade #1 a destravar.",
  dados_insuficientes:
    "Dados insuficientes: o vídeo não teve marcadores de linguagem suficientes (frases de autoridade tipo \"eu acredito/defendo/tenho certeza\" ou de vítima tipo \"talvez/acho/não sei\") pra avaliar identidade comunicativa.",
  // storytelling
  narrativa_excepcional:
    "Narrativa excepcional: hook forte, encadeamento claro, bridge sentence presente e múltiplas famílias de gancho ativadas. Quem assiste para, escuta e quer mais.",
  narrativa_solida:
    "Narrativa sólida: estrutura consistente com começo, meio e fim. Tem hook reconhecível e algum gatilho emocional. Falta um pouco de costura entre ideias para virar excepcional.",
  narrativa_basica:
    "Narrativa básica: ideias presentes mas sem hook que fisgue ou bridge sentence que conecte. A audiência segue por educação; ainda não ficou agarrada.",
  narrativa_ausente:
    "Narrativa ausente: o conteúdo flutua sem estrutura clara. Sem hook, sem clímax, sem fechamento. A primeira coisa a construir é uma abertura que pare quem assiste.",
  // facial
  expressao_equilibrada:
    "Expressão equilibrada: rosto vivo na medida certa, com microexpressões que pontuam o conteúdo sem distrair.",
  rosto_estatico:
    "Rosto estático: pouca expressão facial detectada. A audiência pode interpretar como distância ou ensaio mecânico — micro-elevações de sobrancelha e variações de sorriso já desbloqueiam.",
  expressao_travada:
    "Expressão travada: o rosto ficou preso num único registro emocional. Variar entre serenidade, ênfase e leveza faz diferença grande.",
  expressao_monotona:
    "Expressão monótona: pouca oscilação facial — combina com voz plana se aparecer também. Trabalhar facial e voz juntos costuma destravar.",
  expressao_exagerada:
    "Expressão exagerada: muita expressão pode roubar atenção do conteúdo. Reserve os movimentos mais marcantes para os pontos-chave.",
  muito_expressivo:
    "Muito expressivo: rosto trabalha bastante, sinal de engajamento e energia. Mantenha o nível; reserve os movimentos mais marcantes para os pontos-chave.",
};

const DIMENSION_INTRO: Record<string, string> = {
  storytelling:
    "Storytelling é a estrutura narrativa do que você fala — como você prende atenção desde a abertura, costura ideias com bridge sentences (frases-ponte) e ativa emoção (curiosidade, empatia, urgência, autoridade). Avaliamos hook de abertura, encadeamento lógico, presença de bridge, ativação de chemicals (gatilhos emocionais) e diversidade de famílias de hooks (24 padrões reconhecidos).",
  tonality:
    "Tonalidade mede a carga emocional da sua voz: o quanto ela transmite confiança, calor, energia ou tensão. Cruza valência (positivo↔negativo) com arousal (calmo↔intenso) ao longo da fala — comunicador notável passeia entre texturas (ex: confiante, caloroso, inspirado) em vez de travar numa só.",
  archetypes:
    "Arquétipos vocais são 4 modos de falar: Coach (diretivo), Educador (estruturado), Motivador (aspiracional) e Amigo (caloroso). Avaliamos a alternância entre eles — ficar travado num só é não-funcional; bom comunicador cicla 2-5 trocas/min usando os 4 com diferentes pesos.",
  identity:
    "Identidade comunicativa mede a coerência da sua persona ao longo do vídeo: linguagem de autoridade vs vítima, vícios emocionais, e se a forma de falar bate com o que você diz querer transmitir.",
};

const DIMENSION_LABELS: Record<string, string> = {
  variety: "Variedade Vocal",
  voice: "Voz e Dicção",
  gesture: "Presença Visual",
  posture: "Postura e Presença",
  fillers: "Clareza Verbal",
  archetypes: "Arquétipos Vocais",
  facial: "Expressão Facial",
  storytelling: "Storytelling",
  tonality: "Tonalidade",
  identity: "Identidade",
  articulation: "Articulação",
};

const DIMENSION_ICONS: Record<string, string> = {
  posture: "accessibility",
  gesture: "visibility",
  voice: "mic",
  fillers: "chat_bubble",
  variety: "graphic_eq",
  archetypes: "theater_comedy",
  storytelling: "auto_stories",
  tonality: "tune",
  identity: "fingerprint",
  facial: "sentiment_satisfied",
  articulation: "record_voice_over",
};

const METRIC_LABELS: Record<
  string,
  Record<string, { label: string; reference?: string; description?: string }>
> = {
  voice: {
    wpm: {
      label: "Palavras por minuto",
      reference: "Ideal: 130-170",
      description: "Sua cadência de fala. Acima de 180 cansa o ouvinte; abaixo de 120 perde atenção.",
    },
    pitch_mean_hz: {
      label: "Tom base da voz",
      description: "Sua frequência fundamental média — o tom em que sua voz se assenta naturalmente. Não é bom nem ruim, é seu ponto de partida pra modular.",
    },
    pitch_range_semitones: {
      label: "Variação de tom (semitons)",
      reference: "10+ = expressivo",
      description: "Distância do seu tom mais grave ao mais agudo. Range maior = mais repertório vocal em uso.",
    },
    monotonia_score: {
      label: "Variação Global da Voz",
      reference: "70+ = boa amplitude geral",
      description: "Visão estatística do vídeo inteiro: o quanto seu tom, volume e velocidade variaram em média ao longo da fala. É complementar à Variedade Vocal — enquanto esta detecta trechos específicos planos, esta mostra a amplitude geral de variação.",
    },
    pitch_accent_per_minute: {
      label: "Ênfases vocais por minuto",
      reference: "Comunicadores notáveis: 50-80/min",
      description: "Quantas vezes você ENFATIZA uma palavra ao falar (sobe ou desce o tom de forma marcada). É como sublinhar palavras-chave com a voz — cada ênfase puxa a atenção do ouvinte de volta.",
    },
    pitch_accent_mean_prominence_st: {
      label: "Intensidade média das ênfases",
      reference: "10+ semitons = ênfase dramática",
      description: "Quão FORTE é cada ênfase em média. Sublinhar levemente vs sublinhar com marcador grosso. Distingue modulação intencional de tremor inseguro.",
    },
    pitch_accent_strong_per_minute: {
      label: "Ênfases fortes por minuto",
      reference: "≥8 semitons de proeminência",
      description: "Saltos melódicos significativos. Mentores notáveis de comunicação têm 25-35/min.",
    },
  },
  fillers: {
    fillers_per_minute: {
      label: "Vícios de linguagem por minuto",
      reference: "Meta: < 3/min",
      description: "Quantas vezes 'né', 'tipo', 'sabe', 'então' aparecem por minuto. Substitua por pausas.",
    },
    hesitacoes_per_minute: {
      label: "Hesitações por minuto",
      reference: "< 2/min ideal",
      description: "Frequência de 'ahn', 'eh', 'hum'. Mostra busca de palavra. Pausa silenciosa lê melhor.",
    },
    total_fillers: {
      label: "Total de vícios de linguagem",
      description: "Contagem absoluta no vídeo todo.",
    },
    total_clusters: {
      label: "Problemas de fluência",
      reference: "0 = ideal",
      description: "Trechos com múltiplos vícios em sequência. Sinaliza ansiedade ou falta de preparo.",
    },
    type_token_ratio: {
      label: "Riqueza de vocabulário",
      reference: "0.5+ = bom vocabulário",
      description: "Razão entre palavras únicas e total. Quanto maior, mais variado seu repertório.",
    },
  },
  posture: {
    alignment_score: {
      label: "Alinhamento postural (0-100)",
      description: "Coluna ereta, ombros alinhados. Postura forte = autoridade percebida.",
    },
    open_posture_pct: {
      label: "% postura aberta",
      description: "Tempo com peito aberto vs braços cruzados/fechado. Aberto convida conexão.",
    },
    ombros_nivelados_pct: {
      label: "% ombros nivelados",
      description: "Estabilidade lateral. Ombros tortos sinalizam tensão ou desbalanceio.",
    },
    grounding_score: {
      label: "Estabilidade corporal (0-100)",
      reference: "Base firme = força",
      description: "Pés firmes no chão, sem balanço lateral. Base sólida = presença sólida.",
    },
    proposital_score: {
      label: "Movimento proposital (0-100)",
      description: "Cada movimento tem intenção (não é tique nervoso). Ocupe espaço com propósito, não com agitação.",
    },
    padrao_movimento: {
      label: "Padrão de movimento",
      description: "Categoria detectada: estático, oscilante, intencional, etc.",
    },
  },
  gesture: {
    eye_contact_pct: {
      label: "% contato visual",
      reference: "80%+ é ótimo",
      description: "Quanto do tempo você olhou direto pra câmera. Quanto mais alto, mais conexão — falar pra câmera é falar olho no olho com quem te assiste.",
    },
    olhar_baixo_pct: {
      label: "% olhar para baixo",
      reference: "< 10% ideal",
      description: "Olhar pra notas/chão diminui conexão. Ensaie até dispensar slides.",
    },
    gesticulation_pct: {
      label: "% tempo gesticulando",
      reference: "Zona ideal: 40-85%",
      description: "Mãos visíveis e ativas. Comunicadores engajados ficam naturalmente em 70-90%. Acima de 95% pode distrair.",
    },
    gesto_zona: {
      label: "Zona de gesticulação",
      description: "Faixa vertical onde os gestos acontecem. Peitoral é a zona de poder.",
    },
    duas_maos_pct: {
      label: "% gestos com duas mãos",
      reference: "30%+ = mais expressivo",
      description: "Duas mãos amplificam ideias grandes. Uma mão sozinha limita o palco.",
    },
    vocabulario_gestos: {
      label: "Vocabulário de gestos",
      reference: "6+ posições = variado",
      description: "Quantas regiões diferentes você ocupa. Mais posições = mais 'paleta' visual.",
    },
    distribuicao_olhar: {
      label: "Variação natural do olhar",
      reference: "Ideal: 0.10-0.30",
      description: "Micro-variações naturais do olhar enquanto fala. Pouca variação = engajado e focado na câmera. Muita variação = olhar disperso, perdendo conexão.",
    },
  },
  variety: {
    diagnostico_geral: {
      label: "Diagnóstico geral",
      description: "Resumo qualitativo da sua variação prosódica.",
    },
    pct_tempo_monotono: {
      label: "% tempo monótono",
      reference: "< 20% ideal",
      description: "Tempo em que volume, tom ou velocidade ficaram estáveis demais. Cérebro do ouvinte desliga no automático.",
    },
    cv_velocidade: {
      label: "Variação de velocidade",
      reference: "0.05-0.30 = ideal",
      description: "Quanto sua cadência muda ao longo da fala. Sempre que algo se torna padrão, deixa de funcionar — variação controlada é fundamental para reter atenção.",
    },
    cv_volume: {
      label: "Variação de volume",
      reference: "0.05-0.20 = ideal",
      description: "Quanto seu volume modula ao longo do tempo. Sussurros e projeções alternados criam altos e baixos que prendem atenção.",
    },
    cv_pitch: {
      label: "Variação de entonação",
      reference: "0.05-0.20 = ideal",
      description: "Quanto seu tom oscila ao longo da fala. Pouca oscilação = monotonia melódica; oscilação saudável carrega emoção.",
    },
    intensity_mean_db: {
      label: "Volume médio (dB)",
      description: "Intensidade média ao longo da fala. Comunicadores notáveis ficam em 60-70 dB com picos pra modular ênfase.",
    },
  },
  facial: {
    feedback: {
      label: "Feedback do sistema",
    },
    diagnostico: {
      label: "Diagnóstico",
    },
    detection_pct: {
      label: "% rosto detectado",
      reference: "90+ = bom enquadramento",
      description: "Quanto do tempo o rosto está visível e analisável.",
    },
    smile_variability: {
      label: "Variabilidade do sorriso",
      reference: ">0.05 = expressivo",
      description: "Quanto seu sorriso muda de intensidade. Sorriso estático = inautêntico.",
    },
    smile_frequency_percent: {
      label: "% tempo sorrindo",
      reference: "30-60% = caloroso natural",
      description: "Quanto do tempo aparece um sorriso. Calor humano sem cair em sorriso forçado.",
    },
    eye_openness_stddev: {
      label: "Variação abertura dos olhos",
      reference: ">0.03 = expressivo",
      description: "Olhos arregalando vs apertando. Captura surpresa, foco, ênfase emocional.",
    },
    brow_raises_per_minute: {
      label: "Sobrancelhas (movimentos claros) /min",
      reference: "1-5/min = expressivo",
      description: "Movimentos marcantes de sobrancelha — surpresa, ênfase, dúvida.",
    },
    brow_subtle_per_minute: {
      label: "Sobrancelhas (sutis) /min",
      reference: "complementa os claros",
      description: "Microelevações que captam expressões discretas.",
    },
    brow_combined_per_minute: {
      label: "Sobrancelhas combinadas /min",
      reference: "2-7/min = sobrancelha trabalhando",
      description: "Soma ponderada de movimentos de sobrancelha (claros pesam 1.0, sutis 0.5). Quanto mais alto, mais sua sobrancelha enfatiza emoção e ritmo no rosto.",
    },
  },
  tonality: {
    diagnostico: {
      label: "Diagnóstico de tonalidade",
      description: "Classificação emocional via VAD — modelo que mede 3 eixos: Valence (positivo↔negativo), Arousal (calmo↔intenso) e Dominance (submisso↔autoritativo). Cruzando os 3, identificamos a textura emocional dominante da sua voz.",
    },
    textura_dominante: {
      label: "Textura dominante",
      description: "Padrão emocional mais frequente na fala (alegre, neutro, tenso, etc).",
    },
    n_texturas_usadas: {
      label: "Texturas distintas usadas",
      reference: "3+ = variação",
      description: "Quantas categorias emocionais aparecem ao longo do vídeo.",
    },
  },
  archetypes: {
    arquetipo_dominante: {
      label: "Arquétipo dominante",
      description: "Coach (diretivo), Educador (estruturado), Motivador (aspiracional) ou Amigo (caloroso).",
    },
    pct_dominante: {
      label: "% no arquétipo dominante",
      reference: "< 50% = equilibrado",
      description: "Acima de 50% começa a travar. Acima de 70% = audiência percebe. Acima de 80% = audiência adormece. Cycling cria contraste e mantém atenção.",
    },
    num_arquetipos_usados: {
      label: "Arquétipos usados",
      reference: "4 = ideal",
      description: "Quantos dos 4 arquétipos apareceram. Faltar um = faltar uma cor.",
    },
    trocas_por_minuto: {
      label: "Trocas por minuto",
      reference: "2-5 = ideal",
      description: "Frequência de mudança entre arquétipos. Pouca = monotonia. Muita = caos.",
    },
    lock_in: {
      label: "Lock-in detectado (>70%)",
      reference: "false = bom",
      description: "Quando ≥70% da fala fica num único arquétipo — audiência percebe como personagem único. Default = não-funcional.",
    },
    lock_in_critico: {
      label: "Lock-in crítico (≥80%)",
      reference: "false = bom",
      description: "≥80% num único arquétipo — adormece a audiência. Prioridade máxima de cycling.",
    },
  },
  storytelling: {
    diagnostico: {
      label: "Diagnóstico narrativo",
    },
  },
  identity: {
    diagnostico: {
      label: "Diagnóstico de identidade",
    },
  },
  opening: {
    type: {
      label: "Tipo de abertura",
      description: "Categoria de hook detectada (pergunta, dado, vulnerabilidade, etc).",
    },
    strength: {
      label: "Força do hook",
      description: "Avaliação qualitativa: weak, moderate, strong.",
    },
  },
  congruence: {
    diagnostico: {
      label: "Congruência verbal-vocal-visual",
      description: "Quão alinhado está o que você diz com tom de voz e linguagem corporal.",
    },
  },
};

const SUB_SCORE_LABELS: Record<string, string> = {
  wpm_score: "Palavras por Minuto",
  wpm: "Palavras por Minuto",
  pausa_score: "Pausa",
  pausa: "Pausa",
  pitch_score: "Variação de Tom",
  pitch: "Variação de Tom",
  volume_score: "Variação de Volume",
  volume: "Variação de Volume",
  velocidade_score: "Variação de Velocidade",
  velocidade: "Variação de Velocidade",
  variacao_volume: "Variação de Volume",
  variacao_entonacao: "Variação de Entonação",
  variacao_velocidade: "Variação de Velocidade",
  grounding: "Estabilidade Corporal",
  alinhamento: "Alinhamento",
  postura_aberta: "Postura Aberta",
  movimento_proposital: "Movimento Proposital",
  dinamismo: "Dinamismo",
  // ombros_relaxados removido do UI ate calibracao studio-grade
  zona: "Zona",
  duas_maos: "Duas Mãos",
  gesticulacao: "Gesticulação",
  contato_visual: "Contato Visual",
  distribuicao_olhar: "Distribuição do Olhar",
  cycling: "Alternância",
  anti_lockin: "Anti Lock-in",
  diversidade: "Diversidade",
};

const SUB_SCORE_DESC: Record<string, string> = {
  wpm_score: "Cadência ideal: 130-170 palavras/min. Acima cansa, abaixo perde.",
  wpm: "Cadência ideal: 130-170 palavras/min. Acima cansa, abaixo perde.",
  pausa_score: "Pausas estratégicas (pré conteúdo) puxam atenção; hesitação dispersa.",
  pausa: "Pausas estratégicas (pré conteúdo) puxam atenção; hesitação dispersa.",
  pitch_score: "Range total entre seu tom mais grave e mais agudo. 15+ semitons = nível de comunicador notável.",
  pitch: "Range total entre seu tom mais grave e mais agudo. 15+ semitons = nível de comunicador notável.",
  volume_score: "Quanto seu volume modula ao longo da fala. Variar = altos e baixos que prendem atenção.",
  volume: "Quanto seu volume modula ao longo da fala. Variar = altos e baixos que prendem atenção.",
  velocidade_score: "Quanto sua cadência muda. Não é só rápido vs devagar — é o ritmo mudar.",
  velocidade: "Quanto sua cadência muda. Não é só rápido vs devagar — é o ritmo mudar.",
  variacao_volume: "Quanto seu volume modula ao longo da fala. Variar = altos e baixos que prendem atenção.",
  variacao_entonacao: "Quanto seu tom oscila ao longo da fala. Pouca oscilação = monotonia melódica; oscilação saudável carrega emoção.",
  variacao_velocidade: "Quanto sua cadência muda. Não é só rápido vs devagar — é o ritmo mudar.",
  grounding: "Pés firmes, corpo estável. Base solida = presença sólida.",
  alinhamento: "Coluna ereta, ombros alinhados. Postura forte vende autoridade.",
  postura_aberta: "Peito aberto vs fechado. Aberto convida conexão.",
  movimento_proposital: "Cada movimento com intenção, não tique nervoso.",
  dinamismo: "Quanto você se movimenta no espaço. Em vídeo pra câmera, neutro é o esperado — câmera fixa não pede deslocamento.",
  ombros_relaxados: "Distância orelha→ombro. Ombros encolhidos = tensão = ansiedade percebida.",
  zona: "Faixa vertical onde gesticula. Peitoral é zona de poder.",
  duas_maos: "Gesticular com 2 mãos amplifica ideias grandes.",
  gesticulacao: "Tempo com mãos visíveis e ativas. Mãos paradas = energia parada.",
  contato_visual: "Tempo olhando pra câmera. Audiência precisa sentir presença.",
  distribuicao_olhar: "Quão equilibradamente você varre o enquadramento.",
  cycling: "Frequência de troca entre os 4 arquétipos.",
  anti_lockin: "Você não trava num único arquétipo. Default = não-funcional.",
  diversidade: "Quantos dos 4 arquétipos você usou no vídeo.",
};

const ARCHETYPE_LABELS: Record<string, string> = {
  educador: "Educador",
  coach: "Coach",
  motivador: "Motivador",
  amigo: "Amigo",
};

function getScoreTone(score: number) {
  if (score >= 70)
    return { text: "text-secondary", bar: "bg-secondary" };
  if (score >= 40)
    return { text: "text-tertiary", bar: "bg-tertiary" };
  return { text: "text-error", bar: "bg-error" };
}

export default function DimensionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const dimension = params.dimension as string;
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const main = await fetchDimensionDetail(id, dimension);
        if (dimension === "variety") {
          try {
            const voiceData = await fetchDimensionDetail(id, "voice");
            const vm = voiceData?.metrics || {};
            main.metrics = {
              ...main.metrics,
              cv_velocidade: vm.cv_velocidade,
              cv_volume: vm.cv_volume,
              cv_pitch: vm.cv_pitch,
              intensity_mean_db: vm.intensity_mean_db,
            };
          } catch {}
        }
        setData(main);
      } catch {
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id, dimension]);

  // Articulation está em pesquisa — métrica espectral não confiável em
  // áudio mobile (codec AAC corta 4-8kHz, AGC suprime consoantes). Backend
  // continua coletando, mas frontend não expõe pra evitar diagnóstico falso.
  if (dimension === "articulation") {
    return (
      <AppShell maxWidth="lg" showBack backHref={`/report/${id}`} backLabel="Voltar ao relatório">
        <div className="min-h-[40vh] flex flex-col items-center justify-center text-center space-y-3 px-6">
          <span className="material-symbols-outlined text-5xl text-on-surface-variant">science</span>
          <h2 className="font-headline text-xl font-bold">Articulação — em pesquisa</h2>
          <p className="text-sm text-on-surface-variant max-w-md leading-relaxed">
            A medição espectral de articulação ainda não é confiável em áudio
            de smartphone (codec corta a banda das consoantes em 4-8kHz). Estamos
            coletando dados para liberar essa dimensão quando tivermos calibração
            studio-grade.
          </p>
        </div>
      </AppShell>
    );
  }

  if (loading) {
    return (
      <AppShell maxWidth="lg" showBack backHref={`/report/${id}`}>
        <div className="min-h-[50vh] flex items-center justify-center">
          <p className="text-on-surface-variant text-sm">Carregando...</p>
        </div>
      </AppShell>
    );
  }

  if (!data) {
    return (
      <AppShell maxWidth="lg" showBack backHref={`/report/${id}`}>
        <div className="min-h-[40vh] flex items-center justify-center">
          <p className="text-error">Dimensão não encontrada</p>
        </div>
      </AppShell>
    );
  }

  const tone = getScoreTone(data.score);
  const metricDefs = METRIC_LABELS[dimension] || {};
  const feedback = data.feedback || {};
  const metrics = data.metrics || {};
  const icon = DIMENSION_ICONS[dimension] || "analytics";

  return (
    <AppShell maxWidth="lg" showBack backHref={`/report/${id}`} backLabel="Relatório">
      <div className="space-y-8">
        {/* Hero */}
        <section className="rounded-3xl bg-surface-container-low p-6 md:p-8 stage-ambient relative overflow-hidden">
          <div className="flex items-start justify-between gap-6">
            <div>
              <span
                className={`material-symbols-outlined text-3xl mb-3 block ${tone.text}`}
              >
                {icon}
              </span>
              <span className="font-label text-xs uppercase tracking-[0.3em] text-on-surface-variant">
                Dimensão
              </span>
              <h1 className="font-headline text-2xl md:text-4xl font-extrabold tracking-tight mt-1">
                {DIMENSION_LABELS[dimension] || dimension}
              </h1>
              {(feedback.label || feedback.score_label) && (
                <p className="mt-3 text-sm text-on-surface-variant">
                  {feedback.label || feedback.score_label}
                </p>
              )}
            </div>
            <div className="shrink-0 flex items-baseline gap-1">
              <span
                className={`font-headline text-5xl md:text-7xl font-extrabold ${tone.text}`}
              >
                {data.score}
              </span>
              <span className="text-on-surface-variant">/100</span>
            </div>
          </div>
          <div className="absolute bottom-0 left-0 right-0 fluency-wave opacity-50" />
        </section>

        {data.confidence === "low" && (
          <div className="rounded-2xl bg-tertiary/10 p-4 text-sm text-tertiary ghost-border flex items-start gap-3">
            <span className="material-symbols-outlined">info</span>
            <span>
              Confiança baixa — qualidade do vídeo pode ter afetado a análise.
            </span>
          </div>
        )}

        {(metrics as Record<string, unknown>).audio_quality_low === true && (
          <div className="rounded-2xl bg-tertiary/10 p-4 text-sm ghost-border flex items-start gap-3 border border-tertiary/30">
            <span className="material-symbols-outlined text-tertiary mt-0.5">graphic_eq</span>
            <div className="text-on-surface-variant leading-relaxed">
              <p className="font-medium text-on-surface mb-1">
                Áudio com ruído elevado
              </p>
              <p>
                Detectamos baixa relação sinal/ruído neste vídeo (SNR ~{String((metrics as Record<string, unknown>).snr_estimated_db ?? "?")} dB).
                Ruído de fundo pode distorcer a medição de variação vocal — pulamos a detecção de monotonia pra evitar falso positivo.
                Em ambiente mais silencioso, a análise fica mais precisa.
              </p>
            </div>
          </div>
        )}

        {(metrics as Record<string, unknown>).babble_suspected === true && (
          <div className="rounded-2xl bg-tertiary/10 p-4 text-sm ghost-border flex items-start gap-3 border border-tertiary/30">
            <span className="material-symbols-outlined text-tertiary mt-0.5">groups</span>
            <div className="text-on-surface-variant leading-relaxed">
              <p className="font-medium text-on-surface mb-1">
                Vozes de fundo detectadas
              </p>
              <p>
                Identificamos sinais de outras pessoas falando ao fundo (ex: ambiente público, café, saguão).
                Isolamos sua voz por proximidade ao microfone, mas a análise pode ter precisão reduzida.
                Pra avaliação mais precisa, prefira gravar em ambiente silencioso.
              </p>
            </div>
          </div>
        )}

        {DIMENSION_INTRO[dimension] && (
          <section className="rounded-2xl bg-surface-container-low p-5 ghost-border">
            <h3 className="font-label text-xs uppercase tracking-[0.3em] text-secondary mb-2">
              O que é e como avaliamos
            </h3>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              {DIMENSION_INTRO[dimension]}
            </p>
          </section>
        )}

        {/* Cards destacados (feedback, diagnóstico) — texto longo precisa espaço */}
        {(["feedback", "diagnostico"] as const).map((key) => {
          const def = metricDefs[key];
          const value = (metrics as Record<string, unknown>)[key];
          if (!def || value === undefined || value === null || value === "") return null;
          const rawValue = String(value);
          const friendly =
            key === "diagnostico" && DIAGNOSTIC_LABELS[rawValue]
              ? DIAGNOSTIC_LABELS[rawValue]
              : rawValue.replace(/_/g, " ");
          return (
            <section
              key={key}
              className="rounded-2xl bg-surface-container-low p-5 ghost-border space-y-2"
            >
              <h3 className="font-label text-xs uppercase tracking-[0.3em] text-secondary">
                {def.label}
              </h3>
              <p className="text-sm text-on-surface leading-relaxed break-words first-letter:uppercase">
                {friendly}
              </p>
              {def.description && (
                <p className="text-xs text-on-surface-variant leading-snug">
                  {def.description}
                </p>
              )}
            </section>
          );
        })}

        {/* Métricas */}
        {Object.entries(metricDefs).some(
          ([k]) =>
            k !== "feedback" &&
            k !== "diagnostico" &&
            (metrics as Record<string, unknown>)[k] !== undefined &&
            (metrics as Record<string, unknown>)[k] !== null
        ) && (
          <section className="space-y-3">
            <h2 className="font-label text-xs uppercase tracking-[0.3em] text-secondary">
              Métricas
            </h2>
            <div className="grid md:grid-cols-2 gap-3">
              {Object.entries(metricDefs).map(([key, def]) => {
                if (key === "feedback" || key === "diagnostico") return null;
                const value = (metrics as Record<string, unknown>)[key];
                if (value === undefined || value === null) return null;

                let displayValue: string;
                if (typeof value === "boolean") {
                  displayValue = value ? "Sim" : "Não";
                } else if (typeof value === "number") {
                  displayValue = String(Math.round(value * 100) / 100);
                } else {
                  // Story 7.1 AC-4 fix QA — traduzir gesto_zona via ZONA_LABELS
                  if (key === "gesto_zona" && typeof value === "string") {
                    displayValue =
                      ZONA_LABELS[value as keyof typeof ZONA_LABELS] ?? String(value);
                  } else {
                    displayValue = String(value);
                  }
                }

                return (
                  <div
                    key={key}
                    className="flex items-center justify-between rounded-xl bg-surface-container-low p-4 ghost-border gap-4"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-on-surface">
                        {def.label}
                      </p>
                      {def.reference && (
                        <p className="text-xs text-secondary/80 mt-0.5">
                          {def.reference}
                        </p>
                      )}
                      {def.description && (
                        <p className="text-[11px] text-on-surface-variant/80 mt-1.5 leading-snug">
                          {def.description}
                        </p>
                      )}
                    </div>
                    <span className="font-headline text-lg font-bold text-secondary shrink-0">
                      {displayValue}
                    </span>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Sub-scores */}
        {metrics.sub_scores && (
          <section className="space-y-3">
            <h2 className="font-label text-xs uppercase tracking-[0.3em] text-secondary">
              Pontuações
            </h2>
            <div className="rounded-2xl bg-surface-container-low p-5 ghost-border space-y-3">
              {Object.entries(
                metrics.sub_scores as Record<string, number>
              ).map(([key, value]) => {
                const subTone = getScoreTone(value);
                return (
                  <div key={key} className="space-y-1.5">
                    <div className="flex justify-between text-sm">
                      <span className="text-on-surface">
                        {SUB_SCORE_LABELS[key] || key.replace(/_/g, " ")}
                      </span>
                      <span className={`font-mono font-bold ${subTone.text}`}>
                        {value}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-surface-container-highest overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${subTone.bar}`}
                        style={{ width: `${Math.min(100, value)}%` }}
                      />
                    </div>
                    {SUB_SCORE_DESC[key] && (
                      <p className="text-[11px] text-on-surface-variant/80 leading-snug pt-0.5">
                        {SUB_SCORE_DESC[key]}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Distribuição de arquétipos */}
        {dimension === "archetypes" && metrics.distribuicao && (
          <section className="space-y-3">
            <h2 className="font-label text-xs uppercase tracking-[0.3em] text-secondary">
              Distribuição de Arquétipos
            </h2>
            <div className="rounded-2xl bg-surface-container-low p-5 ghost-border space-y-3">
              {Object.entries(metrics.distribuicao as Record<string, number>)
                .sort(([, a], [, b]) => b - a)
                .map(([arq, pct]) => (
                  <div key={arq} className="space-y-1.5">
                    <div className="flex justify-between text-sm">
                      <span className="text-on-surface">
                        {ARCHETYPE_LABELS[arq] || arq}
                      </span>
                      <span className="font-mono font-bold text-secondary">
                        {pct}%
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-surface-container-highest overflow-hidden">
                      <div
                        className="h-full rounded-full bg-ai-pulse transition-all"
                        style={{ width: `${Math.min(100, pct)}%` }}
                      />
                    </div>
                  </div>
                ))}
            </div>
            {metrics.acessiveis && (
              <p className="text-xs text-secondary">
                Acessíveis:{" "}
                {(metrics.acessiveis as string[])
                  .map((a) => ARCHETYPE_LABELS[a] || a)
                  .join(", ")}
              </p>
            )}
            {metrics.ausentes &&
              (metrics.ausentes as string[]).length > 0 && (
                <p className="text-xs text-tertiary">
                  Ausentes:{" "}
                  {(metrics.ausentes as string[])
                    .map((a) => ARCHETYPE_LABELS[a] || a)
                    .join(", ")}
                </p>
              )}
          </section>
        )}

        {/* Defaults detectados (variety) */}
        {dimension === "variety" &&
          metrics.defaults_detectados &&
          (metrics.defaults_detectados as string[]).length > 0 && (
            <section className="rounded-2xl bg-tertiary/10 p-5 ghost-border">
              <p className="font-headline text-base font-bold text-tertiary">
                Padrões detectados
              </p>
              <p className="mt-2 text-sm text-on-surface-variant">
                Pilares travados:{" "}
                <strong>
                  {(metrics.defaults_detectados as string[]).join(", ")}
                </strong>
              </p>
              <p className="mt-3 text-xs text-tertiary italic">
                &ldquo;Sempre que algo se torna padrão, se torna
                não-funcional.&rdquo;
              </p>
            </section>
          )}

        {/* Feedback v2 */}
        {feedback.feedback && (
          <section className="space-y-3">
            <div className="rounded-2xl bg-surface-container-low p-5 ghost-border">
              <p className="text-sm text-on-surface leading-relaxed">
                {feedback.feedback}
              </p>
            </div>
            {feedback.dica && (
              <div className="rounded-2xl bg-surface-container-high p-5 ghost-border">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-secondary mb-2">
                  Dica prática
                </p>
                <p className="text-sm text-on-surface leading-relaxed">
                  {feedback.dica}
                </p>
              </div>
            )}
          </section>
        )}

        {/* Feedback v1 (retrocompat) */}
        {!feedback.feedback && feedback.strengths && (
          <section className="space-y-4">
            <div className="rounded-2xl bg-surface-container-low p-5 ghost-border">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-secondary mb-3">
                Pontos fortes
              </p>
              <ul className="space-y-2">
                {feedback.strengths.map((s: string, i: number) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-on-surface-variant"
                  >
                    <span className="material-symbols-outlined text-secondary text-base mt-0.5">
                      check
                    </span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-2xl bg-surface-container-low p-5 ghost-border">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-tertiary mb-3">
                Melhorias
              </p>
              <ul className="space-y-2">
                {feedback.improvements?.map((s: string, i: number) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-on-surface-variant"
                  >
                    <span className="material-symbols-outlined text-tertiary text-base mt-0.5">
                      arrow_forward
                    </span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>

            {feedback.tip && (
              <div className="rounded-2xl bg-surface-container-high p-5 ghost-border">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-secondary mb-2">
                  Dica
                </p>
                <p className="text-sm text-on-surface leading-relaxed">
                  {feedback.tip}
                </p>
              </div>
            )}
          </section>
        )}

        {/* Top fillers */}
        {dimension === "fillers" && metrics.top_fillers && (
          <section className="space-y-3">
            <h2 className="font-label text-xs uppercase tracking-[0.3em] text-secondary">
              Principais vícios
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {(metrics.top_fillers as any[]).map((f: any, i: number) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-xl bg-surface-container-low px-4 py-3 ghost-border"
                >
                  <span className="text-sm text-on-surface italic">
                    &ldquo;{f.word}&rdquo;
                  </span>
                  <span className="font-headline font-bold text-tertiary">
                    {f.count}x
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Clusters (fillers) */}
        {dimension === "fillers" &&
          metrics.clusters &&
          (metrics.clusters as any[]).length > 0 && (
            <section className="rounded-2xl bg-error-container/20 p-5 ghost-border">
              <p className="font-headline text-base font-bold text-error">
                Problemas de fluência ({(metrics.clusters as any[]).length})
              </p>
              <p className="text-xs text-on-surface-variant mt-1">
                Momentos com 3+ vícios em sequência rápida.
              </p>
            </section>
          )}

        {/* Pausas (voice) */}
        {dimension === "voice" && metrics.pausas && (
          <section className="space-y-3">
            <h2 className="font-label text-xs uppercase tracking-[0.3em] text-secondary">
              Pausas
            </h2>
            <div className="rounded-xl bg-surface-container-low p-4 text-sm text-on-surface-variant leading-relaxed space-y-2 ghost-border">
              <p>
                Pausas não são vazio — são parte da fala. Detectamos cada silêncio &gt; 200ms e classificamos pelo contexto:
              </p>
              <ul className="list-disc pl-5 space-y-1">
                <li>
                  <strong className="text-secondary">Estratégicas</strong> — pausa &ge; 0.6s logo após uma frase de impacto. Cria espaço pra audiência processar. Pausa é poder.
                </li>
                <li>
                  <strong className="text-tertiary">Hesitação</strong> — pausa antes ou ao redor de muletas/conectivos ("né", "tipo", "então"). Sinaliza busca de palavra.
                </li>
                <li>
                  <strong className="text-on-surface">Respiração</strong> — micro-pausas 0.2-0.5s entre orações com continuação fluente. Saudáveis, mostram controle de ar.
                </li>
              </ul>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-2xl bg-surface-container-low p-4 text-center ghost-border">
                <p className="font-headline text-2xl font-bold text-secondary">
                  {metrics.pausas.qtd_estrategicas}
                </p>
                <p className="text-xs text-on-surface-variant mt-1">
                  Estratégicas
                </p>
              </div>
              <div className="rounded-2xl bg-surface-container-low p-4 text-center ghost-border">
                <p className="font-headline text-2xl font-bold text-tertiary">
                  {metrics.pausas.qtd_hesitacao}
                </p>
                <p className="text-xs text-on-surface-variant mt-1">
                  Hesitação
                </p>
              </div>
              <div className="rounded-2xl bg-surface-container-low p-4 text-center ghost-border">
                <p className="font-headline text-2xl font-bold text-on-surface-variant">
                  {metrics.pausas.qtd_respiracao}
                </p>
                <p className="text-xs text-on-surface-variant mt-1">
                  Respiração
                </p>
              </div>
            </div>
          </section>
        )}
      </div>
    </AppShell>
  );
}
