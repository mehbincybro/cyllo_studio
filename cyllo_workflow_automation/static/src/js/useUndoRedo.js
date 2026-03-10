/** @odoo-module **/

const { useState, reactive } = owl;

/**
 * useUndoRedo Hook
 * Manages history stacks for the workflow editor.
 */
export function useUndoRedo() {
    const state = reactive({
        past: [],
        future: [],
    });

    const MAX_HISTORY = 50;

    return {
        get canUndo() {
            return state.past.length > 0;
        },
        get canRedo() {
            return state.future.length > 0;
        },

        /**
         * Pushes a new snapshot to the past stack.
         * Clears the future stack since a new action invalidates it.
         */
        pushSnapshot(snapshot) {
            if (state.past.length > 0 && state.past[state.past.length - 1] === snapshot) {
                return; // Don't push identical states
            }
            state.past.push(snapshot);
            if (state.past.length > MAX_HISTORY) {
                state.past.shift();
            }
            state.future = [];
        },

        /**
         * Returns the previous state and moves current to future.
         */
        undo(currentSnapshot) {
            if (!this.canUndo) return null;
            
            const previous = state.past.pop();
            state.future.push(currentSnapshot);
            return previous;
        },

        /**
         * Returns the next state and moves current to past.
         */
        redo(currentSnapshot) {
            if (!this.canRedo) return null;

            const next = state.future.pop();
            state.past.push(currentSnapshot);
            return next;
        },

        clear() {
            state.past = [];
            state.future = [];
        }
    };
}
