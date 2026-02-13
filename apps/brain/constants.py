ANXIETY_KEYWORDS = [
    "ansioso",
    "ansiosa",
    "ancioso",
    "anciosa",
    "ansiedade",
    "nervoso",
    "nervosa",
    "panico",
    "pânico",
    "taquicardia",
    "tremendo",
    "tremor",
    "suando",
    "suor",
    "apreensivo",
    "apreensiva",
]

EXAM_KEYWORDS = [
    "prova",
    "teste",
    "exame",
    "apresentacao",
    "apresentação",
    "seminario",
    "seminário",
    "avaliacao",
    "avaliação",
    "banca",
    "trabalho",
    "entrega",
]

CONTEXT_MESSAGES = {
    "stress_repeat": [
        "Percebo que isso esta se repetindo. Quer me contar um pouco mais do que esta pesando?",
        "Notei que isso voltou a aparecer. Vamos escolher um passo pequeno para aliviar agora?",
        "Entendi. Isso tem se repetido. Quer que eu te ajude a reduzir a carga em 1 prioridade?",
    ],
    "evolucao_repeat": [
        "Voce esta criando consistencia. Quer definir a proxima meta pequena?",
        "Isso e repeticao do bem: consistencia. Qual a proxima etapa simples?",
        "Voce esta mantendo um bom ritmo. Quer escolher um objetivo de 15 minutos agora?",
    ],
    "stress_to_evolucao": [
        "Olha o progresso ai. Ontem parecia pesado e hoje voce avancou.",
        "Da para ver evolucao. Mesmo com desafios recentes, voce conseguiu avancar.",
        "Isso e um bom sinal: voce saiu do peso e foi para a acao. Parabens pelo passo.",
    ],
    "stress_anxiety": [
        "Ansiedade antes de prova e comum. Quer que eu te guie por 60 segundos para acalmar o corpo?",
        "Entendi. Vamos reduzir a ansiedade agora: respira devagar e me diz de 0 a 10 como esta.",
        "Voce nao esta sozinho nisso. Vamos focar no que esta sob controle: qual assunto voce revisou melhor?",
        "Se a ansiedade estiver alta, a meta agora e estabilizar. Quer uma tecnica rapida de aterramento (5-4-3-2-1)?",
    ],
    "stress_short_direction_main": [
        "Você já revisou tudo. O que está acontecendo agora não é falta de preparo, é ansiedade falando alto.\n"
        "Vamos fazer o seguinte: pare por 1 minuto e respire mais lento do que o normal.\n"
        "Depois disso, escolha só 1 tópico que você domina e relembre mentalmente como explicaria ele para alguém.\n"
        "Seu corpo vai entender que você está no controle."
    ],
    "stress_short_direction_ok": [
        "Ótimo. Agora é executar. Você já fez sua parte."
    ],
    "stress_short_direction_body": [
        "Se ainda está forte, é o corpo pedindo regulação.\n"
        "Levanta, movimenta os ombros, dá alguns saltos leves e respira mais lento por 1 minuto.\n"
        "Depois começa pela questão mais simples.\n"
        "Você já fez o trabalho. Agora é executar."
    ],
}
