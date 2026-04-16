// Bloco Demo do Chat CampusCalm
(function () {
  const modal = document.querySelector("[data-demo-modal]");
  const openButton = document.querySelector("[data-demo-open]");
  const closeButtons = document.querySelectorAll("[data-demo-close]");
  const chatBody = document.querySelector("[data-demo-chat-body]");
  const intro = document.querySelector("[data-demo-intro]");

  if (!modal || !openButton || !chatBody || !intro) {
    return;
  }

  const steps = [
    {
      student: "Estou ansioso para a prova de amanhã...",
      system: "Entendo. Vamos organizar isso juntos em pequenos passos.",
      readDelay: 1700,
    },
    {
      student: "Não sei por onde começar",
      system: "Vamos simplificar:\n1. Revisar matemática\n2. Fazer exercícios\n3. Fazer pausa",
      readDelay: 2400,
    },
    {
      student: "Cria uma tarefa para revisar matemática hoje",
      system: "Tarefa criada com sucesso",
      card: {
        type: "task",
        label: "Nova tarefa",
        title: "Revisar matemática hoje",
        meta: "Prioridade do dia • foco em pequenos passos",
      },
      readDelay: 2200,
    },
    {
      student: "Cria um lembrete para estudar às 18h",
      system: "Lembrete criado com sucesso",
      readDelay: 1800,
    },
    {
      student: "Agenda uma revisão amanhã às 9h",
      system: "Evento criado na sua agenda",
      card: {
        type: "event",
        label: "Agenda atualizada",
        title: "Revisão amanhã às 9h",
        meta: "Evento adicionado para manter a rotina organizada",
      },
      readDelay: 2200,
    },
  ];

  let timers = [];
  let isRunning = false;
  let lastFocusedElement = null;

  function clearTimers() {
    timers.forEach((timer) => window.clearTimeout(timer));
    timers = [];
  }

  function schedule(callback, delay) {
    const timer = window.setTimeout(callback, delay);
    timers.push(timer);
  }

  function createMessageRow(role, text) {
    const row = document.createElement("div");
    row.className = `demo-chat-row is-${role}`;

    const bubble = document.createElement("div");
    bubble.className = "demo-chat-bubble";

    text.split("\n").forEach((line) => {
      const paragraph = document.createElement("p");
      paragraph.textContent = line;
      bubble.appendChild(paragraph);
    });

    row.appendChild(bubble);
    return row;
  }

  function createTypingRow() {
    const row = document.createElement("div");
    row.className = "demo-chat-row is-system";
    row.dataset.demoTyping = "true";

    const typing = document.createElement("div");
    typing.className = "demo-chat-typing";
    typing.innerHTML = "<span></span><span></span><span></span>";

    row.appendChild(typing);
    return row;
  }

  function createInlineCard(card) {
    const cardElement = document.createElement("div");
    cardElement.className = "demo-inline-card";

    const label = document.createElement("p");
    label.className = "demo-inline-card-label";
    label.textContent = card.label;
    cardElement.appendChild(label);

    const title = document.createElement("p");
    title.className = card.type === "task" ? "demo-task-card-title" : "demo-event-card-title";
    title.textContent = card.title;
    cardElement.appendChild(title);

    const meta = document.createElement("p");
    meta.className = card.type === "task" ? "demo-task-card-meta" : "demo-event-card-meta";
    meta.textContent = card.meta;
    cardElement.appendChild(meta);

    return cardElement;
  }

  function createFinalCard() {
    const finalCard = document.createElement("div");
    finalCard.className = "demo-final-card";
    finalCard.innerHTML = `
      <p class="demo-final-card-quote">Mais clareza. Mais foco. Mais tranquilidade.</p>
      <p class="demo-final-card-brand">CampusCalm</p>
    `;
    return finalCard;
  }

  function scrollChatToBottom() {
    chatBody.scrollTo({
      top: chatBody.scrollHeight,
      behavior: "smooth",
    });
  }

  function resetDemo() {
    clearTimers();
    isRunning = false;
    chatBody.innerHTML = "";
    chatBody.appendChild(intro);
    intro.hidden = false;
  }

  function playStep(index) {
    if (index >= steps.length) {
      schedule(() => {
        intro.hidden = true;
        chatBody.appendChild(createFinalCard());
        scrollChatToBottom();
      }, 900);
      return;
    }

    const step = steps[index];
    intro.hidden = true;

    schedule(() => {
      chatBody.appendChild(createMessageRow("student", step.student));
      scrollChatToBottom();

      schedule(() => {
        const typingRow = createTypingRow();
        chatBody.appendChild(typingRow);
        scrollChatToBottom();

        schedule(() => {
          typingRow.remove();

          const systemRow = createMessageRow("system", step.system);
          const bubble = systemRow.querySelector(".demo-chat-bubble");

          if (step.card) {
            bubble.appendChild(createInlineCard(step.card));
          }

          chatBody.appendChild(systemRow);
          scrollChatToBottom();

          playStep(index + 1);
        }, 1100);
      }, 950);
    }, index === 0 ? 500 : step.readDelay);
  }

  function openDemo() {
    if (isRunning) {
      return;
    }

    lastFocusedElement = document.activeElement;
    modal.hidden = false;
    document.body.classList.add("demo-modal-open");
    isRunning = true;
    resetDemo();
    isRunning = true;
    playStep(0);

    const closeButton = modal.querySelector(".demo-modal-close");
    if (closeButton) {
      closeButton.focus();
    }
  }

  function closeDemo() {
    modal.hidden = true;
    document.body.classList.remove("demo-modal-open");
    resetDemo();

    if (lastFocusedElement instanceof HTMLElement) {
      lastFocusedElement.focus();
    }
  }

  openButton.addEventListener("click", openDemo);

  closeButtons.forEach((button) => {
    button.addEventListener("click", closeDemo);
  });

  modal.addEventListener("click", (event) => {
    if (event.target === modal) {
      closeDemo();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) {
      closeDemo();
    }
  });
})();
