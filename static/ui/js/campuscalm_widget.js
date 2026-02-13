(function () {
  var root = document.querySelector("[data-campuscalm-widget]");
  if (!root) {
    return;
  }

  var trigger = root.querySelector("[data-cc-trigger]");
  var panel = root.querySelector("[data-cc-panel]");
  var closeButton = root.querySelector("[data-cc-close]");
  var messagesContainer = root.querySelector("[data-cc-messages]");
  var form = root.querySelector("[data-cc-form]");
  var input = root.querySelector("[data-cc-input]");

  if (!trigger || !panel || !closeButton || !messagesContainer || !form || !input) {
    return;
  }

  var currentLang = String(document.documentElement.getAttribute("lang") || "").toLowerCase();
  var isEnglish = currentLang.indexOf("en") === 0;
  var API_ENDPOINT = "/api/widget/chat/";
  var STORAGE_KEY = "campuscalm_widget_history_v1_" + (isEnglish ? "en" : "pt");
  var LEGACY_INITIAL_BOT_MESSAGE = isEnglish
    ? "Hi! Want to organize what's worrying you right now?"
    : "Oi! Quer organizar o que esta te preocupando agora?";
  var INITIAL_BOT_MESSAGE = isEnglish
    ? "Hi! Want to organize what's worrying you right now?\nIf you want, I can help you turn this into 10 minutes of action."
    : "Oi! Quer organizar o que esta te preocupando agora?\nSe voce quiser, eu te ajudo a transformar isso em 10 minutos de acao.";
  var history = loadHistory();

  if (!history.length) {
    history = [{ role: "bot", text: INITIAL_BOT_MESSAGE }];
    persistHistory();
  } else if (history[0] && history[0].role === "bot" && history[0].text === LEGACY_INITIAL_BOT_MESSAGE) {
    history[0].text = INITIAL_BOT_MESSAGE;
    persistHistory();
  }

  renderHistory(history);

  trigger.addEventListener("click", function () {
    if (panel.hidden) {
      openWidget();
      return;
    }
    closeWidget();
  });

  closeButton.addEventListener("click", function () {
    closeWidget();
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    submitMessage();
  });

  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submitMessage();
    }
  });

  function openWidget() {
    panel.hidden = false;
    panel.setAttribute("aria-hidden", "false");
    root.classList.add("is-open");
    trigger.setAttribute("aria-expanded", "true");
    window.setTimeout(function () {
      input.focus();
      scrollMessagesToBottom();
    }, 20);
  }

  function closeWidget() {
    panel.setAttribute("aria-hidden", "true");
    trigger.setAttribute("aria-expanded", "false");
    root.classList.remove("is-open");
    window.setTimeout(function () {
      panel.hidden = true;
    }, 180);
  }

  function submitMessage() {
    var text = input.value.trim();
    if (!text) {
      return;
    }

    appendMessage("user", text);
    input.value = "";
    requestBackendReply(text);
  }

  function appendMessage(role, text) {
    var message = { role: role, text: text };
    history.push(message);
    persistHistory();

    var bubble = buildBubble(message);
    messagesContainer.appendChild(bubble);
    scrollMessagesToBottom();
  }

  function renderHistory(items) {
    messagesContainer.innerHTML = "";
    items.forEach(function (item) {
      messagesContainer.appendChild(buildBubble(item));
    });
    scrollMessagesToBottom();
  }

  function buildBubble(message) {
    var bubble = document.createElement("div");
    bubble.className =
      "cc-widget-bubble " +
      (message.role === "user" ? "cc-widget-bubble-user" : "cc-widget-bubble-bot");
    bubble.textContent = message.text;
    return bubble;
  }

  function scrollMessagesToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function requestBackendReply(text) {
    fetchBackendReply(text)
      .then(function (reply) {
        appendMessage("bot", reply);
      })
      .catch(function () {
        window.setTimeout(function () {
          appendMessage("bot", buildMockReply(text));
        }, 300);
      });
  }

  function fetchBackendReply(text) {
    var headers = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
    var csrfToken = getCsrfToken();
    if (csrfToken) {
      headers["X-CSRFToken"] = csrfToken;
    }

    return window
      .fetch(API_ENDPOINT, {
        method: "POST",
        credentials: "same-origin",
        headers: headers,
        body: JSON.stringify({ message: text }),
      })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Request failed");
        }
        return response.json();
      })
      .then(function (payload) {
        return formatBackendReply(payload);
      });
  }

  function formatBackendReply(payload) {
    if (!payload || typeof payload.reply !== "string" || payload.reply.trim() === "") {
      throw new Error("Invalid payload");
    }

    var reply = payload.reply.trim();
    var emojiPrefix = payload.emoji ? String(payload.emoji).trim() + " " : "";
    var microLines = formatMicroInterventions(payload.micro_interventions);
    return emojiPrefix + reply + microLines;
  }

  function formatMicroInterventions(items) {
    if (!Array.isArray(items) || !items.length) {
      return "";
    }

    var lines = items
      .filter(function (item) {
        return item && typeof item.nome === "string" && typeof item.texto === "string";
      })
      .map(function (item) {
        return "- " + item.nome + ": " + item.texto;
      });

    if (!lines.length) {
      return "";
    }

    var title = isEnglish ? "Micro interventions" : "Microintervencoes";
    return "\n\n" + title + ":\n" + lines.join("\n");
  }

  function getCsrfToken() {
    var cookies = document.cookie ? document.cookie.split(";") : [];
    for (var i = 0; i < cookies.length; i += 1) {
      var cookie = cookies[i].trim();
      if (cookie.indexOf("csrftoken=") === 0) {
        return decodeURIComponent(cookie.substring("csrftoken=".length));
      }
    }
    return "";
  }

  function buildMockReply(rawText) {
    var text = normalizeText(rawText);

    if (
      containsAny(text, [
        "ansioso",
        "prova",
        "medo",
        "nao estou preparado",
        "nao estudei o bastante",
        "anxious",
        "exam",
        "afraid",
        "not prepared",
      ])
    ) {
      if (isEnglish) {
        return "I understand. Let's split this into one small step now. What is the next simplest thing you can do in 10 minutes?";
      }
      return "Entendi. Vamos dividir isso em 1 passo pequeno agora. O que e a proxima coisa mais simples que voce pode fazer em 10 minutos?";
    }

    if (containsAny(text, ["cansado", "exausto", "dormi pouco", "sono", "tired", "exhausted", "sleepy"])) {
      if (isEnglish) {
        return "Your body is asking for an adjustment. Want a 2-minute breathing pause and then one light task?";
      }
      return "Seu corpo esta pedindo um ajuste. Quer fazer uma pausa de 2 minutos (respiracao) e depois escolher 1 tarefa leve?";
    }

    if (
      containsAny(text, [
        "distraido",
        "redes sociais",
        "me tira a atencao",
        "nao consigo concentrar",
        "distracted",
        "social media",
        "cant focus",
      ])
    ) {
      if (isEnglish) {
        return "Let's reduce friction: put your phone away for 10 minutes and choose one single task. Which task do you want to attack first?";
      }
      return "Vamos reduzir a friccao: coloque o celular longe por 10 minutos e escolha uma tarefa unica. Qual tarefa voce quer atacar primeiro?";
    }

    if (containsAny(text, ["travei", "nao consigo entender", "bloqueio", "stuck", "cant understand"])) {
      if (isEnglish) {
        return "Okay. Let's replace 'understand everything' with 'understand one part'. Which exact topic is blocking you?";
      }
      return "Ok. Vamos trocar 'entender tudo' por 'entender 1 parte'. Qual e o topico exato que esta travando?";
    }

    if (isEnglish) {
      return "Got it. Want to turn this into a short 10-minute plan now?";
    }
    return "Entendi. Quer transformar isso em um plano curto de 10 minutos agora?";
  }

  function containsAny(text, terms) {
    return terms.some(function (term) {
      return text.indexOf(term) !== -1;
    });
  }

  function normalizeText(value) {
    return String(value || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function loadHistory() {
    try {
      var raw = window.sessionStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return [];
      }
      var parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        return [];
      }
      return parsed.filter(function (item) {
        return (
          item &&
          (item.role === "bot" || item.role === "user") &&
          typeof item.text === "string" &&
          item.text.trim() !== ""
        );
      });
    } catch (error) {
      return [];
    }
  }

  function persistHistory() {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    } catch (error) {
      // Ignore storage issues in restricted environments.
    }
  }
})();
