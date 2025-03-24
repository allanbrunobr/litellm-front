/**
 * Scripts para o LiteLLM Key Manager
 */

// Copy text to clipboard
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(
    function () {
      // Mostrar tooltip ou notificação
      const tooltip = document.createElement("div");
      tooltip.innerText = "Copiado!";
      tooltip.className =
        "position-fixed top-50 start-50 translate-middle bg-dark text-white py-2 px-3 rounded";
      tooltip.style.zIndex = "9999";
      document.body.appendChild(tooltip);

      // Remover tooltip após 2 segundos
      setTimeout(() => {
        tooltip.remove();
      }, 2000);
    },
    function (err) {
      console.error("Não foi possível copiar o texto: ", err);
      showNotification("error", "Erro ao copiar para a área de transferência");
    }
  );
}

// Format date strings
function formatDate(dateString) {
  if (!dateString) return "N/A";

  try {
    const date = new Date(dateString);
    return date.toLocaleDateString() + " " + date.toLocaleTimeString();
  } catch (error) {
    return dateString;
  }
}

// Show API Key with copy button
function showApiKey(keyValue) {
  const keyDisplay = document.getElementById("generatedKey");
  if (keyDisplay) {
    keyDisplay.textContent = keyValue;

    // Make the container visible
    document.getElementById("keyResultContainer").classList.remove("d-none");

    // Scroll to the key result container
    document.getElementById("keyResultContainer").scrollIntoView({
      behavior: "smooth",
    });
  }
}

// Confirm delete action
function confirmDelete(keyId) {
  /* 
  FUNÇÃO DESATIVADA - Substituída pelo modal Bootstrap no template keys.html
  Esta função usava um confirm() nativo que causava problemas com o fluxo da UI
  Agora usamos a função showDeleteConfirmation em seu lugar.
  */

  // Para evitar erros, apenas retornar sem fazer nada
  console.log(
    "Função confirmDelete() está desabilitada. Use showDeleteConfirmation no lugar."
  );
  return false;
}

// Check server health
function checkServerHealth() {
  fetch("/api/health")
    .then((response) => response.json())
    .then((data) => {
      const statusIndicator = document.getElementById("serverStatus");
      if (statusIndicator) {
        if (data.litellm_server && data.litellm_server.accessible) {
          statusIndicator.className = "api-status online";
          statusIndicator.title = "Servidor online";
        } else {
          statusIndicator.className = "api-status offline";
          statusIndicator.title = "Servidor offline";
        }
      }
    })
    .catch(() => {
      const statusIndicator = document.getElementById("serverStatus");
      if (statusIndicator) {
        statusIndicator.className = "api-status offline";
        statusIndicator.title = "Erro ao verificar status";
      }
    });
}

