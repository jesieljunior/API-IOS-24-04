/* static/js/script.js */

document.addEventListener("DOMContentLoaded", function () {
  // Flash Messages Auto-hide
  const flashMessages = document.querySelectorAll(".flash-message");
  if (flashMessages.length > 0) {
    flashMessages.forEach((message) => {
      setTimeout(() => {
        message.style.opacity = "0";
        setTimeout(() => {
          message.style.display = "none";
        }, 500);
      }, 5000);
    });
  }

  // Confirm Delete Actions
  const deleteButtons = document.querySelectorAll(".btn-danger");
  if (deleteButtons.length > 0) {
    deleteButtons.forEach((button) => {
      button.addEventListener("click", function (e) {
        if (
          !confirm(
            "Tem certeza que deseja excluir? Esta ação não pode ser desfeita."
          )
        ) {
          e.preventDefault();
        }
      });
    });
  }

  // Habilitar/desabilitar campo de justificativa baseado no checkbox de presença
  const presenceCheckboxes = document.querySelectorAll(
    'input[type="checkbox"][id^="presente_"]'
  );

  presenceCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", function () {
      const alunoId = this.id.split("_")[1];
      const justificativaField = document.getElementById(
        `justificativa_${alunoId}`
      );

      if (justificativaField) {
        justificativaField.disabled = this.checked;

        if (this.checked) {
          justificativaField.value = "";
        }
      }
    });
  });

  // Adicionar validação de formulário para campos de email
  const emailInputs = document.querySelectorAll('input[type="email"]');

  emailInputs.forEach((input) => {
    input.addEventListener("blur", function () {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/; // Regex para validar email

      if (!emailRegex.test(input.value) && input.value !== "") {
        input.setCustomValidity(
          "Por favor, insira um endereço de email válido."
        );
        input.style.borderColor = "#F44336"; // Cor de borda para indicar erro
      } else {
        input.setCustomValidity("");
        input.style.borderColor = ""; // Restaurar cor padrão
      }
    });
  });
});
