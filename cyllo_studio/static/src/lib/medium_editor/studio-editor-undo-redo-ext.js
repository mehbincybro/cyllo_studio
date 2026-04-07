// undo_redo_manager.js

/**
 * UndoRedoManager - Universal undo/redo library for any HTML element
 * Works standalone or with Medium Editor, Dragula, and other libraries
 *
 * @example
 * const undoManager = new UndoRedoManager('#my-editor');
 * undoManager.startTracking();
 */
class UndoRedoManager {
  constructor(elementSelector, options = {}) {
    // Get the element
    this.editor = typeof elementSelector === 'string'
      ? document.querySelector(elementSelector)
      : elementSelector;

    if (!this.editor) {
      throw new Error('UndoRedoManager: Element not found');
    }

    // Configuration
    this.maxStackSize = options.maxStackSize || 50;
    this.debounceTime = options.debounceTime || 500;
    this.autoTrack = options.autoTrack !== false; // Default true
    this.trackAttributes = options.trackAttributes !== false; // Default true
    this.keyboardShortcuts = options.keyboardShortcuts !== false; // Default true

    // State management
    this.undoStack = [];
    this.redoStack = [];
    this.debounceTimer = null;
    this.isRestoring = false;
    this.observers = [];
    this.eventListeners = [];

    // Save initial state
    this.saveState();

    // Auto-start tracking if enabled
    if (this.autoTrack) {
      this.startTracking();
    }
  }

  /**
   * Capture current state of the editor
   */
  getCurrentState() {
    return {
      html: this.editor.innerHTML,
      timestamp: Date.now()
    };
  }

  /**
   * Save state to undo stack
   */
  saveState() {
    if (this.isRestoring) return;

    const currentState = this.getCurrentState();

    // Don't save if nothing changed
    if (this.undoStack.length > 0) {
      const lastState = this.undoStack[this.undoStack.length - 1];
      if (lastState.html === currentState.html) return;
    }

    this.undoStack.push(currentState);

    // Clear redo stack when new action is performed
    this.redoStack = [];

    // Limit stack size
    if (this.undoStack.length > this.maxStackSize) {
      this.undoStack.shift();
    }

    this.updateUI();
    this.triggerEvent('stateChanged', { canUndo: this.canUndo(), canRedo: this.canRedo() });
  }

  /**
   * Debounced save (for rapid changes)
   */
  debouncedSave() {
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      this.saveState();
    }, this.debounceTime);
  }

  /**
   * Undo last action
   */
  undo() {
    if (this.undoStack.length <= 1) return false;

    this.isRestoring = true;

    const currentState = this.undoStack.pop();
    this.redoStack.push(currentState);

    const previousState = this.undoStack[this.undoStack.length - 1];
    this.restoreState(previousState);

    this.isRestoring = false;
    this.updateUI();
    this.triggerEvent('undo', { state: previousState });

    return true;
  }

  /**
   * Redo last undone action
   */
  redo() {
    if (this.redoStack.length === 0) return false;

    this.isRestoring = true;

    const nextState = this.redoStack.pop();
    this.undoStack.push(nextState);
    this.restoreState(nextState);

    this.isRestoring = false;
    this.updateUI();
    this.triggerEvent('redo', { state: nextState });

    return true;
  }

  /**
   * Restore editor to a previous state
   */
  restoreState(state) {
    this.editor.innerHTML = state.html;
    this.triggerEvent('restored', { state });
  }

  /**
   * Check if can undo
   */
  canUndo() {
    return this.undoStack.length > 1;
  }

  /**
   * Check if can redo
   */
  canRedo() {
    return this.redoStack.length > 0;
  }

  /**
   * Start automatic tracking of changes
   */
  startTracking() {
    this.stopTracking(); // Clean up any existing tracking

    // Track input events (typing, paste, etc.)
    const inputHandler = () => this.debouncedSave();
    this.editor.addEventListener('input', inputHandler);
    this.eventListeners.push({ element: this.editor, event: 'input', handler: inputHandler });

    // Track attribute changes if enabled
    if (this.trackAttributes) {
      const observer = new MutationObserver((mutations) => {
        if (this.isRestoring) return;

        let shouldSave = false;
        for (const mutation of mutations) {
          if (mutation.type === 'childList' || mutation.type === 'attributes') {
            shouldSave = true;
            break;
          }
        }

        if (shouldSave) {
          this.debouncedSave();
        }
      });

      observer.observe(this.editor, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeOldValue: true
      });

      this.observers.push(observer);
    }

    // Setup keyboard shortcuts if enabled
    if (this.keyboardShortcuts) {
      this.setupKeyboardShortcuts();
    }

    // Setup buttons if they exist
    this.setupButtons();

    return this;
  }

  /**
   * Stop tracking changes
   */
  stopTracking() {
    // Remove event listeners
    this.eventListeners.forEach(({ element, event, handler }) => {
      element.removeEventListener(event, handler);
    });
    this.eventListeners = [];

    // Disconnect observers
    this.observers.forEach(observer => observer.disconnect());
    this.observers = [];

    return this;
  }

  /**
   * Setup keyboard shortcuts
   */
  setupKeyboardShortcuts() {
    const keyHandler = (e) => {
      // Only trigger if the editor or its children are focused
      if (!this.editor.contains(document.activeElement)) return;

      // Ctrl+Z or Cmd+Z (Undo)
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === 'z') {
        e.preventDefault();
        this.undo();
      }
      // Ctrl+Y or Ctrl+Shift+Z or Cmd+Shift+Z (Redo)
      else if ((e.ctrlKey || e.metaKey) && (e.shiftKey && e.key === 'z' || e.key === 'y')) {
        e.preventDefault();
        this.redo();
      }
    };

    document.addEventListener('keydown', keyHandler);
    this.eventListeners.push({ element: document, event: 'keydown', handler: keyHandler });
  }

  /**
   * Setup undo/redo buttons (if they exist in the DOM)
   */
  setupButtons() {
    const undoBtn = document.querySelector('[data-undo]');
    const redoBtn = document.querySelector('[data-redo]');

    if (undoBtn) {
      const undoHandler = () => this.undo();
      undoBtn.addEventListener('click', undoHandler);
      this.eventListeners.push({ element: undoBtn, event: 'click', handler: undoHandler });
    }

    if (redoBtn) {
      const redoHandler = () => this.redo();
      redoBtn.addEventListener('click', redoHandler);
      this.eventListeners.push({ element: redoBtn, event: 'click', handler: redoHandler });
    }

    this.updateUI();
  }

  /**
   * Update UI elements (buttons)
   */
  updateUI() {
    const undoBtn = document.querySelector('[data-undo]');
    const redoBtn = document.querySelector('[data-redo]');

    if (undoBtn) {
      undoBtn.disabled = !this.canUndo();
      undoBtn.classList.toggle('disabled', !this.canUndo());
    }
    if (redoBtn) {
      redoBtn.disabled = !this.canRedo();
      redoBtn.classList.toggle('disabled', !this.canRedo());
    }
  }

  /**
   * Trigger custom events
   */
  triggerEvent(eventName, detail = {}) {
    this.editor.dispatchEvent(new CustomEvent(`undoredo:${eventName}`, {
      detail,
      bubbles: true
    }));
  }

  /**
   * Clear all history
   */
  clear() {
    this.undoStack = [];
    this.redoStack = [];
    this.saveState();
    return this;
  }

  /**
   * Get stack info
   */
  getInfo() {
    return {
      undoCount: this.undoStack.length - 1,
      redoCount: this.redoStack.length,
      canUndo: this.canUndo(),
      canRedo: this.canRedo()
    };
  }

  /**
   * Destroy the manager and clean up
   */
  destroy() {
    this.stopTracking();
    this.clear();
    this.editor = null;
  }
}

