(function () {
  var roots = document.querySelectorAll("[data-learning-dashboard-root]");
  if (!roots.length) {
    return;
  }

  roots.forEach(function (root) {
    var apiUrl = root.getAttribute("data-api-url");
    var dashboardKind = root.getAttribute("data-dashboard-kind");

    if (!apiUrl || !dashboardKind) {
      return;
    }

    fetch(apiUrl + buildApiQueryString(dashboardKind), {
      method: "GET",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
      },
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Dashboard request failed");
        }
        return response.json();
      })
      .then(function (payload) {
        if (dashboardKind === "student") {
          renderStudentDashboard(root, payload);
          return;
        }
        if (dashboardKind === "parent") {
          renderParentDashboard(root, payload);
          return;
        }
        if (dashboardKind === "teacher") {
          renderTeacherDashboard(root, payload);
          return;
        }
        if (dashboardKind === "institution") {
          renderInstitutionDashboard(root, payload);
        }
      })
      .catch(function () {
        renderFallback(root, dashboardKind);
      });
  });

  function buildApiQueryString(dashboardKind) {
    if (dashboardKind !== "teacher") {
      return "";
    }
    var params = new URLSearchParams(window.location.search);
    var apiParams = new URLSearchParams();

    ["class_group", "search", "page", "page_size"].forEach(function (key) {
      if (params.get(key)) {
        apiParams.set(key, params.get(key));
      }
    });

    var queryString = apiParams.toString();
    return queryString ? "?" + queryString : "";
  }

  function renderStudentDashboard(root, payload) {
    setText(root, "[data-student-score-value]", readValue(payload, ["score_current", "score_value"], "--"));
    setText(root, "[data-student-score-classification]", readValue(payload, ["score_current", "classification"], "--"));
    setText(root, "[data-student-sessions]", readValue(payload, ["study_consistency", "sessions_last_7_days"], "--"));
    setText(root, "[data-student-study-days]", readValue(payload, ["study_consistency", "study_days_last_30_days"], "--"));
    setText(root, "[data-student-streak]", readValue(payload, ["study_consistency", "current_streak_days"], "--"));
    renderList(root, "[data-student-alerts]", payload.friendly_alerts, "Nenhum alerta no momento.");
    renderList(root, "[data-student-recommendations]", payload.recommendations, "Nenhuma recomendação no momento.");
  }

  function renderParentDashboard(root, payload) {
    var container = root.querySelector("[data-parent-children]");
    if (!container) {
      return;
    }
    var children = Array.isArray(payload.children) ? payload.children : [];
    if (!children.length) {
      container.innerHTML = '<article class="learning-api-stat"><div class="student-card-muted">Nenhum vínculo encontrado.</div></article>';
      return;
    }
    container.innerHTML = children
      .map(function (child) {
        return (
          '<article class="learning-api-stat">' +
          '<div class="learning-api-label">' + escapeHtml(child.student_name || "-") + " · " + escapeHtml(child.relationship_type || "-") + "</div>" +
          '<div class="learning-api-value">' + escapeHtml(String(readValue(child, ["score_current", "score_value"], "--"))) + "</div>" +
          '<div class="student-card-muted">' + escapeHtml(String(readValue(child, ["score_current", "classification"], "-"))) + "</div>" +
          '<div class="student-card-muted mt-2">Sessões na semana: ' + escapeHtml(String(readValue(child, ["study_consistency", "sessions_last_7_days"], 0))) + "</div>" +
          '<div class="student-card-muted">Sequência atual: ' + escapeHtml(String(readValue(child, ["study_consistency", "current_streak_days"], 0))) + " dias</div>" +
          "</article>"
        );
      })
      .join("");
  }

  function renderTeacherDashboard(root, payload) {
    setText(
      root,
      "[data-teacher-average-label]",
      readValue(payload, ["ranking_filters", "class_group"], "") ? "Média da turma" : "Média geral"
    );
    setText(root, "[data-teacher-class-average]", readValue(payload, ["class_average"], "--"));
    setText(root, "[data-teacher-at-risk]", arrayLength(payload.students_at_risk));
    setText(root, "[data-teacher-low-consistency]", arrayLength(payload.students_low_consistency));
    setText(root, "[data-teacher-good-discipline]", arrayLength(payload.students_good_discipline));
    renderList(root, "[data-teacher-insights]", payload.pedagogical_insights, "Sem insights no momento.");
    renderList(
      root,
      "[data-teacher-distribution]",
      (payload.distribution || []).map(function (entry) {
        return entry.classification + ": " + entry.total;
      }),
      "Sem distribuição disponível."
    );
    renderTeacherRanking(root, payload.ranking || []);
    renderTeacherPagination(root, payload.ranking_pagination || {}, payload.ranking_filters || {});
  }

  function renderInstitutionDashboard(root, payload) {
    setText(root, "[data-institution-average]", readValue(payload, ["institution_average"], "--"));
    setText(root, "[data-institution-at-risk]", arrayLength(payload.students_at_risk));
    setText(root, "[data-institution-class-count]", arrayLength(payload.class_ranking));
    renderInstitutionClassRanking(root, payload.class_ranking || []);
    renderList(root, "[data-institution-insights]", payload.pedagogical_insights, "Sem insights institucionais.");
  }

  function renderInstitutionClassRanking(root, rows) {
    var target = root.querySelector("[data-institution-class-ranking]");
    if (!target) {
      return;
    }
    if (!rows.length) {
      target.innerHTML = '<tr><td colspan="4" class="text-muted">Sem ranking de turmas.</td></tr>';
      return;
    }
    target.innerHTML = rows
      .map(function (row, index) {
        return (
          "<tr>" +
          "<td>" + escapeHtml(String(index + 1)) + "º</td>" +
          "<td>" + escapeHtml(row.class_group || "-") + "</td>" +
          "<td>" + escapeHtml(String(row.average_score || 0)) + "</td>" +
          "<td>" + escapeHtml(String(row.students_total || 0)) + "</td>" +
          "</tr>"
        );
      })
      .join("");
  }

  function renderTeacherRanking(root, rows) {
    var target = root.querySelector("[data-teacher-ranking]");
    if (!target) {
      return;
    }
    if (!rows.length) {
      target.innerHTML = '<tr><td colspan="6" class="text-muted">Sem ranking disponível.</td></tr>';
      return;
    }
    target.innerHTML = rows
      .map(function (row) {
        return (
          "<tr>" +
          "<td>" + escapeHtml(row.student_name || "-") + "</td>" +
          "<td>" + escapeHtml(row.class_group || "-") + "</td>" +
          "<td>" + escapeHtml(String(row.score_value || 0)) + "</td>" +
          "<td>" + escapeHtml(row.classification || "-") + "</td>" +
          "<td>" + escapeHtml(String(row.weekly_sessions || 0)) + "</td>" +
          "<td>" + escapeHtml(String(row.overdue_tasks || 0)) + "</td>" +
          "</tr>"
        );
      })
      .join("");
  }

  function renderTeacherPagination(root, pagination, filters) {
    var summary = root.querySelector("[data-teacher-pagination-summary]");
    var links = root.querySelector("[data-teacher-pagination-links]");
    if (!summary || !links) {
      return;
    }

    var page = Number(pagination.page || 1);
    var totalPages = Number(pagination.total_pages || 1);
    var totalItems = Number(pagination.total_items || 0);
    var pageSize = Number(pagination.page_size || 10);

    summary.textContent = "Página " + page + " de " + totalPages + " · " + totalItems + " alunos";
    links.innerHTML = "";

    if (pagination.has_previous) {
      links.appendChild(buildPaginationLink("Anterior", page - 1, pageSize, filters));
    }
    if (pagination.has_next) {
      links.appendChild(buildPaginationLink("Próxima", page + 1, pageSize, filters));
    }
  }

  function buildPaginationLink(label, page, pageSize, filters) {
    var params = new URLSearchParams(window.location.search);
    params.set("page", page);
    params.set("page_size", pageSize);
    if (filters.class_group) {
      params.set("class_group", filters.class_group);
    } else {
      params.delete("class_group");
    }
    if (filters.search) {
      params.set("search", filters.search);
    } else {
      params.delete("search");
    }

    var link = document.createElement("a");
    link.className = "btn btn-sm btn-outline-secondary";
    link.href = window.location.pathname + "?" + params.toString();
    link.textContent = label;
    return link;
  }

  function renderList(root, selector, items, emptyMessage) {
    var target = root.querySelector(selector);
    if (!target) {
      return;
    }
    if (!Array.isArray(items) || !items.length) {
      target.innerHTML = '<li class="student-list-item"><span class="student-list-meta">' + escapeHtml(emptyMessage) + "</span></li>";
      return;
    }
    target.innerHTML = items
      .map(function (item) {
        return '<li class="student-list-item"><span class="student-list-meta">' + escapeHtml(String(item)) + "</span></li>";
      })
      .join("");
  }

  function renderFallback(root, dashboardKind) {
    if (dashboardKind === "student") {
      renderList(root, "[data-student-alerts]", [], "Não foi possível carregar o dashboard acadêmico agora.");
      renderList(root, "[data-student-recommendations]", [], "Tente novamente em instantes.");
    }
    if (dashboardKind === "parent") {
      var container = root.querySelector("[data-parent-children]");
      if (container) {
        container.innerHTML = '<article class="learning-api-stat"><div class="student-card-muted">Não foi possível carregar o dashboard familiar agora.</div></article>';
      }
    }
    if (dashboardKind === "teacher") {
      renderList(root, "[data-teacher-insights]", [], "Não foi possível carregar os insights agora.");
      renderList(root, "[data-teacher-distribution]", [], "Tente novamente em instantes.");
      renderTeacherRanking(root, []);
    }
    if (dashboardKind === "institution") {
      renderInstitutionClassRanking(root, []);
      renderList(root, "[data-institution-insights]", [], "Tente novamente em instantes.");
    }
  }

  function setText(root, selector, value) {
    var element = root.querySelector(selector);
    if (!element) {
      return;
    }
    element.textContent = String(value);
  }

  function readValue(source, path, fallback) {
    var current = source;
    for (var index = 0; index < path.length; index += 1) {
      if (current == null) {
        return fallback;
      }
      current = current[path[index]];
    }
    return current == null ? fallback : current;
  }

  function arrayLength(value) {
    return Array.isArray(value) ? value.length : 0;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
})();
