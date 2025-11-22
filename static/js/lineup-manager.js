/*
 *   /static/js/lineup-manager.js - ENHANCED VERSION
 *   Quick wins: Better touch targets, visual feedback, haptics, improved subs
 */

class LineupManager {
  constructor(teamData) {
    this.teamData = teamData;
    this.teamType = teamData.team_type;
    this.teamId = teamData.team_id;
    this.canEdit = teamData.can_edit;
    this.saveUrl = teamData.saveUrl;
    this.formation = teamData.formation || "4-4-2";
    this.players = teamData.players || {};
    this.config = {
      mobileBreakpoint: 1280,
    };

    this.state = {
      starters: [...(teamData.starters || [])],
      substitutes: [...(teamData.substitutes || [])],
    };

    this.selectedPlayer = null;
    this.selectedSlot = null;
    this.isMobile = window.innerWidth < this.config.mobileBreakpoint;
    this.hasUnsavedChanges = false;
    this.sortableInstances = [];
    this.mobileModeInitialized = false;
    this.boundHandleTap = this.handleTap.bind(this);
    this.boundHandleModalTap = this.handleModalTap.bind(this);
    this.boundOpenModal = () => {
      this.openModal();
      this.vibrate([10]);
    };
    this.boundModalCloseHandlers = new Map();
    this.boundResizeHandler = this.handleResize.bind(this);
    this.toastHideTimeout = null;
    this.toastCleanupTimeout = null;
    this.resizeDebounceTimeout = null;

    if (!this.teamType || !this.teamId) {
      console.error("LineupManager: Missing required team data", teamData);
      return;
    }

    this.initElements();

    if (!this.panel || !this.pitchGrid) {
      console.error(
        `LineupManager: Could not find required DOM elements for team ${this.teamType}`
      );
      return;
    }

    this.renderAll();
    this.initCollapsibles();
    this.initPlayerSearch();

    if (this.canEdit) {
      this.initEventListeners();
      this.initResponsiveInteractions();
      window.addEventListener("resize", this.boundResizeHandler);
    }

    console.log(
      `LineupManager for ${this.teamType} initialized. Mobile: ${this.isMobile}`,
      {
        players: Object.keys(this.players).length,
        starters: this.state.starters.length,
        substitutes: this.state.substitutes.length,
      }
    );
  }

  initElements() {
    this.panel = document.querySelector(`[data-team-type="${this.teamType}"]`);
    if (!this.panel) {
      console.error(`Could not find team panel for ${this.teamType}`);
      return;
    }

    this.pitchGrid =
      this.panel.querySelector(`[data-pitch-grid="${this.teamType}"]`) ||
      this.panel.querySelector(`[data-pitch-grid]`);
    this.substitutesZone =
      this.panel.querySelector(`[data-substitutes-zone="${this.teamType}"]`) ||
      this.panel.querySelector(`[data-substitutes-zone]`);
    this.availableZone =
      this.panel.querySelector(`[data-available-zone="${this.teamType}"]`) ||
      this.panel.querySelector(`[data-available-zone]`);
    this.formationSelect =
      this.panel.querySelector(`[data-formation-select="${this.teamType}"]`) ||
      this.panel.querySelector(`[data-formation-select]`);
    this.saveBtn =
      this.panel.querySelector(`[data-save-btn="${this.teamType}"]`) ||
      this.panel.querySelector(`[data-save-btn]`);
    this.startersCountEl = this.panel.querySelector(
      `#starters-count-${this.teamType}`
    );
    this.substitutesCountEl = this.panel.querySelector(
      `#substitutes-count-${this.teamType}`
    );

    this.modal = document.getElementById(
      `available-players-modal-${this.teamType}`
    );
    this.modalTrigger = this.panel.querySelector(
      `[data-modal-trigger="available-players-modal-${this.teamType}"]`
    );
    this.modalAvailableZone = this.modal?.querySelector(
      "[data-available-zone-modal]"
    );
    this.addSubstituteBtn = this.panel.querySelector(
      `#add-substitute-${this.teamType}`
    );
  }

  initEventListeners() {
    this.formationSelect.addEventListener("change", (e) => {
      this.formation = e.target.value;
      this.renderPitch();
      this.updateState();
      this.vibrate([10]);
    });

    this.saveBtn.addEventListener("click", () => {
      this.saveLineup();
      this.vibrate([20]);
    });

    if (this.addSubstituteBtn) {
      this.addSubstituteBtn.addEventListener("click", (event) => {
        event.preventDefault();
        this.handleAddSubstituteSlot();
        this.vibrate([10]);
      });
    }
  }