// Create new key via API
document.addEventListener("DOMContentLoaded", function () {
  // Verificar status do servidor periodicamente
  checkServerHealth();
  setInterval(checkServerHealth, 60000); // Verificar a cada minuto

  // Configurar o formulário de criação de chave
  const keyForm = document.getElementById("createKeyForm");

  if (keyForm) {
    keyForm.addEventListener("submit", function (e) {
      e.preventDefault();

      // Get form data
      const formData = new FormData(keyForm);
      const jsonData = {};

      // Convert FormData to JSON
      for (const [key, value] of formData.entries()) {
        if (key === "models") {
          if (!jsonData[key]) {
            jsonData[key] = [];
          }
          jsonData[key].push(value);
        } else {
          jsonData[key] = value;
        }
      }

      // Adicionar spinner ao botão
      const submitButton = keyForm.querySelector('button[type="submit"]');
      const originalButtonText = submitButton.innerHTML;
      submitButton.innerHTML =
        '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processando...';
      submitButton.disabled = true;

      // Send API request
      fetch("/api/keys", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(jsonData),
      })
        .then((response) => response.json())
        .then((data) => {
          // Restaurar botão
          submitButton.innerHTML = originalButtonText;
          submitButton.disabled = false;

          if (data.key) {
            // Show the API key
            showApiKey(data.key);

            // Reset form
            keyForm.reset();

            // Show success message
            showNotification("success", "Chave criada com sucesso!");
          } else {
            showNotification(
              "error",
              "Erro ao criar chave: " + (data.error || "Erro desconhecido")
            );
          }
        })
        .catch((error) => {
          // Restaurar botão
          submitButton.innerHTML = originalButtonText;
          submitButton.disabled = false;

          console.error("Erro:", error);
          showNotification("error", "Erro ao processar a solicitação.");
        });
    });
  }

  // Configurar botões de teste de conexão
  const testConnectionBtn = document.getElementById("test-connection-btn");
  if (testConnectionBtn) {
    testConnectionBtn.addEventListener("click", function () {
      const serverUrl = document.getElementById("server-url").value;
      const masterKeyInput = document.getElementById("master-key");
      // Usar o valor original da chave armazenado no dataset, não o valor mascarado exibido
      const masterKey =
        masterKeyInput.dataset.originalValue || masterKeyInput.value;

      testLiteLLMConnection(serverUrl, masterKey);
    });
  }

  // Configurar botões de criar chave
  const createKeyBtn = document.getElementById("createKeyBtn");
  if (createKeyBtn) {
    // Verificar se o botão já tem um handler definido no script inline
    // Essa verificação evita duplicação de event listeners
    if (!createKeyBtn.hasAttribute("data-has-click-handler")) {
      // Adicionar botão "Selecionar todos" para os modelos
      const modelSelection = document.querySelector(".model-selection");
      if (modelSelection) {
        // Criar o seletor "Todos os modelos"
        const allModelsContainer = document.createElement("div");
        allModelsContainer.className = "mb-2 border-bottom pb-2";

        const allModelsCheck = document.createElement("div");
        allModelsCheck.className = "form-check";

        const allModelsInput = document.createElement("input");
        allModelsInput.className = "form-check-input";
        allModelsInput.type = "checkbox";
        allModelsInput.id = "selectAllModels";

        const allModelsLabel = document.createElement("label");
        allModelsLabel.className = "form-check-label fw-bold";
        allModelsLabel.htmlFor = "selectAllModels";
        allModelsLabel.textContent = "Selecionar todos os modelos";

        allModelsCheck.appendChild(allModelsInput);
        allModelsCheck.appendChild(allModelsLabel);
        allModelsContainer.appendChild(allModelsCheck);

        // Inserir antes de todos os outros modelos
        modelSelection.insertBefore(
          allModelsContainer,
          modelSelection.firstChild
        );

        // Configurar funcionamento do checkbox "Selecionar todos"
        allModelsInput.addEventListener("change", function () {
          const modelCheckboxes = modelSelection.querySelectorAll(
            "input.model-checkbox"
          );
          const isChecked = this.checked;

          modelCheckboxes.forEach((checkbox) => {
            checkbox.checked = isChecked;
          });
        });

        // Atualizar estado do "Selecionar todos" quando checkboxes individuais são alterados
        const modelCheckboxes = modelSelection.querySelectorAll(
          "input.model-checkbox"
        );
        modelCheckboxes.forEach((checkbox) => {
          checkbox.addEventListener("change", function () {
            const allChecked = Array.from(modelCheckboxes).every(
              (cb) => cb.checked
            );
            const someChecked = Array.from(modelCheckboxes).some(
              (cb) => cb.checked
            );

            allModelsInput.checked = allChecked;
            allModelsInput.indeterminate = someChecked && !allChecked;
          });
        });
      }

      // NÃO adicionar outro event listener ao botão, pois já existe um no script inline
      console.log("O botão createKeyBtn já tem um handler no script inline.");
    }
  }

  // Configurar botões de excluir chave
  /* 
  CÓDIGO DESATIVADO - Os botões de exclusão agora usam onclick="showDeleteConfirmation(this)" diretamente no HTML
  para evitar conflitos com o modal Bootstrap.
  */

  // Configurar botões de copiar
  const copyButtons = document.querySelectorAll(".copy-btn");
  copyButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const valueToCopy = this.getAttribute("data-copy-value");
      if (valueToCopy) {
        // Criar um elemento de texto temporário
        const tempInput = document.createElement("input");
        tempInput.value = valueToCopy;
        document.body.appendChild(tempInput);
        tempInput.select();
        tempInput.setSelectionRange(0, 99999); // Para dispositivos móveis
        document.execCommand("copy");
        document.body.removeChild(tempInput);

        // Mudar o texto do botão temporariamente
        const originalHTML = this.innerHTML;
        this.innerHTML = '<i class="fas fa-check"></i> Copied!';
        setTimeout(() => {
          this.innerHTML = originalHTML;
        }, 2000);
      }
    });
  });

  // Verificar status do servidor ao carregar a página
  fetch("/api/health")
    .then((response) => {
      updateServerStatus(response.ok);
    })
    .catch(() => {
      updateServerStatus(false);
    });
});

