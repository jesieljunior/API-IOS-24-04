document.addEventListener("DOMContentLoaded", function () {
  // Elementos do DOM
  const sidebar = document.querySelector(".sidebar");
  const mainContent = document.querySelector(".main-content");
  const toggleBtn = document.querySelector(".toggle-sidebar");
  const mobileToggle = document.querySelector(".mobile-menu-toggle");
  const overlay = document.querySelector(".sidebar-overlay");
  const dropdownToggles = document.querySelectorAll(".dropdown-toggle");
  const menuItems = document.querySelectorAll(".menu-item");
  const closeAlertBtns = document.querySelectorAll(".close-alert");

  // Toggle sidebar no desktop
  if (toggleBtn) {
    toggleBtn.addEventListener("click", function (e) {
      // Prevenir comportamento padrão para garantir controle total
      e.preventDefault();

      sidebar.classList.toggle("collapsed");
      mainContent.classList.toggle("expanded");

      // Guardar o estado no localStorage de forma segura
      try {
        const isCollapsed = sidebar.classList.contains("collapsed");
        localStorage.setItem("sidebarCollapsed", isCollapsed);
      } catch (err) {
        console.error("Erro ao salvar estado do sidebar:", err);
      }
    });
  }

  // Toggle sidebar no mobile com tratamento de erros
  if (mobileToggle) {
    mobileToggle.addEventListener("click", function (e) {
      e.preventDefault();

      try {
        sidebar.classList.toggle("mobile-show");
        overlay.classList.toggle("show");

        // Previnir scroll no body quando o menu está aberto
        if (sidebar.classList.contains("mobile-show")) {
          document.body.style.overflow = "hidden";
        } else {
          document.body.style.overflow = "";
        }
      } catch (err) {
        console.error("Erro ao alternar sidebar móvel:", err);
      }
    });
  }

  // Fechar sidebar no mobile ao clicar no overlay
  if (overlay) {
    overlay.addEventListener("click", function () {
      try {
        sidebar.classList.remove("mobile-show");
        overlay.classList.remove("show");
        document.body.style.overflow = "";
      } catch (err) {
        console.error("Erro ao fechar sidebar:", err);
      }
    });
  }

  // Dropdown submenus com tratamento de erros
  if (dropdownToggles && dropdownToggles.length > 0) {
    dropdownToggles.forEach((toggle) => {
      toggle.addEventListener("click", function (e) {
        e.preventDefault();

        try {
          // Encontrar o dropdown relacionado a este toggle
          const dropdownId = this.getAttribute("data-dropdown");
          const dropdown = document.getElementById(dropdownId);

          if (!dropdown) return;

          // Fechar outros dropdowns abertos
          document
            .querySelectorAll(".menu-dropdown.show")
            .forEach((openDropdown) => {
              if (openDropdown !== dropdown) {
                openDropdown.classList.remove("show");

                // Resetar o ícone do dropdown
                const relatedToggle = document.querySelector(
                  `[data-dropdown="${openDropdown.id}"]`
                );
                if (relatedToggle) {
                  const icon = relatedToggle.querySelector(".dropdown-icon");
                  if (icon) {
                    icon.classList.remove("fa-chevron-down");
                    icon.classList.add("fa-chevron-right");
                  }
                  relatedToggle.setAttribute("aria-expanded", "false");
                }
              }
            });

          // Alternar a visibilidade do dropdown
          dropdown.classList.toggle("show");

          // Alternar o ícone do dropdown
          const icon = this.querySelector(".dropdown-icon");
          if (icon) {
            icon.classList.toggle("fa-chevron-down");
            icon.classList.toggle("fa-chevron-right");
          }

          // Atualizar aria-expanded para acessibilidade
          const isExpanded = dropdown.classList.contains("show");
          this.setAttribute("aria-expanded", isExpanded ? "true" : "false");
        } catch (err) {
          console.error("Erro ao manipular dropdown:", err);
        }
      });
    });
  }

  // Fechar alertas com tratamento de erros
  if (closeAlertBtns && closeAlertBtns.length > 0) {
    closeAlertBtns.forEach((btn) => {
      btn.addEventListener("click", function (e) {
        e.preventDefault();

        try {
          const alert = this.closest(".alert");
          if (alert) {
            alert.style.opacity = "0";
            setTimeout(() => {
              alert.style.display = "none";
            }, 300);
          }
        } catch (err) {
          console.error("Erro ao fechar alerta:", err);
        }
      });
    });
  }

  // Marcar item de menu ativo baseado na URL atual
  if (menuItems.length > 0) {
    const currentPath = window.location.pathname;

    menuItems.forEach((item) => {
      const itemPath = item.getAttribute("href");
      if (itemPath && currentPath.includes(itemPath) && itemPath !== "#") {
        item.classList.add("active");

        // Se for um submenu, abrir o menu pai
        const parentDropdown = item.closest(".menu-dropdown");
        if (parentDropdown) {
          parentDropdown.classList.add("show");

          // Atualizar ícone do dropdown
          const parentToggle = document.querySelector(
            `[data-dropdown="${parentDropdown.id}"]`
          );
          if (parentToggle) {
            const icon = parentToggle.querySelector(".dropdown-icon");
            if (icon) {
              icon.classList.remove("fa-chevron-right");
              icon.classList.add("fa-chevron-down");
            }
            parentToggle.setAttribute("aria-expanded", "true");
          }
        }
      }
    });

    // Para URLs de submenu
    document.querySelectorAll(".submenu-item").forEach((submenuItem) => {
      const itemPath = submenuItem.getAttribute("href");
      if (itemPath && currentPath === itemPath) {
        submenuItem.style.color = "var(--text-light)";
        submenuItem.style.fontWeight = "bold";

        // Ativar o dropdown pai
        const parentDropdown = submenuItem.closest(".menu-dropdown");
        if (parentDropdown) {
          parentDropdown.classList.add("show");

          const parentToggle = document.querySelector(
            `[data-dropdown="${parentDropdown.id}"]`
          );
          if (parentToggle) {
            parentToggle.classList.add("active");
            const icon = parentToggle.querySelector(".dropdown-icon");
            if (icon) {
              icon.classList.remove("fa-chevron-right");
              icon.classList.add("fa-chevron-down");
            }
            parentToggle.setAttribute("aria-expanded", "true");
          }
        }
      }
    });
  }

  // Restaurar estado do sidebar com verificações de segurança
  try {
    const isCollapsed = localStorage.getItem("sidebarCollapsed") === "true";
    if (isCollapsed && window.innerWidth > 768 && sidebar) {
      sidebar.classList.add("collapsed");
      if (mainContent) mainContent.classList.add("expanded");
    }
  } catch (err) {
    console.error("Erro ao restaurar estado do sidebar:", err);
    // Caso falhe ao ler localStorage, não fazemos nada
  }

  // Ajustar ao redimensionar a janela
  window.addEventListener("resize", function () {
    if (window.innerWidth <= 768) {
      sidebar.classList.remove("collapsed");
      mainContent.classList.remove("expanded");
    } else {
      sidebar.classList.remove("mobile-show");
      overlay.classList.remove("show");
      document.body.style.overflow = "";

      // Restaurar estado salvo em telas maiores
      const shouldBeCollapsed =
        localStorage.getItem("sidebarCollapsed") === "true";
      if (shouldBeCollapsed) {
        sidebar.classList.add("collapsed");
        mainContent.classList.add("expanded");
      }
    }
  });
});