  initResponsiveInteractions() {
    this.refreshModeInteractions();
  }

  refreshModeInteractions() {
    const shouldUseMobile = this.isViewportMobile();

    if (shouldUseMobile) {
      this.destroySortables();
      this.initMobileMode();
    } else {
      this.cleanupMobileMode();
      this.initDesktopMode();
    }
  }

  isViewportMobile() {
    const isMobile = window.innerWidth < this.config.mobileBreakpoint;
    this.isMobile = isMobile;
    return isMobile;
  }

  handleResize() {
    clearTimeout(this.resizeDebounceTimeout);
    this.resizeDebounceTimeout = setTimeout(() => {
      const shouldUseMobile = window.innerWidth < this.config.mobileBreakpoint;
      const modeChanged = shouldUseMobile !== this.isMobile;
      this.isMobile = shouldUseMobile;

      if (modeChanged) {
        this.renderAll();
      } else {
        this.refreshModeInteractions();
      }
    }, 200);
  }

  destroySortables() {
    if (this.sortableInstances.length === 0) return;
    this.sortableInstances.forEach((instance) => {
      if (instance && typeof instance.destroy === "function") {
        instance.destroy();
      }
    });
    this.sortableInstances = [];
  }

  initCollapsibles() {
    this.panel
      .querySelectorAll("[data-collapsible-section]")
      .forEach((section) => {
        const trigger = section.querySelector("[data-collapsible-trigger]");
        const content = section.querySelector("[data-collapsible-content]");
        const icon = section.querySelector("[data-collapsible-icon]");

        if (trigger && content) {
          trigger.addEventListener("click", () => {
            const isExpanding = content.classList.contains("hidden");
            content.classList.toggle("hidden");
            icon?.classList.toggle("rotate-180");
            this.vibrate([5]);

            if (isExpanding) {
              content.style.animation = "slideDown 0.3s ease-out";
            }
          });

          // Start with substitutes expanded on mobile
          if (
            this.isMobile &&
            section.querySelector("[data-substitutes-zone]")
          ) {
            content.classList.remove("hidden");
            icon?.classList.add("rotate-180");
          } else {
            content.classList.remove("hidden");
            icon?.classList.add("rotate-180");
          }
        }
      });
  }

  initPlayerSearch() {
    const searchInputs = this.panel.querySelectorAll(
      `[data-player-search="${this.teamType}"]`
    );
    const modalSearchInputs = this.modal
      ? this.modal.querySelectorAll(`[data-player-search="${this.teamType}"]`)
      : [];
    const allSearchInputs = [...searchInputs, ...modalSearchInputs];

    allSearchInputs.forEach((input) => {
      const newInput = input.cloneNode(true);
      input.parentNode.replaceChild(newInput, input);

      newInput.addEventListener("input", (e) => {
        const searchTerm = e.target.value.toLowerCase().trim();
        const isModalInput = this.modal && this.modal.contains(e.target);
        const searchZone = isModalInput
          ? this.modalAvailableZone
          : this.availableZone;

        if (!searchZone) return;

        const players = searchZone.querySelectorAll(
          ".player-card[data-player-id]"
        );
        let visibleCount = 0;

        players.forEach((card) => {
          const playerName = (
            card.dataset.playerName ||
            card.textContent ||
            ""
          ).toLowerCase();
          const matches = searchTerm === "" || playerName.includes(searchTerm);

          if (matches) {
            card.style.display = "";
            visibleCount++;
          } else {
            card.style.display = "none";
          }
        });

        let noResultsMsg = searchZone.querySelector(".no-search-results");
        if (visibleCount === 0 && searchTerm !== "") {
          if (!noResultsMsg) {
            noResultsMsg = document.createElement("div");
            noResultsMsg.className =
              "no-search-results text-gray-400 text-center py-4 col-span-full";
            noResultsMsg.textContent = "No players found";
            searchZone.appendChild(noResultsMsg);
          }
        } else if (noResultsMsg) {
          noResultsMsg.remove();
        }
      });
    });
  }