/*
 * LiteLLM Key Manager
 * Main JavaScript Functions
 */

// Função para testar a conexão com o servidor LiteLLM
function testLiteLLMConnection(serverUrl, masterKey) {
  // Exibir estado de carregamento
  showLoadingState("Testando conexão...");

  // Preparar dados da requisição
  const requestData = {
    server_url: serverUrl,
    master_key: masterKey,
  };

  // Chamar a API
  fetch("/api/test_connection", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(requestData),
  })
    .then((response) => response.json())
    .then((data) => {
      // Esconder o estado de carregamento
      hideLoadingState();

      // Verificar resultado
      if (data.success) {
        showNotification(
          "success",
          "Conexão bem-sucedida com o servidor LiteLLM!"
        );
        updateServerStatus(true);
      } else {
        // Personalizar a mensagem de erro para o caso de timeout
        let errorMsg = data.error || "Erro desconhecido";

        if (errorMsg.includes("timed out") || errorMsg.includes("timeout")) {
          errorMsg =
            "Servidor não respondeu no tempo esperado. Verifique se o endereço está correto e se o servidor está disponível.";
        } else if (errorMsg.includes("Connection refused")) {
          errorMsg =
            "Conexão recusada. Verifique se o servidor está em execução no endereço especificado.";
        } else if (errorMsg.includes("Name or service not known")) {
          errorMsg =
            "Não foi possível encontrar o servidor. Verifique o endereço e sua conexão com a internet.";
        }

        showNotification("error", `Falha na conexão: ${errorMsg}`);
        updateServerStatus(false);
      }
    })
    .catch((error) => {
      hideLoadingState();
      // Personalizar a mensagem de erro para exceções
      let errorMsg = error.message;

      if (
        errorMsg.includes("NetworkError") ||
        errorMsg.includes("Failed to fetch")
      ) {
        errorMsg =
          "Erro de rede. Verifique sua conexão com a internet e se o servidor está acessível.";
      }

      showNotification("error", `Erro ao testar conexão: ${errorMsg}`);
      updateServerStatus(false);
    });
}

// Função para criar uma nova chave
function createKey(formData) {
  showLoadingState("Criando chave...");

  fetch("/api/keys", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(formData),
  })
    .then((response) => response.json())
    .then((data) => {
      hideLoadingState();

      if (data.error) {
        showNotification("error", `Erro ao criar chave: ${data.error}`);
      } else {
        // Mostrar os detalhes da chave criada
        showKeyCreatedModal(data);
        // Não é mais necessário recarregar a página aqui, pois isso é tratado no arquivo keys.html
      }
    })
    .catch((error) => {
      hideLoadingState();
      showNotification("error", `Erro ao criar chave: ${error.message}`);
    });
}

// Funções de UI

// Exibir estado de carregamento
function showLoadingState(message) {
  const loadingElement = document.getElementById("loading-overlay");
  if (loadingElement) {
    const messageElement = loadingElement.querySelector(".loading-message");
    if (messageElement) {
      messageElement.textContent = message || "Carregando...";
    }
    loadingElement.style.display = "flex";
  } else {
    // Criar um overlay de carregamento se não existir
    const overlay = document.createElement("div");
    overlay.id = "loading-overlay";
    overlay.style.position = "fixed";
    overlay.style.top = "0";
    overlay.style.left = "0";
    overlay.style.width = "100%";
    overlay.style.height = "100%";
    overlay.style.backgroundColor = "rgba(0, 0, 0, 0.5)";
    overlay.style.display = "flex";
    overlay.style.justifyContent = "center";
    overlay.style.alignItems = "center";
    overlay.style.zIndex = "9999";

    const spinner = document.createElement("div");
    spinner.className = "spinner-border text-light";
    spinner.setAttribute("role", "status");

    const loadingMessage = document.createElement("div");
    loadingMessage.className = "loading-message text-white ms-3";
    loadingMessage.textContent = message || "Carregando...";

    const spinnerContainer = document.createElement("div");
    spinnerContainer.className = "d-flex align-items-center";
    spinnerContainer.appendChild(spinner);
    spinnerContainer.appendChild(loadingMessage);

    overlay.appendChild(spinnerContainer);
    document.body.appendChild(overlay);
  }
}

