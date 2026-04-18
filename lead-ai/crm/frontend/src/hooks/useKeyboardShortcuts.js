import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Global Keyboard Shortcuts Hook
 * 
 * Shortcuts:
 * - Cmd/Ctrl + K: Open command palette
 * - Cmd/Ctrl + N: New lead
 * - Cmd/Ctrl + S: Save/Submit current form
 * - Cmd/Ctrl + /: Focus search
 * - Esc: Close modals/drawers
 * - G then L: Go to Leads
 * - G then D: Go to Dashboard
 * - G then P: Go to Pipeline
 * - G then A: Go to Analytics
 * - E: Edit selected item
 * - A: Assign selected items
 * - D: Delete selected items
 * - ?: Show keyboard shortcuts help
 */
const useKeyboardShortcuts = ({
  onOpenCommandPalette,
  onNewLead,
  onSave,
  onFocusSearch,
  onEdit,
  onAssign,
  onDelete,
  onShowHelp,
  enabled = true
}) => {
  const navigate = useNavigate();
  
  // Track "g" key for navigation shortcuts
  let gPressed = false;
  let gTimeout;

  const handleKeyDown = useCallback((event) => {
    if (!enabled) return;

    const { key, ctrlKey, metaKey, shiftKey, target } = event;
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const cmdOrCtrl = isMac ? metaKey : ctrlKey;
    
    // Don't trigger shortcuts when typing in inputs (except Esc and Cmd+S)
    const isInput = ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName);
    if (isInput && key !== 'Escape' && !(cmdOrCtrl && key === 's')) {
      return;
    }

    // Cmd/Ctrl + K: Command Palette
    if (cmdOrCtrl && key === 'k') {
      event.preventDefault();
      if (onOpenCommandPalette) {
        onOpenCommandPalette();
      }
    }

    // Cmd/Ctrl + N: New Lead
    if (cmdOrCtrl && key === 'n') {
      event.preventDefault();
      if (onNewLead) {
        onNewLead();
      }
    }

    // Cmd/Ctrl + S: Save
    if (cmdOrCtrl && key === 's') {
      event.preventDefault();
      if (onSave) {
        onSave();
      }
    }

    // Cmd/Ctrl + /: Focus Search
    if (cmdOrCtrl && key === '/') {
      event.preventDefault();
      if (onFocusSearch) {
        onFocusSearch();
      }
    }

    // Escape: Close modals/drawers
    if (key === 'Escape') {
      // Let React components handle this via their own listeners
      // This is just for documentation
    }

    // G key navigation (vim-style)
    if (key === 'g' && !isInput && !cmdOrCtrl) {
      if (gPressed) {
        // Double G - scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
        gPressed = false;
        clearTimeout(gTimeout);
      } else {
        gPressed = true;
        gTimeout = setTimeout(() => {
          gPressed = false;
        }, 1000); // Reset after 1 second
      }
    }

    // G + L: Go to Leads
    if (gPressed && key === 'l' && !isInput) {
      event.preventDefault();
      navigate('/leads');
      gPressed = false;
      clearTimeout(gTimeout);
    }

    // G + D: Go to Dashboard
    if (gPressed && key === 'd' && !isInput) {
      event.preventDefault();
      navigate('/');
      gPressed = false;
      clearTimeout(gTimeout);
    }

    // G + P: Go to Pipeline
    if (gPressed && key === 'p' && !isInput) {
      event.preventDefault();
      navigate('/pipeline');
      gPressed = false;
      clearTimeout(gTimeout);
    }

    // G + A: Go to Analytics
    if (gPressed && key === 'a' && !isInput) {
      event.preventDefault();
      navigate('/analytics');
      gPressed = false;
      clearTimeout(gTimeout);
    }

    // E: Edit (when not in input)
    if (key === 'e' && !isInput && !cmdOrCtrl) {
      if (onEdit) {
        event.preventDefault();
        onEdit();
      }
    }

    // A: Assign (when not in input)
    if (key === 'a' && !isInput && !cmdOrCtrl && !gPressed) {
      if (onAssign) {
        event.preventDefault();
        onAssign();
      }
    }

    // D: Delete (when not in input)
    if (key === 'd' && !isInput && !cmdOrCtrl && !gPressed) {
      if (onDelete) {
        event.preventDefault();
        onDelete();
      }
    }

    // ?: Show help
    if (shiftKey && key === '?' && !isInput) {
      event.preventDefault();
      if (onShowHelp) {
        onShowHelp();
      }
    }

  }, [
    enabled,
    navigate,
    onOpenCommandPalette,
    onNewLead,
    onSave,
    onFocusSearch,
    onEdit,
    onAssign,
    onDelete,
    onShowHelp
  ]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      if (gTimeout) clearTimeout(gTimeout);
    };
  }, [handleKeyDown]);

  return null; // This hook doesn't render anything
};

/**
 * Get formatted keyboard shortcuts for display
 */
export const getKeyboardShortcuts = () => {
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  const cmd = isMac ? '⌘' : 'Ctrl';
  
  return [
    {
      category: 'General',
      shortcuts: [
        { keys: `${cmd} + K`, description: 'Open command palette' },
        { keys: `${cmd} + /`, description: 'Focus search bar' },
        { keys: 'Esc', description: 'Close modal/drawer' },
        { keys: '?', description: 'Show keyboard shortcuts' },
      ]
    },
    {
      category: 'Navigation',
      shortcuts: [
        { keys: 'G then L', description: 'Go to Leads page' },
        { keys: 'G then D', description: 'Go to Dashboard' },
        { keys: 'G then P', description: 'Go to Pipeline' },
        { keys: 'G then A', description: 'Go to Analytics' },
        { keys: 'G G', description: 'Scroll to top' },
      ]
    },
    {
      category: 'Actions',
      shortcuts: [
        { keys: `${cmd} + N`, description: 'Create new lead' },
        { keys: `${cmd} + S`, description: 'Save/Submit form' },
        { keys: 'E', description: 'Edit selected item' },
        { keys: 'A', description: 'Assign selected items' },
        { keys: 'D', description: 'Delete selected items' },
      ]
    }
  ];
};

export default useKeyboardShortcuts;