  initDesktopMode() {
    if (!this.pitchGrid || !this.substitutesZone || !this.availableZone) return;

    this.destroySortables();
    const commonSortableOptions = {
      group: `lineup-${this.teamType}`,
      animation: 150,
      ghostClass: "player-ghost",
      dragClass: "player-dragging",
      onEnd: () => this.updateState(),
    };

    this.pitchGrid.querySelectorAll(".pitch-position").forEach((pos) => {
      const sortableInstance = new Sortable(pos, {
        ...commonSortableOptions,
        filter: ".empty-player-placeholder",
        onAdd: (evt) => {
          const placeholder = evt.to.querySelector(".empty-player-placeholder");
          if (placeholder) {
            placeholder.remove();
          }
          this.updateState();
        },
      });
      this.sortableInstances.push(sortableInstance);
    });

    const substitutesSortable = new Sortable(
      this.substitutesZone,
      commonSortableOptions
    );
    const availableSortable = new Sortable(
      this.availableZone,
      commonSortableOptions
    );

    this.sortableInstances.push(substitutesSortable, availableSortable);
  }

  initMobileMode() {
    if (!this.panel || this.mobileModeInitialized) return;

    if (this.modalTrigger) {
      this.modalTrigger.addEventListener("click", this.boundOpenModal);
    }

    if (this.modal) {
      const closeButtons = this.modal.querySelectorAll("[data-modal-close]");
      closeButtons.forEach((btn) => {
        const handler = () => {
          this.closeModal();
          this.vibrate([10]);
        };
        btn.addEventListener("click", handler);
        this.boundModalCloseHandlers.set(btn, handler);
      });
    }

    this.panel.addEventListener("click", this.boundHandleTap);
    this.modal?.addEventListener("click", this.boundHandleModalTap);

    if (!localStorage.getItem(`lineup_tutorial_shown_${this.teamType}`)) {
      setTimeout(() => {
        this.showToast(
          "💡 Tip: Tap + to pick a player, or tap a player then tap where to move them",
          "info",
          4000
        );
        localStorage.setItem(`lineup_tutorial_shown_${this.teamType}`, "true");
      }, 1000);
    }

    this.mobileModeInitialized = true;
  }

  cleanupMobileMode() {
    if (!this.mobileModeInitialized || !this.panel) return;

    this.panel.removeEventListener("click", this.boundHandleTap);
    this.modal?.removeEventListener("click", this.boundHandleModalTap);

    if (this.modalTrigger) {
      this.modalTrigger.removeEventListener("click", this.boundOpenModal);
    }

    this.boundModalCloseHandlers.forEach((handler, button) => {
      button.removeEventListener("click", handler);
    });
    this.boundModalCloseHandlers.clear();

    this.mobileModeInitialized = false;
    this.closeModal();
  }

  openModal(slotMode = false) {
    if (!this.modal || !this.availableZone || !this.modalAvailableZone) return;

    this.syncModalWithAvailablePlayers();

    const searchInputs = this.modal.querySelectorAll(
      `[data-player-search="${this.teamType}"]`
    );
    searchInputs.forEach((input) => {
      input.value = "";
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });

    if (slotMode && this.selectedSlot) {
      const modalHeader = this.modal.querySelector("h3");
      const headerParent = modalHeader?.parentElement;

      if (modalHeader) {
        const slotType =
          this.selectedSlot.type === "pitch"
            ? "Starting Position"
            : "Substitute Bench";
        const icon = this.selectedSlot.type === "pitch" ? "⚽" : "🔄";

        modalHeader.innerHTML = `
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-full flex items-center justify-center text-2xl shadow-lg">
              ${icon}
            </div>
            <div>
              <div class="text-xl font-bold text-white">Select Player</div>
              <div class="text-sm text-gray-400">For: ${slotType}</div>
            </div>
          </div>
        `;
      }

      const existingSubtitle = this.modal.querySelector(
        ".slot-picker-subtitle"
      );
      if (existingSubtitle) existingSubtitle.remove();

      const subtitle = document.createElement("p");
      subtitle.className =
        "text-sm text-gray-400 mt-2 slot-picker-subtitle px-4";
      subtitle.textContent =
        this.selectedSlot.type === "bench"
          ? "👆 Tap any player below to add them to your substitutes bench"
          : "👆 Tap a player to assign them to this position";
      headerParent?.appendChild(subtitle);
    }

    this.modal.classList.remove("hidden");
    this.modal.style.animation = "fadeIn 0.2s ease-out";
  }

  closeModal() {
    if (!this.modal) return;
    this.modal.classList.add("hidden");
    this.clearSlotSelection();
    this.resetModalHeader();
  }