/**
 * MediumEditor Extensions for Cyllo Studio
 */
if (typeof MediumEditor !== 'undefined') {
  const DeleteButton = MediumEditor.Extension.extend({
    name: 'deleteElement',
    init: function () {
      this.button = this.document.createElement('button');
      this.button.classList.add('medium-editor-action');
      this.button.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13"
             viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="3 6 5 6 21 6"/>
          <path d="M19 6l-1 14H6L5 6"/>
          <path d="M10 11v6M14 11v6"/>
          <path d="M9 6V4h6v2"/>
        </svg>`;
      this.button.title = 'Delete Element';

      this.on(this.button, 'click', this.handleClick.bind(this));
    },
    getButton: function () {
      return this.button;
    },
    handleClick: function (event) {
      event.preventDefault();
      event.stopPropagation();

      const el = this.base.getSelectedParentElement();
      if (el && !el.classList.contains('page')) {
          el.remove();
          this.base.checkContentChanged();
      }
    }
  });

  const UndoButton = MediumEditor.Extension.extend({
    name: 'undoButton',
    init: function () {
      this.button = this.document.createElement('button');
      this.button.classList.add('medium-editor-action');
      this.button.innerHTML = '<i class="fa fa-undo"></i>';
      this.button.title = 'Undo';
      this.on(this.button, 'click', this.handleClick.bind(this));
    },
    getButton: function () { return this.button; },
    handleClick: function (event) {
      event.preventDefault();
      if (this.base.options.owner && typeof this.base.options.owner.undo === 'function') {
        this.base.options.owner.undo();
      }
    }
  });

  const RedoButton = MediumEditor.Extension.extend({
    name: 'redoButton',
    init: function () {
      this.button = this.document.createElement('button');
      this.button.classList.add('medium-editor-action');
      this.button.innerHTML = '<i class="fa fa-repeat"></i>';
      this.button.title = 'Redo';
      this.on(this.button, 'click', this.handleClick.bind(this));
    },
    getButton: function () { return this.button; },
    handleClick: function (event) {
      event.preventDefault();
      if (this.base.options.owner && typeof this.base.options.owner.redo === 'function') {
        this.base.options.owner.redo();
      }
    }
  });

  // Global exposure for explicit instantiation
  window.DeleteButton = DeleteButton;
  window.UndoButton = UndoButton;
  window.RedoButton = RedoButton;

  MediumEditor.extensions.deleteElement = DeleteButton;
  MediumEditor.extensions.undoButton = UndoButton;
  MediumEditor.extensions.redoButton = RedoButton;
}

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = UndoRedoManager;
}

if (typeof window !== 'undefined') {
  window.UndoRedoManager = UndoRedoManager;
}