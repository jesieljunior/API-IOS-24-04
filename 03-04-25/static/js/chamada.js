document.addEventListener("DOMContentLoaded", function () {
  // Mostrar/ocultar campo de justificativa quando o checkbox for clicado
  const justifyCheckboxes = document.querySelectorAll(".justify-check");
  const faltaCheckboxes = document.querySelectorAll(".falta-check");

  faltaCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", function () {
      const alunoId = this.dataset.aluno;
      const justifyCheck = document.getElementById("justificar_" + alunoId);

      if (!this.checked) {
        // Se a falta for desmarcada, desmarcar também a justificativa
        justifyCheck.checked = false;
        document.getElementById("justify-field-" + alunoId).style.display =
          "none";
      }
    });
  });

  justifyCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", function () {
      const alunoId = this.dataset.aluno;
      const faltaCheck = document.getElementById("falta_" + alunoId);
      const justifyField = document.getElementById("justify-field-" + alunoId);

      if (this.checked) {
        // Se a justificativa for marcada, marcar também a falta
        faltaCheck.checked = true;
        justifyField.style.display = "block";
      } else {
        justifyField.style.display = "none";
      }
    });
  });
});