  resetModalHeader() {
    if (!this.modal) return;
    const modalHeader = this.modal.querySelector("h3");
    if (modalHeader) {
      modalHeader.textContent = "Available Players";
    }
    const subtitle = this.modal.querySelector(".slot-picker-subtitle");
    if (subtitle) subtitle.remove();
  }

  syncModalWithAvailablePlayers() {
    if (!this.modalAvailableZone || !this.availableZone) return;

    this.renderAvailable();
    this.modalAvailableZone.innerHTML = "";
    const availablePlayers = Array.from(
      this.availableZone.querySelectorAll(".player-card[data-player-id]")
    );

    availablePlayers.forEach((playerNode) => {
      const clone = playerNode.cloneNode(true);
      clone.style.display = "";
      clone.classList.add(
        "hover:scale-105",
        "active:scale-95",
        "transition-transform",
        "duration-200",
        "cursor-pointer"
      );
      clone.dataset.playerId = playerNode.dataset.playerId;
      clone.dataset.playerName = playerNode.dataset.playerName;
      this.modalAvailableZone.appendChild(clone);
    });
  }

  handleTap(e) {
    const emptySlot = e.target.closest(".empty-player-placeholder");
    const player = e.target.closest(".player-card");
    const pitchPosition = e.target.closest(".pitch-position");
    const subsZone = e.target.closest("[data-substitutes-zone]");

    if (!this.canEdit) return;
    if (!this.isMobile) return;

    if (emptySlot) {
      e.stopPropagation();
      this.handleEmptySlotTap(emptySlot);
      this.vibrate([15]);
      return;
    }

    if (this.selectedPlayer && (pitchPosition || subsZone)) {
      e.stopPropagation();
      this.handleDestinationTap(pitchPosition || subsZone);
      this.vibrate([10, 50, 10]);
      return;
    }

    if (player) {
      e.stopPropagation();
      this.handlePlayerTap(player);
      this.vibrate([10]);
      return;
    }

    if (subsZone && !player) {
      e.stopPropagation();
      this.handleBenchZoneTap(subsZone);
      this.vibrate([10]);
      return;
    }
  }

  handleModalTap(e) {
    if (!this.isMobile) return;

    const player = e.target.closest(".player-card");

    if (player && this.selectedSlot) {
      e.stopPropagation();
      this.handleSlotPlayerSelection(player);
      this.vibrate([10, 50, 10]);
    }
  }

  handleEmptySlotTap(emptyElement) {
    if (this.selectedPlayer) {
      const position = emptyElement.closest(".pitch-position");
      if (position) {
        this.handleDestinationTap(position);
      }
      return;
    }

    const pitchPosition = emptyElement.closest(".pitch-position");
    const isSubsZone = emptyElement.closest("[data-substitutes-zone]");

    this.selectedSlot = {
      element: pitchPosition || isSubsZone || emptyElement.parentElement,
      type: pitchPosition ? "pitch" : "bench",
      emptyPlaceholder: emptyElement,
    };

    this.selectedSlot.element.classList.add(
      "slot-selected",
      "ring-4",
      "ring-yellow-400"
    );
    emptyElement.classList.add("animate-pulse", "scale-110");

    this.openModal(true);
    this.showToast("👆 Select a player from the list", "info");
  }

  handleSlotPlayerSelection(playerCard) {
    if (!this.selectedSlot) return;

    const playerId = playerCard.dataset.playerId;
    if (!playerId) return;

    const originalPlayerCard = this.availableZone.querySelector(
      `.player-card[data-player-id="${playerId}"]`
    );

    if (!originalPlayerCard) {
      this.showToast("Player not found", "error");
      return;
    }

    const existingPlayerInSlot =
      this.selectedSlot.element.querySelector(".player-card");

    if (this.selectedSlot.type === "pitch") {
      this.selectedSlot.element.innerHTML = "";
      this.selectedSlot.element.appendChild(originalPlayerCard);

      if (existingPlayerInSlot && existingPlayerInSlot !== originalPlayerCard) {
        this.availableZone.appendChild(existingPlayerInSlot);
      }
    } else {
      const added = this.addPlayerToBench(playerId);
      if (!added) {
        return;
      }
    }

    this.updateState();
    this.clearSlotSelection();
    this.closeModal();
    this.showToast("✅ Player assigned!", "success");
  }

  clearSlotSelection() {
    if (this.selectedSlot) {
      this.selectedSlot.element.classList.remove(
        "slot-selected",
        "ring-4",
        "ring-yellow-400"
      );

      const emptyPlaceholder = this.selectedSlot.element.querySelector(
        ".empty-player-placeholder"
      );
      if (emptyPlaceholder) {
        emptyPlaceholder.classList.remove("animate-pulse", "scale-110");
      }
    }
    this.selectedSlot = null;
  }