// Esconder estado de carregamento
function hideLoadingState() {
  const loadingElement = document.getElementById("loading-overlay");
  if (loadingElement) {
    loadingElement.style.display = "none";
  }
}

// Exibir notificação
function showNotification(type, message) {
  // Verificar se já existe um container para notificações
  let notificationContainer = document.getElementById("notification-container");

  if (!notificationContainer) {
    notificationContainer = document.createElement("div");
    notificationContainer.id = "notification-container";
    notificationContainer.style.position = "fixed";
    notificationContainer.style.top = "20px";
    notificationContainer.style.right = "20px";
    notificationContainer.style.zIndex = "9999";
    document.body.appendChild(notificationContainer);
  }

  // Criar a notificação
  const notification = document.createElement("div");
  notification.className = `alert alert-${
    type === "error" ? "danger" : type
  } alert-dismissible fade show`;
  notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

  // Adicionar ao container
  notificationContainer.appendChild(notification);

  // Auto-remover após 5 segundos
  setTimeout(() => {
    notification.classList.remove("show");
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 300);
  }, 5000);
}

// Mostrar modal com chave criada
function showKeyCreatedModal(data) {
  const keyValue = data.api_key || data.key || data.token || "";

  // Encontrar o modal existente ou criar um novo
  let modal = document.getElementById("keyCreatedModal");

  if (modal) {
    // Se o modal já existe, atualizar o valor da chave
    const keyInput = document.getElementById("createdKeyValue");
    if (keyInput) {
      keyInput.value = keyValue;
    }

    // Exibir o modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
  } else {
    // Se o modal não existe, criar um novo
    const modalHTML = `
            <div class="modal fade" id="keyCreatedModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">API Key Created</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="alert alert-warning">
                                <i class="fas fa-exclamation-triangle"></i>
                                Save this API key now. You won't be able to see it again!
                            </div>
                            <div class="mb-3">
                                <label class="form-label">API Key:</label>
                                <div class="input-group">
                                    <input type="text" class="form-control" id="createdKeyValue" value="${keyValue}" readonly>
                                    <button class="btn btn-outline-secondary" type="button" id="copyKeyBtn">
                                        <i class="fas fa-copy"></i> Copy
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

    // Adicionar o modal ao corpo do documento
    const modalContainer = document.createElement("div");
    modalContainer.innerHTML = modalHTML;
    document.body.appendChild(modalContainer);

    // Exibir o modal
    const modal = document.getElementById("keyCreatedModal");
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();

    // Configurar o botão de cópia
    document
      .getElementById("copyKeyBtn")
      .addEventListener("click", function () {
        const keyInput = document.getElementById("createdKeyValue");
        keyInput.select();
        keyInput.setSelectionRange(0, 99999); // Para dispositivos móveis
        document.execCommand("copy");
        this.innerHTML = '<i class="fas fa-check"></i> Copied!';
        setTimeout(() => {
          this.innerHTML = '<i class="fas fa-copy"></i> Copy';
        }, 2000);
      });
  }
}

// Atualizar o status do servidor na UI
function updateServerStatus(isOnline) {
  const statusElement = document.getElementById("server-status");
  if (statusElement) {
    if (isOnline) {
      statusElement.className = "badge bg-success";
      statusElement.textContent = "Online";
    } else {
      statusElement.className = "badge bg-danger";
      statusElement.textContent = "Offline";
    }
  }

  // Atualizar também o alerta de status na página de configurações
  const statusAlert = document.querySelector('.alert[role="alert"]');
  if (statusAlert) {
    if (isOnline) {
      statusAlert.className = "alert alert-success d-flex align-items-center";
      const icon = statusAlert.querySelector("i");
      if (icon) {
        icon.className = "fas fa-check-circle me-2";
      }
      const statusText = statusAlert.querySelector("span");
      if (statusText) {
        statusText.textContent = "LiteLLM Server is online and responding";
      }
    } else {
      statusAlert.className = "alert alert-danger d-flex align-items-center";
      const icon = statusAlert.querySelector("i");
      if (icon) {
        icon.className = "fas fa-exclamation-triangle me-2";
      }
      const statusText = statusAlert.querySelector("span");
      if (statusText) {
        statusText.textContent = "LiteLLM Server is offline or not responding";
      }
    }
  }
}
