(function () {
  var bellButton = document.getElementById("studentBellButton");
  var badge = document.getElementById("studentBellBadge");
  var list = document.getElementById("studentBellList");
  var markAllButton = document.getElementById("studentBellMarkAll");

  if (!bellButton || !badge || !list || !markAllButton) {
    return;
  }

  var API_BASE = "/api/notifications/in-app";
  var STORAGE_KEY_UNREAD = "campuscalm_bell_unread_count_v1";
  var previousUnreadCount = readStoredUnreadCount();

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

  function apiGet(path) {
    return window.fetch(API_BASE + path, {
      method: "GET",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
      },
    }).then(function (response) {
      if (!response.ok) {
        throw new Error("request failed");
      }
      return response.json();
    });
  }

  function apiPost(path) {
    var headers = {
      Accept: "application/json",
      "X-CSRFToken": getCsrfToken(),
    };
    return window.fetch(API_BASE + path, {
      method: "POST",
      credentials: "same-origin",
      headers: headers,
    }).then(function (response) {
      if (!response.ok) {
        throw new Error("request failed");
      }
      return response.json();
    });
  }

  function formatDate(value) {
    if (!value) {
      return "";
    }
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "";
    }
    return date.toLocaleString();
  }

  function readStoredUnreadCount() {
    try {
      var raw = window.sessionStorage.getItem(STORAGE_KEY_UNREAD);
      if (raw === null) {
        return null;
      }
      var parsed = Number.parseInt(raw, 10);
      return Number.isNaN(parsed) ? null : parsed;
    } catch (error) {
      return null;
    }
  }

  function persistUnreadCount(unreadCount) {
    try {
      window.sessionStorage.setItem(STORAGE_KEY_UNREAD, String(unreadCount));
    } catch (error) {
      // Ignore storage failures (private mode/restrictions).
    }
  }

  function triggerBellPulse() {
    bellButton.classList.remove("is-pulsing");
    void bellButton.offsetWidth;
    bellButton.classList.add("is-pulsing");
    window.setTimeout(function () {
      bellButton.classList.remove("is-pulsing");
    }, 900);
  }

  function renderBadge(unreadCount) {
    if (unreadCount > 0) {
      badge.textContent = String(unreadCount);
      badge.classList.remove("d-none");
      return;
    }
    badge.textContent = "0";
    badge.classList.add("d-none");
  }

  function renderEmpty(message) {
    list.innerHTML = "";
    var empty = document.createElement("div");
    empty.className = "student-bell-empty text-muted";
    empty.textContent = message;
    list.appendChild(empty);
  }

  function markReadAndGo(notificationId, targetUrl) {
    apiPost("/" + encodeURIComponent(notificationId) + "/mark-read/")
      .catch(function () {
        // Even if mark-read fails, continue navigation.
      })
      .finally(function () {
        window.location.href = targetUrl;
      });
  }

  function renderDropdownItems(items) {
    list.innerHTML = "";
    if (!Array.isArray(items) || !items.length) {
      renderEmpty("Sem notificacoes recentes.");
      return;
    }

    items.forEach(function (item) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "student-bell-item" + (item.is_read ? "" : " is-unread");
      button.addEventListener("click", function () {
        markReadAndGo(item.id, item.target_url || "/tarefas/");
      });

      var title = document.createElement("div");
      title.className = "student-bell-item-title";
      title.textContent = item.title || "Notificacao";

      var body = document.createElement("div");
      body.className = "student-bell-item-body";
      body.textContent = item.body || "";

      var date = document.createElement("div");
      date.className = "student-bell-item-date";
      date.textContent = formatDate(item.created_at);

      button.appendChild(title);
      if (item.body) {
        button.appendChild(body);
      }
      button.appendChild(date);
      list.appendChild(button);
    });
  }

  function fetchUnreadCount() {
    return apiGet("/unread-count/").then(function (data) {
      var unreadCount = data.unread_count || 0;
      var shouldPulse = typeof previousUnreadCount === "number" && unreadCount > previousUnreadCount;
      renderBadge(unreadCount);
      if (shouldPulse) {
        triggerBellPulse();
      }
      previousUnreadCount = unreadCount;
      persistUnreadCount(unreadCount);
    });
  }

  function fetchLatest() {
    return apiGet("/latest/?limit=5").then(function (data) {
      renderDropdownItems(data);
    });
  }

  function refreshBell() {
    return Promise.all([fetchUnreadCount(), fetchLatest()]).catch(function () {
      renderEmpty("Nao foi possivel carregar notificacoes.");
    });
  }

  bellButton.addEventListener("show.bs.dropdown", function () {
    refreshBell();
  });

  markAllButton.addEventListener("click", function (event) {
    event.preventDefault();
    apiPost("/mark-all-read/")
      .then(function () {
        return refreshBell();
      })
      .catch(function () {
        // Keep UI stable if request fails.
      });
  });

  refreshBell();
})();