  handlePlayerTap(playerElement) {
    const playerId = playerElement.dataset.playerId;
    if (!playerId) return;

    if (this.selectedPlayer && this.selectedPlayer.id === playerId) {
      this.deselectPlayer();
    } else {
      this.deselectPlayer();
      this.selectedPlayer = {
        id: playerId,
        element: playerElement,
        sourceContainer: playerElement.parentElement,
      };
      playerElement.classList.add(
        "player-selected",
        "ring-4",
        "ring-blue-500",
        "scale-110",
        "z-50"
      );

      document
        .querySelectorAll(".pitch-position, [data-substitutes-zone]")
        .forEach((el) => {
          el.classList.add("destination-available");
        });

      this.showToast("👆 Tap where to move this player", "info");
    }
  }

  handleDestinationTap(destinationElement) {
    if (!this.selectedPlayer) return;

    const sourceElement = this.selectedPlayer.sourceContainer;

    const playerElement = this.selectedPlayer.element;

    // Don't do anything if tapping on the same spot

    if (destinationElement === sourceElement) {
      this.deselectPlayer();

      return;
    }

    const isDestPitch = destinationElement.classList.contains("pitch-position");

    const isDestSubs = destinationElement.hasAttribute("data-substitutes-zone");

    if (isDestPitch) {
      const existingPlayerEl = destinationElement.querySelector(".player-card");

      if (existingPlayerEl) {
        // Swapping players

        sourceElement.appendChild(existingPlayerEl);

        destinationElement.appendChild(playerElement);
      } else {
        // Moving to empty pitch slot
        destinationElement.innerHTML = "";
        destinationElement.appendChild(playerElement);

        if (sourceElement.classList.contains("pitch-position")) {
          sourceElement.innerHTML = this.createEmptyPlaceholder();
        }
      }
    } else if (isDestSubs) {
      // Moving to subs

      const existing = destinationElement.querySelector(
        `.player-card[data-player-id="${this.selectedPlayer.id}"]`
      );

      if (existing) {
        this.showToast("⚠️ Player already on the bench", "warning");

        return;
      }

      destinationElement.appendChild(playerElement);

      if (sourceElement.classList.contains("pitch-position")) {
        sourceElement.innerHTML = this.createEmptyPlaceholder();
      }
    }

    this.updateState();

    this.deselectPlayer();

    this.showToast("✅ Player moved!", "success");
  }
  deselectPlayer() {
    document.querySelectorAll(".player-selected").forEach((el) => {
      el.classList.remove(
        "player-selected",
        "ring-4",
        "ring-blue-500",
        "scale-110",
        "z-50"
      );
    });

    document.querySelectorAll(".destination-available").forEach((el) => {
      el.classList.remove("destination-available");
    });

    this.selectedPlayer = null;
  }

  updateState(newState, options = {}) {
    const { suppressDirty = false } = options;

    if (newState) {
      this.state.starters = newState.starters.map((id) => String(id));
      this.state.substitutes = newState.substitutes.map((id) => String(id));
      this.renderAll();
    } else {
      this.state.starters = Array.from(
        this.pitchGrid.querySelectorAll(".player-card[data-player-id]")
      ).map((el) => el.dataset.playerId);
      this.state.substitutes = Array.from(
        this.substitutesZone.querySelectorAll(".player-card[data-player-id]")
      ).map((el) => el.dataset.playerId);
      this.updateCounts();
    }

    if (suppressDirty) {
      this.hasUnsavedChanges = false;
      this.clearSaveButtonDirty();
    } else {
      this.hasUnsavedChanges = true;
      this.markSaveButtonDirty();
    }
  }
  renderAll() {
    this.renderPitch();
    this.renderSubstitutes();
    this.renderAvailable();
    this.updateCounts();
    if (this.canEdit) {
      this.refreshModeInteractions();
    }
  }

