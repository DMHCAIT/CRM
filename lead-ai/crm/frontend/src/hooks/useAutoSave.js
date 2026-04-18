import { useEffect, useCallback, useRef, useState } from 'react';
import { message } from 'antd';
import debounce from 'lodash/debounce';

/**
 * Auto-save Hook
 * Automatically saves form data to localStorage every 30 seconds
 * Recovers drafts on component mount
 * Shows unsaved changes warning
 * 
 * @param {string} storageKey - Unique key for localStorage
 * @param {object} formData - Current form values
 * @param {function} onRecover - Callback when draft is recovered
 * @param {number} interval - Auto-save interval in milliseconds (default: 30000)
 */
const useAutoSave = ({
  storageKey,
  formData,
  onRecover,
  interval = 30000, // 30 seconds
  enabled = true
}) => {
  const [hasDraft, setHasDraft] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const savedDataRef = useRef(null);
  const intervalRef = useRef(null);

  // Save to localStorage
  const saveToStorage = useCallback((data) => {
    if (!enabled || !storageKey) return;
    
    try {
      const saveData = {
        data,
        timestamp: new Date().toISOString(),
        version: '1.0'
      };
      
      localStorage.setItem(storageKey, JSON.stringify(saveData));
      savedDataRef.current = data;
      setLastSaved(new Date());
      setHasUnsavedChanges(false);
      
      console.log(`[AutoSave] Saved draft to ${storageKey}`);
    } catch (error) {
      console.error('[AutoSave] Failed to save:', error);
      message.error('Failed to save draft');
    }
  }, [storageKey, enabled]);

  // Debounced save function
  const debouncedSave = useCallback(
    debounce((data) => {
      saveToStorage(data);
    }, 1000), // Wait 1 second after last change
    [saveToStorage]
  );

  // Load from localStorage
  const loadFromStorage = useCallback(() => {
    if (!enabled || !storageKey) return null;
    
    try {
      const stored = localStorage.getItem(storageKey);
      if (!stored) return null;
      
      const { data, timestamp } = JSON.parse(stored);
      
      // Check if draft is older than 7 days
      const draftAge = Date.now() - new Date(timestamp).getTime();
      const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days
      
      if (draftAge > maxAge) {
        // Draft too old, remove it
        clearDraft();
        return null;
      }
      
      return { data, timestamp };
    } catch (error) {
      console.error('[AutoSave] Failed to load draft:', error);
      return null;
    }
  }, [storageKey, enabled]);

  // Clear draft from storage
  const clearDraft = useCallback(() => {
    if (!storageKey) return;
    
    try {
      localStorage.removeItem(storageKey);
      setHasDraft(false);
      setLastSaved(null);
      setHasUnsavedChanges(false);
      savedDataRef.current = null;
      
      console.log(`[AutoSave] Cleared draft from ${storageKey}`);
    } catch (error) {
      console.error('[AutoSave] Failed to clear draft:', error);
    }
  }, [storageKey]);

  // Recover draft
  const recoverDraft = useCallback(() => {
    const draft = loadFromStorage();
    if (draft && onRecover) {
      onRecover(draft.data);
      message.success(`Draft recovered from ${new Date(draft.timestamp).toLocaleString()}`);
      setHasDraft(false);
    }
  }, [loadFromStorage, onRecover]);

  // Check for existing draft on mount
  useEffect(() => {
    const draft = loadFromStorage();
    if (draft) {
      setHasDraft(true);
      console.log('[AutoSave] Draft found:', draft.timestamp);
    }
  }, [loadFromStorage]);

  // Auto-save on interval
  useEffect(() => {
    if (!enabled || !formData) return;

    // Check if data has changed
    const dataChanged = JSON.stringify(formData) !== JSON.stringify(savedDataRef.current);
    if (dataChanged) {
      setHasUnsavedChanges(true);
      debouncedSave(formData);
    }

    // Set up periodic save
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    intervalRef.current = setInterval(() => {
      if (hasUnsavedChanges) {
        saveToStorage(formData);
      }
    }, interval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      debouncedSave.cancel();
    };
  }, [formData, enabled, interval, saveToStorage, debouncedSave, hasUnsavedChanges]);

  // Warn on page unload
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (hasUnsavedChanges && enabled) {
        e.preventDefault();
        e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
        return e.returnValue;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [hasUnsavedChanges, enabled]);

  // Manual save function
  const manualSave = useCallback(() => {
    saveToStorage(formData);
    message.success('Draft saved');
  }, [formData, saveToStorage]);

  return {
    hasDraft,
    lastSaved,
    hasUnsavedChanges,
    recoverDraft,
    clearDraft,
    manualSave
  };
};

/**
 * Auto-save Banner Component
 * Shows draft recovery prompt and last saved time
 */
export const AutoSaveBanner = ({ 
  hasDraft, 
  lastSaved, 
  hasUnsavedChanges,
  onRecover, 
  onDismiss 
}) => {
  if (!hasDraft && !lastSaved) return null;

  return (
    <div>
      {hasDraft && (
        <div style={{
          padding: '12px 16px',
          background: '#fff7e6',
          border: '1px solid #ffd591',
          borderRadius: '4px',
          marginBottom: '16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <strong>Draft found</strong>
            <p style={{ margin: 0, fontSize: 12, color: '#8c8c8c' }}>
              You have an unsaved draft. Would you like to recover it?
            </p>
          </div>
          <div>
            <button
              onClick={onRecover}
              style={{
                marginRight: 8,
                padding: '4px 12px',
                background: '#1890ff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Recover
            </button>
            <button
              onClick={onDismiss}
              style={{
                padding: '4px 12px',
                background: 'transparent',
                border: '1px solid #d9d9d9',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
      
      {lastSaved && (
        <div style={{
          padding: '4px 8px',
          fontSize: 11,
          color: '#8c8c8c',
          textAlign: 'right'
        }}>
          {hasUnsavedChanges ? (
            <span>• Unsaved changes</span>
          ) : (
            <span>✓ Last saved at {lastSaved.toLocaleTimeString()}</span>
          )}
        </div>
      )}
    </div>
  );
};

export default useAutoSave;