  renderPitch() {
    this.pitchGrid.innerHTML = "";
    const formationLayout = this.getFormationLayout(this.formation);
    let startersToPlace = [...this.state.starters];

    // Add formation badge
    const formationBadge = document.createElement("div");
    formationBadge.className = "formation-badge";
    formationBadge.textContent = this.formation;
    this.pitchGrid.appendChild(formationBadge);

    formationLayout.reverse().forEach((row, index) => {
      const rowDiv = document.createElement("div");
      rowDiv.className =
        "pitch-row relative grid w-full place-items-center gap-4";
      const count = row[0] || 1;
      rowDiv.style.gridTemplateColumns = `repeat(${count}, minmax(0, 1fr))`;
      rowDiv.dataset.playerCount = count;

      // Add position zone label
      const zoneLabel = this.getZoneLabel(
        formationLayout.length - 1 - index,
        formationLayout.length
      );
      if (zoneLabel) {
        const label = document.createElement("div");
        label.className = "position-zone-label";
        label.textContent = zoneLabel;
        rowDiv.appendChild(label);
      }

      for (let i = 0; i < count; i++) {
        const positionDiv = document.createElement("div");
        positionDiv.className =
          "pitch-position relative flex justify-center items-center transition-all duration-200 w-full mx-auto";
        positionDiv.style.minWidth = "0";

        const starterId = startersToPlace.shift();
        const playerCard = starterId ? this.createPlayerCard(starterId) : null;

        if (playerCard) {
          positionDiv.appendChild(playerCard);
        } else {
          positionDiv.innerHTML = this.createEmptyPlaceholder();
        }
        rowDiv.appendChild(positionDiv);
      }
      this.pitchGrid.appendChild(rowDiv);
    });
  }

  getZoneLabel(rowIndex, totalRows) {
    if (rowIndex === 0) return "GK";
    if (rowIndex === totalRows - 1) return "FWD";
    if (rowIndex === 1) return "DEF";
    if (rowIndex === totalRows - 2) return "MID";
    return "";
  }

  renderSubstitutes() {
    this.substitutesZone.innerHTML = "";

    if (this.state.substitutes.length === 0 && this.isMobile) {
      const emptyState = this.createSubstitutesEmptyState();
      this.substitutesZone.appendChild(emptyState);
    } else {
      this.state.substitutes.forEach((playerId) => {
        const card = this.createPlayerCard(playerId);
        if (card) {
          this.substitutesZone.appendChild(card);
        }
      });
    }
  }

  createSubstitutesEmptyState() {
    const container = document.createElement("div");
    container.className =
      "empty-subs-state col-span-full flex flex-col items-center justify-center py-8 px-4";
    container.innerHTML = `
      <div class="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mb-4 shadow-lg">
        <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
        </svg>
      </div>
      <p class="text-lg font-bold text-white mb-2">No Substitutes Yet</p>
      <p class="text-sm text-gray-400 text-center mb-4">Build your bench by adding substitute players</p>
      <button type="button" class="add-sub-from-empty bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold py-3 px-6 rounded-lg shadow-lg transition-all duration-200 flex items-center gap-2 active:scale-95">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
        </svg>
        Add First Substitute
      </button>
    `;

    const addBtn = container.querySelector(".add-sub-from-empty");
    addBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.handleBenchZoneTap(this.substitutesZone, { forceModal: true });
      this.vibrate([10]);
    });

    return container;
  }

  renderAvailable() {
    this.availableZone.innerHTML = "";
    const onFieldIds = new Set([
      ...this.state.starters,
      ...this.state.substitutes,
    ]);
    const availableIds = Object.keys(this.players).filter(
      (id) => !onFieldIds.has(id)
    );

    if (availableIds.length === 0) {
      const emptyMsg = document.createElement("div");
      emptyMsg.className = "col-span-full text-center py-8 text-gray-400";
      emptyMsg.innerHTML = `
        <svg class="w-12 h-12 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
        <p class="font-semibold">All players assigned!</p>
        <p class="text-sm">Great job building your lineup</p>
      `;
      this.availableZone.appendChild(emptyMsg);
    } else {
      availableIds.forEach((playerId) => {
        this.availableZone.appendChild(this.createPlayerCard(playerId));
      });
    }
  }

  createPlayerCard(playerId) {
    const player = this.players[playerId];
    if (!player) return null;

    // Ensure the card fills its container
    const card = document.createElement("div");
    card.className =
      "player-card w-full h-full flex flex-col justify-center items-center cursor-pointer bg-gray-800 rounded-lg p-1 text-center shadow-lg border-2 border-transparent hover:border-blue-500 transition-all duration-200 active:scale-95";
    card.dataset.playerId = playerId;
    card.dataset.playerName = player.name;

    // Using w-10 h-10 for mobile, lg:w-16 lg:h-16 for desktop
    card.innerHTML = `
    <div class="relative inline-block mb-1 lg:mb-2 pointer-events-none">
      <img src="${player.photo_url || "/static/images/default-avatar.png"}" 
           alt="${player.name}" 
           class="w-10 h-10 lg:w-16 lg:h-16 rounded-full mx-auto object-cover border-2 border-gray-600" 
           onerror="this.src='/static/images/default-avatar.png'">
    </div>
    <p class="text-white font-semibold text-xs break-words pointer-events-none px-1 leading-tight">${
      player.name
    }</p>
    <p class="text-gray-400 text-[9px] lg:text-xs font-medium pointer-events-none">${
      player.position
    }</p>
  `;
    return card;
  }

  createEmptyPlaceholder() {
    return `<div class="empty-player-placeholder w-full h-full rounded-lg border-2 border-dashed border-gray-500 
               opacity-70 flex items-center justify-center cursor-pointer hover:border-blue-400 
               hover:opacity-100 hover:bg-blue-500 hover:bg-opacity-10 transition-all duration-200 
               active:scale-95 relative group"
               data-empty-slot="true">
            <span class="text-gray-400 text-2xl lg:text-4xl font-thin pointer-events-none group-hover:text-blue-400 transition-colors">+</span>
            <span class="absolute bottom-1 left-1/2 -translate-x-1/2 text-[8px] lg:text-[10px] text-gray-500 whitespace-nowrap pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity">Tap to add</span>
          </div>`;
  }

  handleAddSubstituteSlot() {
    if (!this.canEdit || !this.substitutesZone) return;
    this.handleBenchZoneTap(this.substitutesZone, { forceModal: true });
  }

  handleBenchZoneTap(subsZone, { forceModal = false } = {}) {
    if (!subsZone || !this.canEdit) return;

    if (this.selectedPlayer) {
      this.handleDestinationTap(subsZone);
      return;
    }

    if (this.selectedSlot && this.selectedSlot.element !== subsZone) {
      this.clearSlotSelection();
    }

    this.selectedSlot = {
      element: subsZone,
      type: "bench",
      emptyPlaceholder: null,
    };

    subsZone.classList.add("slot-selected", "ring-4", "ring-yellow-400");

    if (this.isMobile || forceModal) {
      this.openModal(true);
      this.showToast("👆 Select players to add to your bench", "info");
    } else {
      this.showToast("Drag a player here or tap a player to move them", "info");
      setTimeout(() => this.clearSlotSelection(), 700);
    }
  }

  addPlayerToBench(playerId) {
    if (!this.canEdit) return false;

    if (!this.players[playerId]) {
      this.showToast("Player data not found", "error");
      return false;
    }

    if (this.state.substitutes.includes(playerId)) {
      this.showToast("⚠️ Player already on the bench", "warning");
      return false;
    }

    if (this.state.starters.includes(playerId)) {
      this.showToast("⚠️ Player is already in the starting lineup", "warning");
      return false;
    }

    if (this.state.substitutes.length >= 12) {
      this.showToast("⚠️ Maximum 12 substitutes allowed", "warning");
      return false;
    }

    const newSubstitutes = [...this.state.substitutes, playerId];
    this.updateState({
      starters: this.state.starters,
      substitutes: newSubstitutes,
    });

    return true;
  }

  updateCounts() {
    this.startersCountEl.textContent = this.state.starters.length;
    this.substitutesCountEl.textContent = this.state.substitutes.length;

    // Visual feedback for starter count
    if (this.state.starters.length === 11) {
      this.startersCountEl.classList.add("text-green-400");
      this.startersCountEl.classList.remove("text-yellow-400", "text-red-400");
    } else if (this.state.starters.length > 11) {
      this.startersCountEl.classList.add("text-red-400");
      this.startersCountEl.classList.remove(
        "text-green-400",
        "text-yellow-400"
      );
    } else {
      this.startersCountEl.classList.add("text-yellow-400");
      this.startersCountEl.classList.remove("text-green-400", "text-red-400");
    }
  }
  getFormationLayout(formation) {
    const layouts = {
      "4-4-2": [[1], [4], [4], [2]],
      "4-3-3": [[1], [4], [3], [3]],
      "3-5-2": [[1], [3], [5], [2]],
      "4-2-3-1": [[1], [4], [2], [3], [1]],
      "5-3-2": [[1], [5], [3], [2]],
      "3-4-3": [[1], [3], [4], [3]],
      "4-5-1": [[1], [4], [5], [1]],
      "5-4-1": [[1], [5], [4], [1]],
    };
    return layouts[formation] || [[1], [4], [4], [2]];
  }

  markSaveButtonDirty() {
    if (!this.saveBtn) return;

    this.saveBtn.disabled = false;
    const saveText = this.saveBtn.querySelector("[data-save-text]");
    if (saveText && this.hasUnsavedChanges) {
      saveText.innerHTML =
        '<span class="flex items-center gap-2"><span class="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></span>Save Changes</span>';
    }
  }

  clearSaveButtonDirty() {
    if (!this.saveBtn) return;

    this.saveBtn.disabled = true;
    const saveText = this.saveBtn.querySelector("[data-save-text]");
    if (saveText) {
      saveText.textContent = "Save Lineup";
    }
  }

  async saveLineup() {
    if (!this.saveBtn) return;

    this.saveBtn.disabled = true;
    const saveText = this.saveBtn.querySelector("[data-save-text]");
    const originalText = saveText ? saveText.textContent : "Save Lineup";
    if (saveText) {
      saveText.textContent = "Saving...";
    }

    const csrfToken =
      this.getCookie("csrftoken") ||
      document.querySelector('input[name="csrfmiddlewaretoken"]')?.value;

    if (!csrfToken) {
      console.error("CSRF token not found!");
      this.showToast("🛑 Security token not found. Please refresh.", "error");
      this.saveBtn.disabled = false;
      if (saveText) {
        saveText.textContent = originalText;
      }
      return;
    }

    // Validation before saving
    if (this.state.starters.length !== 11) {
      this.showToast(
        `⚠️ Need exactly 11 starters (currently ${this.state.starters.length})`,
        "warning",
        3000
      );
      this.saveBtn.disabled = false;
      if (saveText) {
        saveText.textContent = originalText;
      }
      return;
    }

    const lineupData = {
      team_id: parseInt(this.teamId),
      formation: this.formation,
      starters: this.state.starters
        .map((id) => parseInt(id))
        .filter((id) => !isNaN(id)),
      substitutes: this.state.substitutes
        .map((id) => parseInt(id))
        .filter((id) => !isNaN(id)),
    };

    try {
      const response = await fetch(this.saveUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify(lineupData),
      });

      const result = await response.json();

      if (!response.ok) {
        const errorMessage =
          result.message ||
          result.error ||
          `Server responded with status: ${response.status}`;
        throw new Error(errorMessage);
      }

      if (result.status === "success") {
        this.showToast("✅ Lineup saved successfully!", "success", 3000);

        if (result.data) {
          this.updateState(
            {
              starters: result.data.starters.map((p) => String(p.id)),
              substitutes: result.data.substitutes.map((p) => String(p.id)),
            },
            { suppressDirty: true }
          );
        } else {
          this.updateState(null, { suppressDirty: true });
        }
      } else {
        throw new Error(
          result.message || result.error || "An unknown error occurred."
        );
      }
    } catch (error) {
      console.error("Failed to save lineup:", error);
      this.showToast(`🛑 Error: ${error.message}`, "error", 4000);
      this.saveBtn.disabled = false;
      if (saveText) {
        saveText.textContent = originalText;
      }
    }
  }

  getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  vibrate(pattern = [10]) {
    if ("vibrate" in navigator) {
      navigator.vibrate(pattern);
    }
  }

  showToast(message, type = "info", duration = 3000) {
    const toast = document.getElementById("toast");
    const toastMessage = document.getElementById("toast-message");
    const toastIcon = document.getElementById("toast-icon");

    if (!toast || !toastMessage || !toastIcon) return;

    clearTimeout(this.toastHideTimeout);
    clearTimeout(this.toastCleanupTimeout);

    toastMessage.textContent = message;

    const icons = {
      success: `<svg class="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`,
      error: `<svg class="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`,
      warning: `<svg class="w-6 h-6 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>`,
      info: `<svg class="w-6 h-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`,
    };
    toastIcon.innerHTML = icons[type] || icons["info"];

    toast.classList.remove("hidden", "translate-x-full");
    toast.classList.add("toast-show", "translate-x-0");

    this.toastHideTimeout = setTimeout(() => {
      toast.classList.remove("translate-x-0");
      toast.classList.add("translate-x-full");
      toast.classList.remove("toast-show");

      this.toastCleanupTimeout = setTimeout(() => {
        if (toast.parentElement) {
          toast.parentElement.removeChild(toast);
        }
      }, 350);
    }, duration);
  }
}
